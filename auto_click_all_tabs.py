#!/usr/bin/env python3
"""
自动点击所有已打开Chrome标签页中的"保存到我的网盘"按钮
"""
import asyncio
import json
import os
import time
from playwright.async_api import async_playwright

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(PROJECT_DIR, "auto_click_all_progress.json")
TARGET_DIR = "/mac/FCP插件"


async def click_save_button(page):
    """在页面中查找并点击保存按钮"""
    try:
        # 等待页面加载
        await asyncio.sleep(1)
        
        # 查找保存按钮的多种选择器
        save_selectors = [
            'a:has-text("保存到我的网盘")',
            '[node-type="bottomShareSave"]',
            'a[class*="save"]',
            '.save-btn',
            'a:has-text("保存")'
        ]
        
        for selector in save_selectors:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    # 检查按钮是否可见
                    is_visible = await btn.is_visible()
                    if is_visible:
                        await btn.click(timeout=3000)
                        return True, "clicked"
            except:
                continue
        
        return False, "button not found"
    
    except Exception as e:
        return False, str(e)[:30]


async def main():
    print("=" * 60)
    print("   自动点击所有标签页的保存按钮")
    print("=" * 60)
    print("")
    
    # 加载进度
    progress = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            progress = json.load(f)
    
    async with async_playwright() as p:
        # 连接到已打开的Chrome
        print("🔍 正在连接到Chrome浏览器...")
        
        try:
            # 尝试通过CDP连接
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        except:
            print("❌ 无法连接到Chrome，请确保Chrome以调试模式启动")
            print("   启动命令: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
            return
        
        print("✅ 已连接到Chrome")
        print("")
        
        # 获取所有context和pages
        contexts = browser.contexts
        all_pages = []
        
        for context in contexts:
            pages = context.pages
            all_pages.extend(pages)
        
        total = len(all_pages)
        print(f"📊 找到 {total} 个标签页")
        print("")
        
        if total == 0:
            print("❌ 没有找到任何标签页")
            return
        
        success = 0
        failed = 0
        skipped = 0
        
        for i, page in enumerate(all_pages, 1):
            try:
                url = page.url
                title = await page.title()
                
                # 只处理百度网盘页面
                if 'pan.baidu.com' not in url:
                    print(f"[{i}/{total}] ⏭️  跳过（非百度网盘页面）")
                    skipped += 1
                    continue
                
                # 获取短标题
                short_title = title[:40] if title else "无标题"
                print(f"[{i}/{total}] {short_title}", end=" ")
                
                # 检查URL是否已处理
                if url in progress and progress[url].get('clicked'):
                    print("⏭️  已跳过")
                    skipped += 1
                    continue
                
                # 点击保存按钮
                result, msg = await click_save_button(page)
                
                # 记录进度
                progress[url] = {
                    'title': title,
                    'url': url,
                    'clicked': result,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                if result:
                    success += 1
                    print("✅")
                    await asyncio.sleep(1.5)  # 等待保存对话框
                else:
                    failed += 1
                    print(f"❌ {msg}")
                
                # 每10个保存一次进度
                if i % 10 == 0:
                    with open(PROGRESS_FILE, 'w') as f:
                        json.dump(progress, f, ensure_ascii=False, indent=2)
                
            except Exception as e:
                failed += 1
                print(f"❌ 错误: {str(e)[:30]}")
        
        # 保存最终进度
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        
        print("")
        print("=" * 60)
        print(f"✅ 完成！成功: {success} | 跳过: {skipped} | 失败: {failed}")
        print("=" * 60)
        print("")
        print(f"💾 进度已保存到: {PROGRESS_FILE}")
        print("")
        print(f"📂 请检查文件是否保存到: {TARGET_DIR}")
        
        await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏸️  用户中断")
