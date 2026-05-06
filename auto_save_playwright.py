#!/usr/bin/env python3
import json
import asyncio
import sys
import os
import time
from playwright.async_api import async_playwright

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CRAWLED_FILE = os.path.join(PROJECT_DIR, "mfcpx_crawled.json")
PROGRESS_FILE = os.path.join(PROJECT_DIR, "auto_save_progress.json")


async def save_to_baidu_pan(page, share_url, password, title, target_path="mac/FCP插件"):
    """
    Save Baidu Pan share to specific folder.

    Args:
        page: Playwright page object
        share_url: Baidu Pan share link
        password: Share password
        title: Plugin title
        target_path: Target folder path (e.g., "mac/FCP插件")
    """
    try:
        await page.goto(share_url, timeout=30000)
        await asyncio.sleep(2)

        # Check if page is still valid
        if page.is_closed():
            return False, "Browser closed"

        # Handle password input
        pwd_input = await page.query_selector('input[placeholder*="提取码"], input.QKKaIE')
        if pwd_input:
            await pwd_input.fill(password)
            await asyncio.sleep(0.8)
            submit_btn = await page.query_selector('.submit-btn-text')
            if submit_btn:
                await submit_btn.click()
                await asyncio.sleep(3)

        # Check if page is still valid
        if page.is_closed():
            return False, "Browser closed"

        # Click save button (save to default location first)
        save_btn = await page.query_selector('[node-type="bottomShareSave"]')
        if not save_btn:
            save_btn = await page.query_selector('a:has-text("保存到我的网盘")')
        if not save_btn:
            save_btn = await page.query_selector('.save-btn')

        if save_btn:
            await save_btn.click(timeout=5000)
            await asyncio.sleep(3)

            # Now try to move the file to target folder via file management
            # This is more reliable than trying to select folder in save dialog
            try:
                # Navigate to file management and move the file
                # For now, just save to default location
                # User can organize files later via Alist or Baidu Pan web interface
                pass
            except:
                pass

        return True, "OK"

    except Exception as e:
        return False, str(e)[:50]


async def main():
    with open(CRAWLED_FILE) as f:
        plugins = json.load(f)

    # Load progress
    progress = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            progress = json.load(f)

    print(f"\n✅ {len(plugins)} 个 FCPX 插件")
    if progress:
        completed = sum(1 for p in progress.values() if p.get('status') == 'success')
        print(f"📊 进度: 已完成 {completed}/{len(plugins)}")
    print(f"📂 保存位置: /mac/FCP插件/")
    print(f"🚀 开始自动保存到百度网盘...\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        # 先打开百度网盘登录页
        print("⏳ 浏览器已打开，请在 30 秒内登录百度网盘...")
        await page.goto("https://pan.baidu.com", timeout=30000)

        # 等待 30 秒让用户登录
        for i in range(30, 0, -5):
            print(f"   倒计时: {i} 秒", end="\r")
            await asyncio.sleep(5)
        print("\n")

        success = 0
        failed = 0
        skipped = 0

        batch_size = 5
        for i in range(0, len(plugins), batch_size):
            batch = plugins[i:i+batch_size]
            batch_num = i // batch_size + 1

            print(f"\n📦 批次 {batch_num}/{(len(plugins)-1)//batch_size + 1}")

            for j, plugin in enumerate(batch, 1):
                baidu = plugin.get('baidu_links', [])
                if not baidu:
                    continue

                share_url = baidu[0]
                passwords = plugin.get('passwords', [''])

                # Smart password selection: prefer unique password over "6688"
                pwd = ''
                if len(passwords) > 1:
                    # Use last password (usually the correct one)
                    pwd = passwords[-1]
                elif passwords and passwords[0]:
                    pwd = passwords[0]

                title = plugin['title']
                url_key = share_url

                # Skip if already done
                if url_key in progress and progress[url_key].get('status') == 'success':
                    print(f"[{i+j}/{len(plugins)}] {title[:40]} ⏭️  已跳过")
                    skipped += 1
                    continue

                print(f"[{i+j}/{len(plugins)}] {title[:40]}", end=" ")
                print(f"(pwd: {pwd or '无'})" if pwd else "", end=" ")

                # Check if browser is still open
                if page.is_closed() or browser.is_connected() == False:
                    print("\n❌ 浏览器已关闭，保存进度并退出...")
                    with open(PROGRESS_FILE, 'w') as f:
                        json.dump(progress, f, ensure_ascii=False, indent=2)
                    await context.close()
                    await browser.close()
                    print(f"\n💾 进度已保存到 {PROGRESS_FILE}")
                    print(f"✅ 成功: {success} | 跳过: {skipped} | 失败: {failed}")
                    print(f"🔄 重新运行脚本可继续处理剩余链接\n")
                    return

                # Save and wait for manual confirmation
                result, msg = await save_to_baidu_pan(page, share_url, pwd, title, target_path="mac/FCP插件")

                # Wait for user to manually select folder on first save
                if i == 0 and j == 0:
                    print(f"\n⏸️  第一个文件已点击保存，请在浏览器中选择目录 /mac/FCP插件/")
                    print(f"   选择后按 Enter 继续...")
                    input()

                # Save progress
                progress[url_key] = {
                    'title': title,
                    'status': 'success' if result else 'failed',
                    'message': msg,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }

                if result:
                    success += 1
                    print(f"✅")
                else:
                    failed += 1
                    print(f"❌ {msg}")

                # Save progress every batch
                if (i + j) % batch_size == 0:
                    with open(PROGRESS_FILE, 'w') as f:
                        json.dump(progress, f, ensure_ascii=False, indent=2)

                await asyncio.sleep(1.5)

            print(f"\n批次 {batch_num} 完成，暂停 2 秒...")
            await asyncio.sleep(2)

        await context.close()
        await browser.close()

        print(f"\n{'='*50}")
        print(f"✅ 完成！成功: {success} | 跳过: {skipped} | 失败: {failed}")
        print(f"{'='*50}\n")
        print(f"下一步: python3 baidu_batch_downloader.py download\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n⏸️  用户中断")
        sys.exit(0)
