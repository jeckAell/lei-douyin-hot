#!/usr/bin/env python3
"""
抖音热点中心登录检测脚本
功能：检测 douhot.douyin.com 登录状态，未登录则截图提示用户扫码
用法: python3 check_douyin_hot.py
"""

import subprocess, json, sys, time, os, re, http.client

CDP_HOST, CDP_PORT = '127.0.0.1', 9223
SCREENSHOT_DIR = os.path.expanduser('~/.openclaw/workspace/douyin_hot')

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def check_chrome():
    try:
        c = http.client.HTTPConnection(CDP_HOST, CDP_PORT, timeout=3)
        c.request('GET', '/json/version')
        c.getresponse().read(); c.close()
        return True
    except:
        return False

def run(cmd, timeout=12):
    try:
        r = subprocess.run(f'agent-browser --cdp {CDP_PORT} {cmd}', shell=True,
                         capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return ''

def cdp_js(js):
    """执行 JS 并返回结果字符串"""
    try:
        c = http.client.HTTPConnection(CDP_HOST, CDP_PORT, timeout=5)
        c.request('GET', '/json/list')
        pages = json.loads(c.getresponse().read()); c.close()
        ws_url = next((p['webSocketDebuggerUrl'] for p in pages if p.get('type') == 'page'), pages[0]['webSocketDebuggerUrl'])
        import asyncio, websockets
        async def do():
            ws = await asyncio.wait_for(websockets.connect(ws_url), timeout=10)
            mid = 1
            async def send(m, p=None):
                nonlocal mid
                await ws.send(json.dumps({'id': mid, 'method': m, 'params': p or {}})); mid += 1
                while True:
                    r = await asyncio.wait_for(ws.recv(), timeout=5)
                    d = json.loads(r)
                    if d.get('id') == mid - 1: return d
            rv = await send('Runtime.evaluate', {'expression': js, 'returnByValue': True})
            await ws.close()
            return rv.get('result',{}).get('result',{}).get('value','') or ''
        return asyncio.run(do())
    except Exception as e:
        return f'error:{e}'

def find_ref(text, kw):
    """通过文本找 ref"""
    for line in text.split('\n'):
        if kw not in line:
            continue
        m = re.search(r'ref=(e\d+)', line)
        if m:
            return m.group(1)
    return None

def check_login_state():
    """检测登录状态，返回 True=已登录，False=未登录"""
    # 用更精确的 JS 检测登录状态
    js_result = cdp_js('''
        (function() {
            // 查找"登录"相关按钮（未登录状态）
            var loginBtns = document.querySelectorAll('button, a, [role="button"]');
            for (var el of loginBtns) {
                var txt = el.textContent.trim();
                if (txt === '登录' || txt === '登录/注册' || txt === '立即登录') {
                    var rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        return 'LOGIN_REQUIRED:登录按钮';
                    }
                }
            }
            // 检查"我的数据"、"我的"导航（已登录状态）
            var navItems = document.querySelectorAll('a, button, [class*="nav"], [class*="menu"]');
            for (var el of navItems) {
                var txt = el.textContent.trim();
                if (txt === '我的数据' || txt === '我的') {
                    var rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && rect.top < 100) {
                        return 'LOGGED_IN:发现用户导航';
                    }
                }
            }
            // 检查 URL 是否有 sign_uid 参数（已登录标识）
            var currentUrl = window.location.href;
            if (currentUrl.includes('sign_uid=')) {
                return 'LOGGED_IN:URL含sign_uid';
            }
            // 页面标题检查
            var title = document.title || '';
            if (title.includes('我的')) {
                return 'LOGGED_IN:标题含我的';
            }
            return 'UNKNOWN:未能确定登录状态';
        })()
    ''')
    print(f'   JS检测结果: {js_result}')

    if js_result.startswith('LOGGED_IN') or js_result.startswith('UNKNOWN'):
        return True  # 已登录或无法确定时都当作已登录（避免误判）
    return False  # LOGIN_REQUIRED 时未登录

def take_screenshot():
    """截取整个页面并保存"""
    filepath = os.path.join(SCREENSHOT_DIR, 'login_need.png')
    result = run(f'screenshot "{filepath}"', timeout=10)
    if os.path.exists(filepath):
        return filepath
    return None

def main():
    print('🔧 检查 Chrome...')
    if not check_chrome():
        print('❌ Chrome Debug 未启动，请先运行 start.sh')
        sys.exit(1)
    print('✅ Chrome 运行中')

    print('🌐 打开抖音热点中心...')
    run('open "https://douhot.douyin.com/"', timeout=10)
    time.sleep(3)

    print('🔍 检测登录状态...')
    is_logged_in = check_login_state()

    if is_logged_in:
        print()
        print('=' * 40)
        print('✅ 已登录')
        print('=' * 40)
        sys.exit(0)

    # 未登录，截图提示用户扫码
    print()
    print('🔐 检测到未登录，开始登录流程...')

    # 尝试点击登录按钮
    snap = run('snapshot -i', timeout=8)
    for kw in ['登录', '登录/注册', '立即登录']:
        ref = find_ref(snap, kw)
        if ref:
            print(f'🖱️ 点击登录按钮 @{ref}...')
            run(f'click @{ref}', timeout=8)
            time.sleep(2)
            break
    else:
        # 用 JS 点击
        js_result = cdp_js('''
            (function() {
                var els = document.querySelectorAll('button, a, [role="button"]');
                for (var el of els) {
                    var txt = el.textContent.trim();
                    if (txt === '登录' || txt === '登录/注册' || txt === '立即登录') {
                        el.scrollIntoView({block: "center"});
                        el.click();
                        return 'clicked';
                    }
                }
                return 'not found';
            })()
        ''')
        print(f'   JS点击结果: {js_result}')

    time.sleep(2)
    print('📸 截图保存...')
    screenshot_path = take_screenshot()

    print()
    print('=' * 50)
    print('⚠️ 未登录，请扫描二维码登陆')
    if screenshot_path:
        print(f'📁 截图: {screenshot_path}')
    print('=' * 50)
    sys.exit(1)

if __name__ == '__main__':
    main()
