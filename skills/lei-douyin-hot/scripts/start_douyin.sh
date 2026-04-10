#!/bin/bash
# Chrome Debug 启动脚本 - 抖音热点专用
# 功能：启动带调试端口的 Chrome（端口9223），继承已有登录状态
# 用法: ./start_douyin.sh [test]
#   无参数 = 无头模式（默认）
#   test    = 测试模式，使用有头浏览器

CHROME="$HOME/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome"
USER_DATA="$HOME/.config/chromium-hot"
PORT=9223
HEADED=false

# 解析参数
if [ "$1" == "test" ]; then
    HEADED=true
fi

# 杀掉已有实例（只杀这个端口的）
pkill -f "chrome-linux64/chrome.*--remote-debugging-port=$PORT" 2>/dev/null
sleep 1

# 清理锁文件
rm -rf "$USER_DATA/SingletonLock" "$USER_DATA/.lock" 2>/dev/null

# 启动参数
ARGS=(
  --remote-debugging-port=$PORT
  --user-data-dir=$USER_DATA
  --no-sandbox
  --disable-dev-shm-usage
  --disable-extensions
  --disable-background-networking
  --disable-sync
  --disable-translate
  --no-first-run
  --metrics-recording-only
  --mute-audio
  --no-default-browser-check
)

if [ "$HEADED" == "true" ]; then
    echo "启动模式: 测试模式 (有头浏览器)"
    $CHROME "${ARGS[@]}" 2>&1 &
else
    echo "启动模式: 无头浏览器（xvfb）"
    xvfb-run -a $CHROME "${ARGS[@]}" 2>&1 &
fi

sleep 3

# 验证是否启动成功
if curl -s http://127.0.0.1:$PORT/json/version > /dev/null 2>&1; then
    echo "✅ Chrome 抖音热点 Debug 启动成功"
    echo "   CDP: http://127.0.0.1:$PORT"
else
    echo "❌ 启动失败"
fi
