#!/bin/bash

echo "=========================================="
echo "  百度网盘自动分批保存助手"
echo "=========================================="
echo ""
echo "工作流程："
echo "  1. 每批自动打开 5 个链接"
echo "  2. 等待 3 分钟让你保存"
echo "  3. 自动继续下一批"
echo "  4. 重复直到完成"
echo ""
echo "⏰ 预计总时间: 约 50 分钟"
echo ""

CRAWLED_FILE="mfcpx_crawled.json"
BATCH_SIZE=5
SAVE_TIME=180  # 每批等待3分钟

total=$(python3 -c "import json; print(len(json.load(open('$CRAWLED_FILE'))))")
echo "共 $total 个插件，分 $(( ($total + BATCH_SIZE - 1) / BATCH_SIZE )) 批"
echo ""

start_time=$(date +%s)

# 分批处理
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
      echo "[$idx/$total] ${title:0:45} (pwd: ${pwd:-无})"
      
      if [[ -n "$url" ]]; then
        open -a "Google Chrome" "$url"
        sleep 1
      fi
    fi
  done
  
  echo ""
  echo "✅ 本批 5 个链接已打开"
  echo ""
  
  # 如果不是最后一批，等待用户保存
  if [[ $((i + BATCH_SIZE)) -lt $total ]]; then
    echo "⏳ 等待 3 分钟让你保存..."
    echo "   保存完成后脚本会自动继续"
    echo ""
    
    # 倒计时显示
    for ((k=SAVE_TIME; k>0; k-=10)); do
      minutes=$((k / 60))
      seconds=$((k % 60))
      printf "\r   剩余时间: %02d:%02d " $minutes $seconds
      sleep 10
    done
    echo ""
    echo ""
  fi
done

end_time=$(date +%s)
duration=$((end_time - start_time))
minutes=$((duration / 60))
seconds=$((duration % 60))

echo "=========================================="
echo "✅ 所有 81 个链接已处理完毕！"
echo "=========================================="
echo "总用时: ${minutes} 分 ${seconds} 秒"
echo ""
echo "📂 请检查所有文件是否已保存到 /mac/FCP插件/"
