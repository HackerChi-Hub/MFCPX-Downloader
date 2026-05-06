#!/bin/bash

echo "=============================================="
echo "   打开剩余80个链接（密码已内置）"
echo "=============================================="
echo ""
echo "准备打开链接 2-81..."
echo ""

# 打开剩余80个链接
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
    echo "[$idx/81] ${title:0:55}"
    
    if [[ -n "$url" ]]; then
      open -a "Google Chrome" "$url"
      sleep 0.5
    fi
  fi
  
  # 每10个暂停一下
  if [[ $((idx % 10)) -eq 0 ]]; then
    echo ""
    echo "⏸️  已打开 $idx 个链接，暂停2秒..."
    sleep 2
    echo ""
  fi
done

echo ""
echo "=============================================="
echo "✅ 所有81个链接已全部打开！"
echo "=============================================="
echo ""
echo "📋 现在请在浏览器中："
echo "  - 逐个点击'保存到我的网盘'"
echo "  - 第一个已选择的目录会自动用于后续文件"
echo "  - 大约需要 20-30 分钟保存全部81个文件"
