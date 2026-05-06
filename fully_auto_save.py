#!/usr/bin/env python3
"""
完全自动化：逐个打开链接 → 自动点击保存 → 良好间隔 → 完成全部
"""
import asyncio
import json
import os
import time
from playwright.async_api import async_playwright

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CRAWLED_FILE = os.path.join(PROJECT_DIR, "mfcpx_crawled.json")
PROGRESS_FILE = os.path.join(PROJECT_DIR, "fully_auto_save_progress.json")

# 配置
WAIT_BETWEEN_LINKS = 12  # 每个链接间隔12秒（避免被限制）
WAIT_AFTER_CLICK = 3     # 点击后等待3秒


async def process_single_link(page, url, title, index, total, is_first=False):
    """处理单个链接"""
    try:
        print(f"[{index}/{total}] {title[:50]}", end=" ", flush=True)
        
        # 打开链接
        await page.goto(url, timeout=30000)
        await asyncio.sleep(2)
        
        # 检查是否需要验证码
        page_text = await page.content()
        if '验证码' in page_text or 'captcha' in page_text.lower():
            print("⚠️  需要验证码")
            return False, "需要验证码"
        
        # 查找并点击保存按钮
        save_selectors = [
            'a[node-type="bottomShareSave"]',
            'a:has-text("保存到我的网盘")',
            'a[class*="save"]'
        ]
        
        clicked = False
        for selector in save_selectors:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    is_visible = await btn.is_visible()
                    if is_visible:
                        await btn.click(timeout=5000)
                        clicked = True
                        break
            except:
                continue
        
        if not clicked:
            print("❌ 未找到保存按钮")
            return False, "未找到保存按钮"
        
        # 等待保存对话框
        await asyncio.sleep(WAIT_AFTER_CLICK)
        
        # 如果是第一个，等待用户选择目录
        if is_first:
            print("\n")
            print("=" * 60)
            print("⏸️  第一个链接：请选择保存目录")
            print("=" * 60)
            print("1. 在浏览器中选择目录: /mac/FCP插件/")
            print("2. 点击确定")
            print("3. 确认保存成功后，回到这里按 Enter 继续...")
            print("=" * 60)
            input()
            print("✅ 继续...")
        else:
            print("✅ 已点击保存")
        
        return True, "OK"
        
    except Exception as e:
        print(f"❌ 错误: {str(e)[:30]}")
        return False, str(e)[:30]


async def main():
    # 读取链接
    with open(CRAWLED_FILE) as f:
        plugins = json.load(f)
    
    # 构建带密码的URL列表
    links = []
    for item in plugins:
        baidu_links = item.get('baidu_links', [])
        passwords = item.get('passwords', [''])
        
        if baidu_links:
            url = baidu_links[0]
            pwd = passwords[-1] if passwords else ''
            
            if pwd and 'pwd=' not in url:
                url = f'{url}?pwd={pwd}'
            
            links.append({
                'title': item['title'],
                'url': url
            })
    
    # 加载进度
    progress = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            progress = json.load(f)
    
    print("=" * 60)
    print("   完全自动化批量保存")
    print("=" * 60)
    print(f"📊 总链接数: {len(links)}")
    print(f"⏱️  间隔时间: {WAIT_BETWEEN_LINKS}秒")
    print(f"📂 目标目录: /mac/FCP插件/")
    print("")
    
    # 检查已完成的
    completed = sum(1 for url, data in progress.items() if data.get('success'))
    if completed > 0:
        print(f"💾 已完成: {completed}/{len(links)}")
        print("")
    
    async with async_playwright() as p:
        # 启动浏览器（持久化context）
        print("🚀 启动浏览器...")
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="/tmp/chrome_baidu_auto",
            headless=False,
            viewport={'width': 1280, 'height': 800}
        )
        
        # 创建页面
        page = await browser.new_page()
        
        # 先登录百度网盘
        print("📝 请在30秒内登录百度网盘...")
        await page.goto("https://pan.baidu.com", timeout=30000)
        
        for i in range(30, 0, -5):
            print(f"   倒计时: {i} 秒", end="\r", flush=True)
            await asyncio.sleep(5)
        print("\n")
        
        success = 0
        failed = 0
        skipped = 0
        
        # 检查是否有已完成的
        first_done = any(data.get('success') for data in progress.values())
        
        # 逐个处理
        for i, link in enumerate(links, 1):
            url = link['url']
            
            # 跳过已完成的
            if url in progress and progress[url].get('success'):
                print(f"[{i}/{len(links)}] {link['title'][:50]} ⏭️  已跳过")
                skipped += 1
                continue
            
            # 判断是否是第一个需要处理的
            is_first = (not first_done) and (success == 0 and skipped == 0)
            
            # 处理链接
            result, msg = await process_single_link(
                page, url, link['title'], i, len(links), is_first
            )
            
            # 记录进度
            progress[url] = {
                'title': link['title'],
                'success': result,
                'message': msg,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 保存进度文件
            with open(PROGRESS_FILE, 'w') as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
            
            if result:
                success += 1
                first_done = True
            else:
                failed += 1
            
            # 等待间隔（最后一个不需要等待）
            if i < len(links):
                print(f"⏳ 等待 {WAIT_BETWEEN_LINKS} 秒...", end=" ", flush=True)
                for w in range(WAIT_BETWEEN_LINKS, 0, -1):
                    print(f"{w}", end=" ", flush=True)
                    await asyncio.sleep(1)
                print("")
                print("")
        
        await browser.close()
        
        print("")
        print("=" * 60)
        print(f"✅ 完成！成功: {success} | 跳过: {skipped} | 失败: {failed}")
        print("=" * 60)
        print(f"💾 进度已保存到: {PROGRESS_FILE}")
        print(f"📂 请检查文件是否保存到: /mac/FCP插件/")
        print("")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏸️  用户中断")
