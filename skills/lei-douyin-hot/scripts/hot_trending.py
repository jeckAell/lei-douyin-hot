#!/usr/bin/env python3
"""
抖音热点中心爬取主脚本
功能：自动爬取抖音热点视频榜前10条视频，调用 analyze_video.py 分析
用法: python3 hot_trending.py
"""

import subprocess, json, sys, time, os, re, http.client, asyncio, websockets

CDP_HOST = '127.0.0.1'
CDP_PORT = 9223  # 专属端口，不与主 CDP 冲突
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# analyze_video.py 所在目录及 CDP 端口
ANALYZE_SCRIPT_DIR = '/home/lei/.openclaw/workspace/skills/lei-doubao-browser/scripts'
ANALYZE_CDP_PORT = 9222
MAX_VIDEOS = 10
DOUHOT_URL = 'https://douhot.douyin.com/square/hotspot?active_tab=hotspot_video&date_window=1&first_tag=643&second_tag=64301x64302&sub_type=1002'


# ---------------------------------------------------------------------------
# Chrome / CDP 基础工具
# ---------------------------------------------------------------------------

def check_chrome():
    """检查 Chrome Debug 是否运行"""
    try:
        c = http.client.HTTPConnection(CDP_HOST, CDP_PORT, timeout=3)
        c.request('GET', '/json/version')
        c.getresponse().read()
        c.close()
        return True
    except Exception:
        return False


def get_pages():
    """获取所有标签页列表"""
    try:
        c = http.client.HTTPConnection(CDP_HOST, CDP_PORT, timeout=5)
        c.request('GET', '/json/list')
        pages = json.loads(c.getresponse().read())
        c.close()
        return pages
    except Exception:
        return []


def get_target_ws_url(target_keyword=None, activate=True):
    """根据 URL 关键词找到目标标签的 ws_url"""
    pages = get_pages()
    if not pages:
        return None

    if target_keyword:
        for p in pages:
            if target_keyword in p.get('url', ''):
                ws_url = p.get('webSocketDebuggerUrl')
                if ws_url:
                    if activate:
                        try:
                            c = http.client.HTTPConnection(CDP_HOST, CDP_PORT, timeout=5)
                            c.request('GET', f'/json/activate/{p.get("id", "")}')
                            c.getresponse().read()
                            c.close()
                        except Exception:
                            pass
                    return ws_url

    # fallback: 返回最后一个页面
    return pages[-1].get('webSocketDebuggerUrl')


async def _cdp_send_raw(ws_url, method, params=None, timeout=15):
    """通过 WebSocket 发送一条 CDP 命令并返回完整响应"""
    async with websockets.connect(ws_url) as ws:
        msg_id = 1
        await ws.send(json.dumps({'id': msg_id, 'method': method, 'params': params or {}}))
        r = await asyncio.wait_for(ws.recv(), timeout=timeout)
        return json.loads(r)


def cdp_js(js_code, target_keyword=None):
    """通过 CDP 执行 JS 并返回结果的字符串值"""
    try:
        ws_url = get_target_ws_url(target_keyword)
        if not ws_url:
            return 'error: no page found'
        result = asyncio.run(_cdp_send_raw(
            ws_url, 'Runtime.evaluate',
            {'expression': js_code, 'returnByValue': True}
        ))
        return result.get('result', {}).get('result', {}).get('value', '') or ''
    except Exception as e:
        return f'error:{e}'


def cdp_navigate(url, target_keyword=None):
    """通过 CDP Page.navigate 导航到指定 URL"""
    try:
        ws_url = get_target_ws_url(target_keyword)
        if not ws_url:
            return f'error: no page found for {target_keyword}'
        return asyncio.run(_cdp_send_raw(
            ws_url, 'Page.navigate', {'url': url}
        ))
    except Exception as e:
        return f'error:{e}'


def cdp_activate_tab(tab_id):
    """激活指定标签页"""
    try:
        c = http.client.HTTPConnection(CDP_HOST, CDP_PORT, timeout=5)
        c.request('GET', f'/json/activate/{tab_id}')
        c.getresponse().read()
        c.close()
        return True
    except Exception:
        return False


