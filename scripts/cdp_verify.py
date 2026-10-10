# -*- coding: utf-8 -*-
"""
用 Chrome DevTools Protocol 做真实交互验证
==========================================
目的：验证「切换年份下拉框 → 各图表自动刷新」这条链路在真实浏览器里成立。

做法：
    1. 启动带 --remote-debugging-port 的 headless Chrome
    2. 通过 CDP 打开大屏页面
    3. 读取切换前的指标卡数字
    4. 用 Runtime.evaluate 把年份下拉框改成 2021 并派发 change 事件
       （等价于用户真实操作，会触发 Vue 的 v-model 与 watch）
    5. 等待图表重新渲染后，再次读取指标卡数字
    6. 对比两次结果并各截一张图

依赖：websockets（Python 3.12 环境已装）
"""
import asyncio
import base64
import json
import subprocess
import sys
import time
import urllib.request

import websockets

CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 9333
SHOT_DIR = r'C:\Users\QK\WorkBuddy\2026-09-23-20-41-43\shot'
URL = 'http://127.0.0.1:5173/'


async def main():
    # ---------- 1. 启动 headless Chrome 并开启调试端口 ----------
    proc = subprocess.Popen([
        CHROME, '--headless=new', '--disable-gpu', '--no-sandbox', '--no-first-run',
        '--disable-extensions', '--hide-scrollbars',
        '--user-data-dir=' + SHOT_DIR + r'\cdp-profile',
        '--window-size=1920,1080',
        '--remote-debugging-port=' + str(PORT),
        'about:blank',
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        # ---------- 2. 等待调试端口就绪，取 target ----------
        ws_url = None
        for _ in range(30):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json', timeout=3) as r:
                    targets = json.load(r)
                pages = [t for t in targets if t.get('type') == 'page']
                if pages:
                    ws_url = pages[0]['webSocketDebuggerUrl']
                    break
            except Exception:
                continue

        if not ws_url:
            print('✗ 无法连接 Chrome 调试端口')
            return 1

        async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
            msg_id = 0

            async def send(method, params=None):
                nonlocal msg_id
                msg_id += 1
                await ws.send(json.dumps({'id': msg_id, 'method': method, 'params': params or {}}))
                while True:
                    data = json.loads(await ws.recv())
                    if data.get('id') == msg_id:
                        return data.get('result', {})

            async def evaluate(expr):
                r = await send('Runtime.evaluate', {
                    'expression': expr, 'returnByValue': True, 'awaitPromise': True,
                })
                return r.get('result', {}).get('value')

            async def screenshot(name):
                r = await send('Page.captureScreenshot', {'format': 'png'})
                path = SHOT_DIR + '\\' + name
                with open(path, 'wb') as f:
                    f.write(base64.b64decode(r['data']))
                return path

            await send('Page.enable')
            await send('Runtime.enable')

            # ---------- 3. 打开页面 ----------
            await send('Page.navigate', {'url': URL})
            await asyncio.sleep(9)   # 等 Vue 挂载 + 5 个 ECharts 渲染 + 接口返回

            # 读取当前状态
            read_cards = """
            (() => {
              const nums = [...document.querySelectorAll('.card-number')].map(e => e.textContent.trim());
              const sel = document.querySelector('.year-select');
              const canvas = document.querySelectorAll('canvas').length;
              return JSON.stringify({ year: sel ? sel.value : null, nums, canvas });
            })()
            """
            before = json.loads(await evaluate(read_cards))
            print('切换到之前：')
            print('  下拉框年份 =', before['year'])
            print('  指标卡     =', before['nums'])
            print('  canvas 数  =', before['canvas'])
            p1 = await screenshot('before-switch.png')

            # ---------- 4. 真实交互：改成 2021 并派发 change ----------
            print()
            print('执行交互：把下拉框改为 2021 并触发 change 事件 ...')
            switch = """
            (() => {
              const sel = document.querySelector('.year-select');
              if (!sel) return 'NO_SELECT';
              sel.value = '2021';
              sel.dispatchEvent(new Event('change', { bubbles: true }));
              return 'OK';
            })()
            """
            r = await evaluate(switch)
            print('  交互结果 =', r)
            await asyncio.sleep(6)   # 等各组件重新请求 + 重绘

            after = json.loads(await evaluate(read_cards))
            print()
            print('切换到之后（2021）：')
            print('  下拉框年份 =', after['year'])
            print('  指标卡     =', after['nums'])
            print('  canvas 数  =', after['canvas'])
            p2 = await screenshot('after-switch-2021.png')

            # ---------- 5. 结论 ----------
            print()
            print('=' * 56)
            changed = before['nums'] != after['nums']
            year_ok = after['year'] == '2021'
            canvas_ok = after['canvas'] == 5
            print('下拉框已切到 2021        ：', '✓' if year_ok else '✗')
            print('指标卡数字发生变化       ：', '✓' if changed else '✗')
            print('  切换前：', before['nums'])
            print('  切换后：', after['nums'])
            print('图表容器仍为 5 个 canvas ：', '✓' if canvas_ok else f"✗ ({after['canvas']})")
            print()
            print('截图1（切换前 2025）：', p1)
            print('截图2（切换后 2021）：', p2)
            print('=' * 56)
            print('结论：' + ('年份切换确实会驱动各图表刷新 ✓' if (year_ok and changed and canvas_ok) else '存在问题 ✗'))
            return 0 if (year_ok and changed and canvas_ok) else 1
    finally:
        proc.terminate()


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
