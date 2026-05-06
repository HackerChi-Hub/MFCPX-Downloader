#!/bin/bash

echo "=============================================="
echo "   百度网盘手动保存助手 - 第一版"
echo "=============================================="
echo ""
echo "步骤 1/3: 打开第一个链接"
echo ""

# 读取第一个链接
first_link=$(python3 -c "
import json
data = json.load(open('mfcpx_crawled.json'))
if data:
    item = data[0]
    url = item.get('baidu_links', [''])[0]
    pwd = item.get('passwords', [''])[-1]
    if pwd and 'pwd=' not in url:
        url = f'{url}?pwd={pwd}'
    print(f\"{item['title']}|{url}\")
")

if [[ -n "$first_link" ]]; then
  IFS='|' read -r title url <<< "$first_link"
  
  echo "标题: $title"
  echo "链接: $url"
  echo ""
  echo "正在 Chrome 中打开..."
  open -a "Google Chrome" "$url"
  
  echo ""
  echo "=============================================="
  echo "步骤 2/3: 手动保存"
  echo "=============================================="
  echo ""
  echo "请在浏览器中："
  echo "  1. 点击'保存到我的网盘'"
  echo "  2. 选择目录: /mac/FCP插件/"
  echo "  3. 点击确定"
  echo ""
  read -p "完成后按 Enter 继续..."
  
  echo ""
  echo "=============================================="
  echo "步骤 3/3: 自动打开剩余80个链接"
  echo "=============================================="
  echo ""
  echo "准备打开剩余链接（密码已内置）..."
  echo ""
  
  # 打开剩余链接
  for i in {1..80}; do
    idx=$((i+1))
    link_info=$(python3 -c "
import json
data = json.load(open('mfcpx_crawled.json'))
if len(data) > $i:
    item = data[$i]
    url = item.get('baidu_links', [''])[0]
    pwd = item.get('passwords', [''])[-1]
    if pwd and 'pwd=' not in url:
        url = f'{url}?pwd={pwd}'
    print(f\"{item['title']}|{url}\")
")
    
    if [[ -n "$link_info" ]]; then
      IFS='|' read -r title url <<< "$link_info"
      echo "[$idx/81] ${title:0:50}..."
      open -a "Google Chrome" "$url"
      sleep 0.5
    fi
  done
  
  echo ""
  echo "=============================================="
  echo "✅ 所有81个链接已打开！"
  echo "=============================================="
  echo ""
  echo "现在请在浏览器中逐个保存即可"
  echo "第一个已选择的目录会自动用于后续文件"
else
  echo "错误：无法读取链接数据"
fi
