#!/bin/bash
# 配合 Tampermonkey 网盘直链下载助手使用
# 油猴脚本会自动在页面上显示下载链接和转存按钮

cd "/Users/chi/Scripts/02-多媒体处理/MFCPX-Downloader"

python3 << 'PYTHON'
import json
import subprocess
import time

with open('mfcpx_crawled.json') as f:
    plugins = json.load(f)

print(f"\n✅ 加载了 {len(plugins)} 个插件\n")
print(f"{'='*60}")
print(f"油猴脚本批量打开模式")
print(f"{'='*60}\n")

print(f"📋 使用说明：")
print(f"  1. 每批打开 5 个链接（避免浏览器卡顿）")
print(f"  2. 油猴脚本会自动显示：")
print(f"     - 下载链接（可复制到 aria2c/IDM）")
print(f"     - 转存按钮（保存到你的网盘）")
print(f"  3. 每批完成后暂停，你处理完按 Enter 继续\n")

input("按 Enter 开始打开链接...\n")

batch_size = 5
for batch_start in range(0, len(plugins), batch_size):
    batch = plugins[batch_start:batch_start+batch_size]
    
    print(f"\n📦 批次 {batch_start//batch_size + 1}/{(len(plugins)-1)//batch_size + 1}")
    print(f"{'='*50}\n")
    
    for i, plugin in enumerate(batch, 1):
        baidu = plugin.get('baidu_links', [])
        if not baidu:
            continue
        
        url = baidu[0]
        pwds = plugin.get('passwords', [])
        pwd = pwds[-1] if pwds else ''
        
        print(f"[{batch_start+i}/{len(plugins)}] {plugin['title'][:55]}")
        print(f"  链接: {url}")
        print(f"  密码: {pwd if pwd else '(无)'}")
        
        # 在新标签页打开
        subprocess.run(['open', '-na', 'Google Chrome', url])
        time.sleep(0.5)
    
    print(f"\n✅ 已打开 {len(batch)} 个链接")
    print(f"\n💡 在浏览器中：")
    print(f"  - 油猴脚本会自动显示下载按钮/直链")
    print(f"  - 或显示转存按钮（保存到网盘）")
    print(f"  - 批量选中链接，复制到 aria2c 或点击转存")
    print(f"\n处理完这批后按 Enter 继续...")
    input()

print(f"\n{'='*60}")
print(f"✅ 全部 {len(plugins)} 个链接已打开！")
print(f"{'='*60}")
print(f"\n下一步：")
print(f"  如使用了下载直链：运行 aria2c 批量下载")
print(f"  如转存到网盘：运行 python3 baidu_batch_downloader.py download")
PYTHON
