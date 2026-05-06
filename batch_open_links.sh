#!/bin/bash

echo "=========================================="
echo "  百度网盘批量保存助手"
echo "=========================================="
echo ""
echo "操作流程："
echo "  1. Chrome 会批量打开分享链接"
echo "  2. 每批 5 个链接"
echo "  3. 你手动输入密码并保存"
echo "  4. ⚠️  第一个文件保存到: /mac/FCP插件/"
echo "  5. 后续文件会记住该目录"
echo ""
read -p "按 Enter 开始..."

CRAWLED_FILE="mfcpx_crawled.json"
BATCH_SIZE=5

# 读取插件列表
total=$(python3 -c "import json; print(len(json.load(open('$CRAWLED_FILE'))))")
echo "共 $total 个插件"

# 分批打开
for ((i=0; i<$total; i+=$BATCH_SIZE)); do
  batch_num=$((i/$BATCH_SIZE + 1))
  total_batches=$(( ($total + $BATCH_SIZE - 1) / $BATCH_SIZE ))
  
  echo ""
  echo "=========================================="
  echo "批次 $batch_num/$total_batches"
  echo "=========================================="
  
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
      echo ""
      echo "[$idx/$total] $title"
      echo "  链接: $url"
      echo "  密码: ${pwd:-无}"
      
      if [[ -n "$url" ]]; then
        open -a "Google Chrome" "$url"
        sleep 1
      fi
    fi
  done
  
  echo ""
  echo "✅ 本批次链接已打开"
  echo "请在浏览器中保存这些链接"
  read -p "完成后按 Enter 继续下一批..."
done

echo ""
echo "=========================================="
echo "✅ 所有链接已处理完毕！"
echo "=========================================="