def close_tab_by_id(tab_id):
    """通过 CDP HTTP API 关闭指定标签页"""
    try:
        c = http.client.HTTPConnection(CDP_HOST, CDP_PORT, timeout=5)
        c.request('DELETE', f'/json/close/{tab_id}')
        c.getresponse().read()
        c.close()
        return True
    except Exception:
        return False


def close_all_tabs():
    """关闭所有标签页"""
    pages = get_pages()
    for p in pages:
        tab_id = p.get('id')
        if tab_id:
            close_tab_by_id(tab_id)
    print('   ✅ 所有标签页已关闭')


def close_browser():
    """关闭 Chrome 浏览器（杀掉进程）"""
    subprocess.run(['pkill', '-f', 'chrome.*9223'], stderr=subprocess.DEVNULL)
    time.sleep(1)
    print('   ✅ 浏览器已关闭')


def check_cdp_port(port):
    """检查指定 CDP 端口是否运行"""
    try:
        c = http.client.HTTPConnection(CDP_HOST, port, timeout=3)
        c.request('GET', '/json/version')
        c.getresponse().read()
        c.close()
        return True
    except Exception:
        return False


def start_chrome_for_analyze():
    """启动 analyze_video.py 所需的 Chrome（端口 9222）"""
    start_sh = os.path.join(ANALYZE_SCRIPT_DIR, 'start.sh')
    if os.path.exists(start_sh):
        print(f'   调用 start.sh 启动 CDP 9222...')
        subprocess.run(['bash', start_sh], capture_output=True, text=True, timeout=30)
        time.sleep(5)
    else:
        print(f'⚠️ start.sh 不存在: {start_sh}')


def ensure_analyze_chrome():
    """确保 analyze_video.py 所需的 Chrome（9222端口）已启动"""
    if check_cdp_port(ANALYZE_CDP_PORT):
        print(f'   CDP 端口 {ANALYZE_CDP_PORT} 已运行')
        return True
    print(f'   CDP 端口 {ANALYZE_CDP_PORT} 未启动，尝试启动...')
    start_chrome_for_analyze()
    return check_cdp_port(ANALYZE_CDP_PORT)


