#!/bin/bash

echo "=========================================="
echo "  百度网盘全自动批量打开"
echo "=========================================="
echo ""
echo "正在打开所有 81 个链接..."

CRAWLED_FILE="mfcpx_crawled.json"
BATCH_SIZE=5

total=$(python3 -c "import json; print(len(json.load(open('$CRAWLED_FILE'))))")
echo "共 $total 个插件"
echo ""

# 分批打开，不等待
for ((i=0; i<$total; i+=$BATCH_SIZE)); do
  batch_num=$((i/$BATCH_SIZE + 1))
  total_batches=$(( ($total + $BATCH_SIZE - 1) / $BATCH_SIZE ))
  
  echo "批次 $batch_num/$total_batches"
  
  for ((j=0; j<$BATCH_SIZE && j+$i<$total; j++)); do
    idx=$((i+j+1))
    plugin_info=$(python3 -c "
import json
data = json.load(open('$CRAWLED_FILE'))
if len(data) > $((i+j)):
    item = data[$((i+j))]
    links = item.get('baidu_links', [])
    pwds = item.get('passwords', [])
    url = links[0] if links else ''
    pwd = pwds[-1] if pwds else ''
    print(f\"{item['title']}|{url}|{pwd}\")
")
    
    if [[ -n "$plugin_info" ]]; then
      IFS='|' read -r title url pwd <<< "$plugin_info"
      echo "  [$idx/$total] ${title:0:40}... (pwd: ${pwd:-无})"
      
      if [[ -n "$url" ]]; then
        open -a "Google Chrome" "$url"
        sleep 1
      fi
    fi
  done
  
  echo ""
  sleep 2
done

echo "=========================================="
echo "✅ 所有 81 个链接已全部打开！"
echo "=========================================="
echo ""
echo "📋 现在请在浏览器中："
echo "  1. 第一个文件保存到 /mac/FCP插件/"
echo "  2. 后续文件会自动使用相同目录"
echo "  3. 逐个输入密码并保存"
echo ""
