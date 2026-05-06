#!/usr/bin/env python3
"""
完全自动化：打开链接 → 自动点击保存按钮
"""
import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CRAWLED_FILE = os.path.join(PROJECT_DIR, "mfcpx_crawled.json")
PROGRESS_FILE = os.path.join(PROJECT_DIR, "auto_click_save_progress.json")
TARGET_DIR = "/mac/FCP插件"


async def auto_save(page, url, title, idx, total):
    """自动打开链接并点击保存"""
    try:
        await page.goto(url, timeout=30000)
        await asyncio.sleep(2)

        if page.is_closed():
            return False, "Browser closed"

        # 等待页面加载
        await asyncio.sleep(2)

        # 查找并点击保存按钮
        save_selectors = [
            'a:has-text("保存到我的网盘")',
            '[node-type="bottomShareSave"]',
            '.save-btn',
            'a[class*="save"]'
        ]

        clicked = False
        for selector in save_selectors:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    await btn.click(timeout=5000)
                    clicked = True
                    await asyncio.sleep(2)
                    break
            except:
                continue

        if clicked:
            return True, "OK"
        else:
            return False, "Save button not found"

    except Exception as e:
        return False, str(e)[:50]


async def main():
    with open(CRAWLED_FILE) as f:
        plugins = json.load(f)

    # 加载进度
    progress = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            progress = json.load(f)

    print(f"\n✅ {len(plugins)} 个 FCPX 插件")
    if progress:
        completed = sum(1 for p in progress.values() if p.get('status') == 'success')
        print(f"📊 进度: 已完成 {completed}/{len(plugins)}")
    print(f"📂 保存位置: {TARGET_DIR}")
    print(f"🚀 开始自动打开并点击保存...\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        # 先登录
        print("⏳ 浏览器已打开，请在 30 秒内登录百度网盘...")
        await page.goto("https://pan.baidu.com", timeout=30000)

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

                # 构建带密码的URL
                pwd = passwords[-1] if passwords else ''
                if pwd and 'pwd=' not in share_url:
                    separator = '&' if '?' in share_url else '?'
                    share_url = f'{share_url}{separator}pwd={pwd}'

                title = plugin['title']
                url_key = share_url

                # 跳过已完成
                if url_key in progress and progress[url_key].get('status') == 'success':
                    print(f"[{i+j}/{len(plugins)}] {title[:40]} ⏭️  已跳过")
                    skipped += 1
                    continue

                print(f"[{i+j}/{len(plugins)}] {title[:40]}", end=" ")

                # 检查浏览器
                if page.is_closed() or not browser.is_connected():
                    print("\n❌ 浏览器已关闭，保存进度并退出...")
                    with open(PROGRESS_FILE, 'w') as f:
                        json.dump(progress, f, ensure_ascii=False, indent=2)
                    await context.close()
                    await browser.close()
                    print(f"\n💾 进度已保存")
                    print(f"✅ 成功: {success} | 跳过: {skipped} | 失败: {failed}")
                    return

                result, msg = await auto_save(page, share_url, title, i+j, len(plugins))

                # 保存进度
                progress[url_key] = {
                    'title': title,
                    'status': 'success' if result else 'failed',
                    'message': msg,
                    'timestamp': __import__('time').strftime('%Y-%m-%d %H:%M:%S')
                }

                if result:
                    success += 1
                    print(f"✅")
                else:
                    failed += 1
                    print(f"❌ {msg}")

                # 每批保存进度
                if (i + j) % batch_size == 0:
                    with open(PROGRESS_FILE, 'w') as f:
                        json.dump(progress, f, ensure_ascii=False, indent=2)

                await asyncio.sleep(1)

            print(f"\n批次 {batch_num} 完成，暂停 2 秒...")
            await asyncio.sleep(2)

        await context.close()
        await browser.close()

        print(f"\n{'='*50}")
        print(f"✅ 完成！成功: {success} | 跳过: {skipped} | 失败: {failed}")
        print(f"{'='*50}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n⏸️  用户中断")
        sys.exit(0)
