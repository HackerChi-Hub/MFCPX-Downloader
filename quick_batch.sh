#!/bin/bash
# 快速批量打开链接（每批10个）

cd "/Users/chi/Scripts/02-多媒体处理/MFCPX-Downloader"
python3 << 'PYTHON'
import json, subprocess, time, sys

with open('mfcpx_crawled.json') as f:
    plugins = json.load(f)

batch_size = 10
for batch_start in range(0, len(plugins), batch_size):
    batch = plugins[batch_start:batch_start+batch_size]
    
    print(f"\n{'='*60}")
    print(f"批次 {batch_start//batch_size + 1}: {len(batch)} 个链接")
    print(f"{'='*60}\n")
    
    for i, plugin in enumerate(batch, 1):
        baidu = plugin.get('baidu_links', [])
        if not baidu:
            continue
        url = baidu[0]
        pwd = plugin.get('passwords', [''])[0]
        
        print(f"[{i}/{len(batch)}] {plugin['title'][:50]}")
        print(f"  链接: {url}")
        print(f"  密码: {pwd or '无'}")
        
        subprocess.run(['open', '-a', 'Google Chrome', url])
        time.sleep(0.5)
    
    print(f"\n✅ 已打开 {len(batch)} 个链接")
    print(f"请在浏览器中：")
    print(f"  1. 如有验证码，输入一次")
    print(f"  2. 批量选中所有链接")
    print(f"  3. 点击'保存到我的网盘'")
    print(f"\n完成后按 Enter 继续...")
    input()

print(f"\n{'='*60}")
print(f"✅ 全部 {len(plugins)} 个链接已打开！")
print(f"现在运行: python3 baidu_batch_downloader.py download")
print(f"{'='*60}")
PYTHON
