#!/usr/bin/env python3
"""
半自动：自动打开链接，第一个文件暂停让你选择目录
"""
import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CRAWLED_FILE = os.path.join(PROJECT_DIR, "mfcpx_crawled.json")
PROGRESS_FILE = os.path.join(PROJECT_DIR, "auto_save_with_folder_progress.json")


async def open_and_wait_save(page, url, title, idx, total, is_first=False):
    """打开链接并等待用户手动保存"""
    try:
        await page.goto(url, timeout=30000)
        await asyncio.sleep(2)

        if page.is_closed():
            return False, "Browser closed"

        # 如果是第一个，等待用户手动操作
        if is_first:
            print(f"\n⏸️  第一个链接已打开！")
            print(f"   请在浏览器中：")
            print(f"   1. 点击'保存到我的网盘'")
            print(f"   2. 选择目录: /mac/FCP插件/")
            print(f"   3. 点击确定")
            print(f"   4. 回到这里按 Enter 继续...")
            input()

        # 等待页面操作完成
        await asyncio.sleep(2)
        return True, "OK"

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
    print(f"📂 保存位置: /mac/FCP插件/")
    print(f"🚀 开始处理...\n")

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

        batch_size = 3  # 减少批次大小，更可控
        first_done = any(p.get('status') == 'success' for p in progress.values())

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

                # 判断是否是第一个需要处理的
                is_first = (not first_done) and (success == 0 and skipped == 0)

                result, msg = await open_and_wait_save(page, share_url, title, i+j, len(plugins), is_first)

                # 保存进度
                progress[url_key] = {
                    'title': title,
                    'status': 'success' if result else 'failed',
                    'message': msg,
                    'timestamp': __import__('time').strftime('%Y-%m-%d %H:%M:%S')
                }

                if result:
                    success += 1
                    first_done = True
                    print(f"✅")
                else:
                    failed += 1
                    print(f"❌ {msg}")

                # 保存进度
                with open(PROGRESS_FILE, 'w') as f:
                    json.dump(progress, f, ensure_ascii=False, indent=2)

            print(f"\n批次 {batch_num} 完成")

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
