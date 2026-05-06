#!/usr/bin/env python3
"""
稳健地一个一个点击保存按钮，间隔等待，持续直到全部完成
"""
import asyncio
import json
import os
import time
from playwright.async_api import async_playwright

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(PROJECT_DIR, "steady_save_progress.json")


async def click_save_and_wait(page, index, total):
    """点击保存并等待"""
    try:
        url = page.url
        title = await page.title()
        
        if 'pan.baidu.com' not in url:
            return False, "非百度网盘页面"
        
        short_title = title[:35] if title else "未知"
        print(f"[{index}/{total}] {short_title}...", end=" ", flush=True)
        
        # 查找并点击保存按钮
        save_selectors = [
            'a:has-text("保存到我的网盘")',
            '[node-type="bottomShareSave"]',
            'a[class*="save"]'
        ]
        
        clicked = False
        for selector in save_selectors:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    is_visible = await btn.is_visible()
                    if is_visible:
                        await btn.click(timeout=3000)
                        clicked = True
                        break
            except:
                continue
        
        if clicked:
            # 等待保存对话框出现
            await asyncio.sleep(2)
            print("✅ 已点击")
            return True, "OK"
        else:
            print("❌ 未找到按钮")
            return False, "未找到保存按钮"
    
    except Exception as e:
        print(f"❌ 错误: {str(e)[:30]}")
        return False, str(e)[:30]


async def main():
    print("=" * 60)
    print("   稳健自动保存 - 一个一个来")
    print("=" * 60)
    print("")
    
    # 加载进度
    progress = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            progress = json.load(f)
    
    async with async_playwright() as p:
        print("🔍 连接到Chrome...")
        
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        except:
            print("❌ 无法连接")
            print("请先启动Chrome（调试模式）：")
            print("/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
            return
        
        print("✅ 已连接")
        print("")
        
        while True:
            # 获取所有页面
            contexts = browser.contexts
            all_pages = []
            for context in contexts:
                pages = context.pages
                all_pages.extend(pages)
            
            # 过滤出百度网盘页面
            baidu_pages = [p for p in all_pages if 'pan.baidu.com' in p.url]
            
            if not baidu_pages:
                print("❌ 没有找到百度网盘标签页")
                break
            
            total = len(baidu_pages)
            print(f"📊 找到 {total} 个百度网盘标签页")
            print("")
            
            # 统计已完成
            completed = sum(1 for url in progress.values() if url.get('clicked'))
            print(f"💾 已完成: {completed}/{total}")
            print("")
            
            if completed >= total:
                print("✅ 全部完成！")
                break
            
            # 处理每个页面
            for i, page in enumerate(baidu_pages, 1):
                url = page.url
                
                # 检查是否已完成
                if url in progress and progress[url].get('clicked'):
                    continue
                
                # 点击保存
                result, msg = await click_save_and_wait(page, i, total)
                
                # 记录进度
                progress[url] = {
                    'url': url,
                    'clicked': result,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # 保存进度
                with open(PROGRESS_FILE, 'w') as f:
                    json.dump(progress, f, ensure_ascii=False, indent=2)
                
                # 等待一段时间（根据百度网盘的限制）
                wait_time = 8
                print(f"⏳ 等待 {wait_time} 秒...", end=" ", flush=True)
                
                for w in range(wait_time, 0, -1):
                    print(f"{w}", end=" ", flush=True)
                    await asyncio.sleep(1)
                
                print("")
                print("")
            
            # 一轮完成后，检查是否还有未完成的
            remaining = sum(1 for v in progress.values() if not v.get('clicked'))
            if remaining == 0:
                print("✅ 全部完成！")
                break
            
            print(f"⏸️  第一轮完成，还有 {remaining} 个未完成，继续循环...")
            print("")
            await asyncio.sleep(3)
        
        print("")
        print("=" * 60)
        print("✅ 处理完成！")
        print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏸️  用户中断")