def click_at_position(ws_url, x, y):
    """使用 CDP Input.dispatchMouseEvent 点击指定坐标"""
    async def _do():
        async with websockets.connect(ws_url) as ws:
            mid = 1
            # mouseMoved
            await ws.send(json.dumps({
                'id': mid, 'method': 'Input.dispatchMouseEvent',
                'params': {'type': 'mouseMoved', 'x': x, 'y': y}
            }))
            await ws.recv()
            mid += 1
            # mousePressed
            await ws.send(json.dumps({
                'id': mid, 'method': 'Input.dispatchMouseEvent',
                'params': {'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1}
            }))
            await ws.recv()
            mid += 1
            # mouseReleased
            await ws.send(json.dumps({
                'id': mid, 'method': 'Input.dispatchMouseEvent',
                'params': {'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1}
            }))
            await ws.recv()

    return asyncio.run(_do())


# ---------------------------------------------------------------------------
# 业务逻辑辅助
# ---------------------------------------------------------------------------

def wait_for_load(seconds=3):
    """通用等待函数"""
    time.sleep(seconds)


def find_ref(text, keyword):
    """从 agent-browser --cdp 9223 snapshot 文本中按关键词查找 ref"""
    for line in text.split('\n'):
        if keyword not in line:
            continue
        m = re.search(r'ref=(e\d+)', line)
        if m:
            return m.group(1)
    return None


def check_table_exists(ws_url):
    """检查 douhot 页面上是否存在热点表格（<tr> 元素）"""
    js = '''
    (function() {
        var rows = document.querySelectorAll('tr');
        var validRows = [];
        for (var row of rows) {
            var firstTd = row.querySelector('td');
            if (!firstTd) continue;
            var txt = firstTd.textContent.trim();
            // 排名列可能是数字也可能是空（Rank 1/2/3 为空）
            if (txt === '' || /^\d+$/.test(txt)) {
                validRows.push(row);
            }
        }
        return validRows.length;
    })()
    '''
    try:
        result = asyncio.run(_cdp_send_raw(ws_url, 'Runtime.evaluate',
                                           {'expression': js, 'returnByValue': True}))
        val = result.get('result', {}).get('result', {}).get('value', 0)
        return int(val) if isinstance(val, (int, float)) else 0
    except Exception:
        return 0


def get_video_row_info(ws_url, row_index):
    """
    在 douhot 页面上定位第 row_index 个有效视频行（第一个 td 是纯数字或空的 tr），
    返回其 '查看' 按钮的中心坐标。
    注意：Rank 1/2/3 的排名列为空，其 rank 值按顺序推算。
    返回 dict: {x, y, rank} 或 None
    """
    js = f'''
    (function() {{
        var rows = document.querySelectorAll('tr');
        var validRows = [];
        for (var row of rows) {{
            var firstTd = row.querySelector('td');
            if (!firstTd) continue;
            var txt = firstTd.textContent.trim();
            // 排名列可能是数字（如 "04"）也可能是空（如 Rank 1/2/3）
            if (txt === '' || /^\\d+$/.test(txt)) {{
                validRows.push(row);
            }}
        }}
        if (validRows.length <= {row_index}) {{
            return JSON.stringify({{ error: 'row not found', total: validRows.length, requested: {row_index} }});
        }}
        var targetRow = validRows[{row_index}];
        var firstTd = targetRow.querySelector('td');
        var firstTdText = firstTd ? firstTd.textContent.trim() : '';
        // 排名列数字：如果有值就解析，否则按顺序推算（rowIndex 0=rank1, 1=rank2...）
        var rankNum = firstTdText !== '' ? parseInt(firstTdText, 10) : {row_index} + 1;
        var tds = targetRow.querySelectorAll('td');
        var lastTd = tds[tds.length - 1];
        var btn = lastTd.querySelector('button') || lastTd.querySelector('a') || lastTd;
        if (!btn) return JSON.stringify({{ error: 'no button in last td', rank: rankNum }});
        btn.scrollIntoView({{ behavior: 'instant', block: 'center' }});
        var rect = btn.getBoundingClientRect();
        var x = rect.left + rect.width / 2;
        var y = rect.top + rect.height / 2;
        return JSON.stringify({{ x: x, y: y, text: btn.textContent.trim(), rank: rankNum }});
    }})()
    '''
    try:
        result = asyncio.run(_cdp_send_raw(ws_url, 'Runtime.evaluate',
                                           {'expression': js, 'returnByValue': True}))
        val = result.get('result', {}).get('result', {}).get('value', '')
        if isinstance(val, str):
            return json.loads(val)
        return None
    except Exception as e:
        return {'error': str(e)}


def get_new_detail_tab():
    """从当前标签页列表中找 url 包含 'video/detail' 的标签，返回 (tab_id, url)"""
    pages = get_pages()
    for p in pages:
        url = p.get('url', '')
        if 'video/detail' in url:
            return p.get('id'), url
    return None, None


def extract_video_id(url):
    """从详情页 URL 中提取 video_id"""
    m = re.search(r'video_id=(\d+)', url)
    if m:
        return m.group(1)
    return None


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    print('=' * 50)
    print('🚀 抖音热点中心爬取脚本')
    print('=' * 50)

    # 1. 检查/启动专属 Chrome（端口 9223）
    print('\n[Step 1] 检查/启动专属 Chrome...')
    import os as _os
    chrome_path = _os.path.expanduser('~/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome')
    user_data = _os.path.expanduser('~/.config/chromium-hot')
    _os.makedirs(user_data, exist_ok=True)
    # 杀掉已有实例
    subprocess.run(['pkill', '-f', 'chrome.*9223'], stderr=subprocess.DEVNULL)
    time.sleep(1)
    subprocess.Popen([
        chrome_path,
        '--remote-debugging-port=9223',
        '--user-data-dir=' + user_data,
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-software-rasterizer',
        '--disable-extensions',
        '--disable-background-networking',
        '--disable-sync',
        '--disable-translate',
        '--no-first-run',
        '--metrics-recording-only',
        '--mute-audio',
        '--no-default-browser-check'
    ], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    time.sleep(5)
    if not check_chrome():
        print('❌ Chrome 启动失败')
        sys.exit(1)
    print('✅ Chrome 运行中（专属 9223）')

    # 2. 登录状态通过 user-data-dir 保持，跳过检测
    print('\n[Step 2] 跳过登录检测（使用专属 Chrome，数据持久化）')

    # 3. 打开 douhot 热点页面
    print(f'\n[Step 3] 打开 {DOUHOT_URL} ...')
    result = cdp_navigate(DOUHOT_URL)
    print(f'   导航结果: {result}')
    wait_for_load(8)

    # 确认 douhot 页面已加载（navigate 后 URL 可能还未更新，多次尝试）
    ws_url = None
    for _ in range(5):
        pages = get_pages()
        for p in pages:
            if 'douhot' in p.get('url', ''):
                ws_url = p.get('webSocketDebuggerUrl')
                break
        if ws_url:
            break
        wait_for_load(2)
    if not ws_url:
        print('❌ 无法获取 douhot 标签页 ws_url')
        sys.exit(1)
    print('✅ douhot 标签页已激活')

    # 4. 等待页面稳定
    print('\n[Step 4] 等待页面稳定...')
    wait_for_load(8)

    # 5. 收集前 10 条视频的链接
    print(f'\n[Step 7] 收集前 {MAX_VIDEOS} 条视频链接...')

    video_urls = []  # 存储所有视频链接
    ws_url = get_target_ws_url('douhot')  # 保持 douhot 页面焦点

    # 正式开始采集前，先确保表格加载好（最多刷新5次）
    print(f'\n[Step 7a] 检查表格是否加载...')
    table_count = check_table_exists(ws_url)
    if table_count == 0:
        print(f'   ⚠️ 未识别到表格，尝试刷新页面（最多5次）...')
        for retry in range(5):
            cdp_js('window.scrollTo(0, 0)', 'douhot')
            wait_for_load(1)
            cdp_js('location.reload()', 'douhot')
            wait_for_load(5)
            ws_url = get_target_ws_url('douhot')
            table_count = check_table_exists(ws_url)
            print(f'   刷新 {retry+1}/5，表格行数: {table_count}')
            if table_count > 0:
                break
        if table_count == 0:
            print('   ❌ 刷新5次后仍未识别到表格，退出脚本')
            close_browser()
            sys.exit(1)
    print(f'   ✅ 表格已加载，共 {table_count} 行')

    for i in range(MAX_VIDEOS):
        print(f'\n--- 第 {i+1}/{MAX_VIDEOS} 条视频 ---')

        # 每次循环开始时，先滚动到页面顶部，确保从头开始处理
        cdp_js('window.scrollTo(0, 0)', 'douhot')
        wait_for_load(2)

        # 确认表格行数是否足够
        if table_count <= i:
            print(f'   ⚠️ 表格只有 {table_count} 行，无法获取第 {i+1} 行，跳过')
            continue

        row_info = get_video_row_info(ws_url, i)

        if row_info is None or 'error' in row_info:
            print(f'   ⚠️ 获取行信息失败: {row_info}')
            # 尝试滚动一下再重试
            cdp_js('window.scrollBy(0, 200)', 'douhot')
            wait_for_load(2)
            row_info = get_video_row_info(ws_url, i)
            if row_info is None or 'error' in row_info:
                print('   ⚠️ 重试仍失败，跳过')
                continue

        print(f'   ✅ 成功定位第 {row_info.get("rank", "?")} 名，按钮: {row_info.get("text", "")}')

        x = row_info.get('x')
        y = row_info.get('y')
        btn_text = row_info.get('text', '')
        print(f'   按钮文本: {btn_text}，坐标: ({x:.0f}, {y:.0f})')

        # 7b+c+d. 滚动到可视区域 + CDP 鼠标点击
        print(f'   执行 CDP 鼠标点击...')
        try:
            click_at_position(ws_url, x, y)
        except Exception as e:
            print(f'   ⚠️ CDP 点击异常: {e}，跳过')
            continue

        # 7e. 等待新标签打开
        print('   等待新标签页...')
        wait_for_load(3)

        # 7f. 找到 'video/detail' 标签
        tab_id, detail_url = get_new_detail_tab()

        if not tab_id:
            print('   ⚠️ 未找到视频详情标签，跳过')
            continue

        print(f'   详情页: {detail_url[:80]}')

        # 7g. 提取 video_id
        video_id = extract_video_id(detail_url)
        if not video_id:
            print(f'   ⚠️ 无法从 URL 提取 video_id: {detail_url}')
            # 尝试直接关闭并跳过
            close_tab_by_id(tab_id)
            continue

        print(f'   video_id: {video_id}')

        # 7h. 构建标准抖音链接并收集
        douyin_url = f'https://www.douyin.com/video/{video_id}'
        print(f'   抖音链接: {douyin_url}')

        # 收集到列表中
        video_urls.append(douyin_url)
        print(f'   ✅ 已收集链接 ({len(video_urls)}/{MAX_VIDEOS})')

        # 7i. 关闭详情标签页
        close_tab_by_id(tab_id)
        print('   详情页已关闭')

        # 7j. 等待 2 秒
        wait_for_load(2)

        # 7k. 确保还在 douhot 页面，滚动到顶部准备下一条
        pages = get_pages()
        douhot_ok = any('douhot' in p.get('url', '') for p in pages)
        if not douhot_ok:
            print('   ⚠️ douhot 页面丢失，正在恢复...')
            pages = get_pages()
            if pages:
                recovery_ws = pages[-1].get('webSocketDebuggerUrl')
                if recovery_ws:
                    asyncio.run(_cdp_send_raw(recovery_ws, 'Page.navigate', {'url': DOUHOT_URL}))
            wait_for_load(8)
            ws_url = get_target_ws_url('douhot')
            if ws_url:
                print('   ✅ 页面已恢复')
            else:
                print('   ⚠️ 页面恢复失败')
        else:
            # 页面还在，滚动到顶部
            try:
                cdp_js('window.scrollTo(0, 0)', 'douhot')
            except:
                pass

    # 链接收集完毕，关闭 9223 浏览器
    print(f'\n[Step 8] 链接收集完毕，关闭浏览器...')
    close_all_tabs()
    close_browser()

    # 9. 批量调用 analyze_video.py 分析收集到的视频
    print(f'\n[Step 9] 批量分析 {len(video_urls)} 个视频...')

    processed = 0
    for idx, url in enumerate(video_urls, 1):
        print(f'\n--- 分析第 {idx}/{len(video_urls)} 个视频 ---')
        print(f'   链接: {url}')

        # 确保 CDP 9222 已启动
        if not ensure_analyze_chrome():
            print('   ⚠️ CDP 9222 启动失败，跳过该视频')
            continue

        analyze_script = os.path.join(ANALYZE_SCRIPT_DIR, 'analyze_video.py')
        try:
            result = subprocess.run(
                ['python3', analyze_script, url],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                print('   ✅ 分析完成')
                processed += 1
            else:
                print(f'   ⚠️ 分析失败: {result.stderr[:200] if result.stderr else result.stdout[:200]}')
        except subprocess.TimeoutExpired:
            print('   ⚠️ 分析超时')
        except Exception as e:
            print(f'   ⚠️ 调用异常: {e}')

        wait_for_load(2)

    # 9. 清理过期数据
    print('\n[Step 10] 清理过期数据...')
    cleanup_script = os.path.join(SCRIPT_DIR, 'cleanup_old_data.py')
    if os.path.exists(cleanup_script):
        try:
            subprocess.run(
                ['python3', cleanup_script],
                capture_output=True, text=True, timeout=60
            )
            print('✅ 清理完成')
        except Exception as e:
            print(f'⚠️ 清理异常: {e}')
    else:
        print('⚠️ cleanup_old_data.py 不存在，跳过')

    # 10. 打印完成报告
    print()
    print('=' * 50)
    print('✅ 爬取完成')
    print(f'   处理视频数: {processed}/{MAX_VIDEOS}')
    print(f'   数据文件: ~/.openclaw/workspace/doubao/sheet/scripts/data/scripts.json')
    print('=' * 50)


if __name__ == '__main__':
    main()
