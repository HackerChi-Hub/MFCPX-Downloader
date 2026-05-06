#!/usr/bin/env python3
"""
增强版完全自动化 - 带重试和容错
"""
import asyncio
import json
import os
import time
from playwright.async_api import async_playwright

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CRAWLED_FILE = os.path.join(PROJECT_DIR, "mfcpx_crawled.json")
PROGRESS_FILE = os.path.join(PROJECT_DIR, "robust_auto_save_progress.json")

# 配置
WAIT_BETWEEN = 15  # 间隔15秒
TIMEOUT = 60000    # 超时60秒
MAX_RETRIES = 3    # 最多重试3次


async def safe_goto(page, url, max_retries=MAX_RETRIES):
    """安全导航，带重试"""
    for attempt in range(max_retries):
        try:
            await page.goto(url, timeout=TIMEOUT, wait_until='domcontentloaded')
            await asyncio.sleep(2)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  ⚠️  导航失败，重试 {attempt+1}/{max_retries}...")
                await asyncio.sleep(3)
            else:
                raise
    return False


async def process_link(page, url, title, index, total, is_first):
    """处理单个链接"""
    try:
        print(f"[{index}/{total}] {title[:45]}", flush=True)
        
        # 打开链接
        await safe_goto(page, url)
        
        # 检查验证码
        content = await page.content()
        if '验证码' in content:
            print("  ⚠️  需要验证码，暂停...")
            print("  请手动处理后按 Enter 继续...")
            input()
        
        # 点击保存
        save_selectors = [
            'a[node-type="bottomShareSave"]',
            'a:has-text("保存到我的网盘")',
        ]
        
        for selector in save_selectors:
            try:
                btn = await page.wait_for_selector(selector, timeout=10000)
                if btn:
                    await btn.click()
                    print("  ✅ 已点击保存")
                    await asyncio.sleep(3)
                    
                    if is_first:
                        print("\n" + "="*50)
                        print("⏸️  请选择目录: /mac/FCP插件/")
                        print("   确认后按 Enter 继续...")
                        print("="*50 + "\n")
                        input()
                    
                    return True
            except:
                continue
        
        print("  ❌ 未找到保存按钮")
        return False
        
    except Exception as e:
        print(f"  ❌ 错误: {str(e)[:40]}")
        return False


async def main():
    # 读取数据
    with open(CRAWLED_FILE) as f:
        plugins = json.load(f)
    
    links = []
    for item in plugins:
        baidu = item.get('baidu_links', [])
        pwds = item.get('passwords', [])
        if baidu:
            url = baidu[0]
            pwd = pwds[-1] if pwds else ''
            if pwd and 'pwd=' not in url:
                url = f'{url}?pwd={pwd}'
            links.append({'title': item['title'], 'url': url})
    
    # 进度
    progress = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            progress = json.load(f)
    
    print("="*50)
    print("   增强版自动保存")
    print("="*50)
    print(f"总计: {len(links)} 个链接")
    print(f"间隔: {WAIT_BETWEEN}秒")
    print("")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="/tmp/chrome_robust",
            headless=False,
            viewport={'width': 1280, 'height': 800},
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        
        page = await browser.new_page()
        
        print("📝 请在浏览器中登录百度网盘（30秒）...")
        try:
            await page.goto("https://pan.baidu.com", timeout=30000)
        except:
            print("  ⚠️  页面加载慢，继续...")
        
        for i in range(30, 0, -5):
            print(f"   {i} 秒", end="\r", flush=True)
            await asyncio.sleep(5)
        print("\n")
        
        success = failed = skipped = 0
        first_done = any(v.get('success') for v in progress.values())
        
        for i, link in enumerate(links, 1):
            url = link['url']
            
            if url in progress and progress[url].get('success'):
                skipped += 1
                continue
            
            is_first = (not first_done) and success == 0
            
            result = await process_link(page, url, link['title'], i, len(links), is_first)
            
            progress[url] = {
                'title': link['title'],
                'success': result,
                'time': time.strftime('%H:%M:%S')
            }
            
            with open(PROGRESS_FILE, 'w') as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
            
            if result:
                success += 1
                first_done = True
            else:
                failed += 1
            
            if i < len(links):
                print(f"  ⏳ 等待 {WAIT_BETWEEN} 秒...", end=" ", flush=True)
                for w in range(WAIT_BETWEEN, 0, -1):
                    print(f"{w}", end=" ", flush=True)
                    await asyncio.sleep(1)
                print("")
        
        await browser.close()
        
        print("\n" + "="*50)
        print(f"✅ 完成！成功: {success} | 跳过: {skipped} | 失败: {failed}")
        print("="*50)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏸️  中断")
