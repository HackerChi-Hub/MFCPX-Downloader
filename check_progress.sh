#!/bin/bash

echo "=========================================="
echo "   百度网盘保存进度检查"
echo "=========================================="
echo ""

# 检查百度网盘目录
echo "📂 /mac/FCP插件/ 目录中的文件："
echo ""

result=$(curl -s "http://localhost:5244/api/fs/list" \
  -H "Authorization: $(curl -s http://localhost:5244/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"alist123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["token"])')" \
  -H "Content-Type: application/json" \
  -d '{"path":"/baidu/mydisk/mac/FCP插件","page":1,"per_page":200}' 2>/dev/null)

if [ $? -eq 0 ]; then
  count=$(echo "$result" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    content = data.get('data', {}).get('content')
    if content is None:
        print(0)
    else:
        print(len(content))
except:
    print(0)
" 2>/dev/null)

  echo "✅ 已保存: $count/81 个文件"
  echo ""
  
  if [ "$count" -gt 0 ]; then
    echo "最新保存的文件（前10个）："
    echo "$result" | python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data.get('data', {}).get('content', [])[:10]
for item in items:
    size = item.get('size', 0)
    if size > 1024**2:
        size_str = f'{size/1024**2:.1f}MB'
    elif size > 1024:
        size_str = f'{size/1024:.1f}KB'
    else:
        size_str = f'{size}B'
    print(f'  📄 {item[\"name\"][:60]} ({size_str})')
" 2>/dev/null
  fi
  
  # 进度百分比
  percent=$((count * 100 / 81))
  echo ""
  echo "📊 进度: $percent%"
  
  # 预计剩余时间
  remaining=$((81 - count))
  if [ "$count" -gt 0 ]; then
    echo "⏱️  剩余: $remaining 个文件"
  fi
else
  echo "❌ 无法连接到Alist，请检查服务"
fi

echo ""
echo "=========================================="
echo "💡 提示：运行 'watch -n 10 ./check_progress.sh' 实时监控"
echo "=========================================="
