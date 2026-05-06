#!/bin/bash

echo "=============================================="
echo "   百度网盘批量打开（密码已内置）"
echo "=============================================="
echo ""
echo "链接已包含密码，打开后只需点击保存按钮即可"
echo ""

CRAWLED_FILE="mfcpx_crawled.json"
BATCH_SIZE=5
BATCH_DELAY=10  # 每批等待秒数

total=$(python3 -c "import json; print(len(json.load(open('$CRAWLED_FILE'))))")
echo "共 $total 个插件"
echo ""

# 分批打开
for ((i=0; i<$total; i+=$BATCH_SIZE)); do
  batch_num=$((i/$BATCH_SIZE + 1))
  total_batches=$(( ($total + $BATCH_SIZE - 1) / $BATCH_SIZE ))
  
  echo "=========================================="
  echo "批次 $batch_num/$total_batches"
  echo "=========================================="
  
  # 打开本批链接
  for ((j=0; j<$BATCH_SIZE && j+$i<$total; j++)); do
    idx=$((i+j+1))
    plugin_info=$(python3 -c "
import json
from urllib.parse import quote
data = json.load(open('$CRAWLED_FILE'))
if len(data) > $((i+j)):
    item = data[$((i+j))]
    links = item.get('baidu_links', [])
    pwds = item.get('passwords', [])
    url = links[0] if links else ''
    pwd = pwds[-1] if pwds else ''
    
    # 构建带密码的URL
    if url and pwd and 'pwd=' not in url:
        separator = '&' if '?' in url else '?'
        url_with_pwd = f'{url}{separator}pwd={pwd}'
    else:
        url_with_pwd = url
    
    print(f\"{item['title']}|{url_with_pwd}\")
")
    
    if [[ -n "$plugin_info" ]]; then
      IFS='|' read -r title url <<< "$plugin_info"
      echo "[$idx/$total] ${title:0:50}"
      
      if [[ -n "$url" ]]; then
        open -a "Google Chrome" "$url"
        sleep 1
      fi
    fi
  done
  
  echo ""
  echo "✅ 本批链接已打开（密码已内置）"
  echo ""
  
  # 如果不是最后一批，等待
  if [[ $((i + BATCH_SIZE)) -lt $total ]]; then
    echo "⏳ 等待 ${BATCH_DELAY} 秒后自动打开下一批..."
    echo ""
    for ((k=BATCH_DELAY; k>0; k--)); do
      printf "\r   倒计时: %02d 秒 " $k
      sleep 1
    done
    echo ""
    echo ""
  fi
done

echo "=========================================="
echo "✅ 所有 81 个链接已打开！"
echo "=========================================="
