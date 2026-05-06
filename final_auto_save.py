#!/usr/bin/env python3
"""
半自动保存方案：自动打开链接，你手动点击保存
"""
import subprocess
import time

with open('mfcpx_crawled.json') as f:
    data = json.load(f)

# 从第10个开始（前9个已完成）
for i, item in enumerate(data[9:], 10):
    baidu = item.get('baidu_links', [])
    pwds = item.get('passwords', [])
    
    if not baidu:
        continue
    
    url = baidu[0]
    pwd = pwds[-1] if pwds else ''
    
    # 构建带密码的URL
    if pwd and 'pwd=' not in url:
        url = f'{url}?pwd={pwd}'
    
    title = item.get('title', '未知')[:50]
    
    print(f"[{i}/81] {title}")
    print("  打开中...")
    
    # 在当前激活的Chrome中打开
    subprocess.run(['open', '-a', 'Google Chrome', url])
    
    # 等待你保存
    print("  ⏳ 等待你保存 (预计10秒)...")
    print("  保存后按 Enter 继续...")
    
    input()  # 等待你按Enter
    
    print("  ✅ 继续...")

print("\n✅ 全部完成！")
