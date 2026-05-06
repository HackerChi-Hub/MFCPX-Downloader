#!/bin/bash

echo "=============================================="
echo "   百度网盘批量打开 - 清晰版本"
echo "=============================================="
echo ""
echo "准备打开前 5 个链接..."
echo ""

# 只打开前5个，让用户测试
links=(
  "https://pan.baidu.com/s/1wBd0gqPnNvM5daMZoMApFQ|b47f|FCPX插件-20组摄像机摇晃"
  "https://pan.baidu.com/s/1NNDT9tp7nVxoLwlHYtsaKA|re3m|FCPX插件-20组动感棱镜"
  "https://pan.baidu.com/s/1ea5HTKgUPGLd_h2Jdq0geQ|6688|FCPX插件-100个光效闪烁"
  "https://pan.baidu.com/s/1BSw_SFJfMUIgJTvrZAz8_Q|evsr|FCPX插件-40种摄像机急速"
  "https://pan.baidu.com/s/1ts-fZXm0h2MfEoV5fWq_TQ|q4pi|FCPX插件-9组竖屏电影"
)

echo "正在 Chrome 中打开 5 个链接..."
echo ""

for i in {1..5}; do
  IFS='|' read -r url pwd title <<< "${links[$((i-1))]}"
  echo "[$i/5] $title"
  echo "     密码: $pwd"
  echo "     链接: $url"
  echo ""
  
  open -a "Google Chrome" "$url"
  sleep 2
done

echo "=============================================="
echo "✅ 5 个链接已打开！"
echo "=============================================="
echo ""
echo "📋 现在请："
echo "  1. 查看 Chrome 浏览器（应该有5个新标签页）"
echo "  2. 第1个链接输入密码 b47f"
echo "  3. 保存到目录: /mac/FCP插件/"
echo "  4. 其余4个直接保存"
echo ""
echo "完成后告诉我，我会继续打开下一批"
echo ""
