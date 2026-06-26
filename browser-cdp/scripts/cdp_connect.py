#!/usr/bin/env python3
"""
CDP Connection Template

Reusable script for connecting to Chrome/Edge via CDP WebSocket.
Customize KEYWORD and the JS expression to match your target page.
"""
import sys
import json
import time
import urllib.request

try:
    import websocket
except ImportError:
    print("pip install websocket-client")
    sys.exit(1)

# Windows UTF-8
sys.stdout.reconfigure(encoding='utf-8')

KEYWORD = 'mooc1.chaoxing.com'  # <-- Change this

# Get pages
pages = json.loads(urllib.request.urlopen('http://localhost:9222/json').read())
target = [p for p in pages if p['type'] == 'page' and KEYWORD in p['url']]

if not target:
    print(f"No page matching '{KEYWORD}'")
    sys.exit(1)

print(f"Connecting to: {target[0]['url'][:80]}...")
ws = websocket.create_connection('ws://localhost:9222/devtools/page/' + target[0]['id'], timeout=15)

# Enable Runtime + collect contexts
ws.send(json.dumps({'id': 1, 'method': 'Runtime.enable'}))

contexts = []
ws.settimeout(2)
try:
    while True:
        msg = json.loads(ws.recv())
        if 'params' in msg and 'context' in msg.get('params', {}):
            ctx = msg['params']['context']
            contexts.append({'id': ctx['id'], 'origin': ctx.get('origin', ''), 'name': ctx.get('name', '')})
except Exception:
    pass

print(f"Found {len(contexts)} execution context(s):")
for c in contexts:
    print(f"  ctx={c['id']} origin={c['origin'][:60]} name={c['name']}")

# Execute JS in last context (main frame)
if contexts:
    ctx_id = contexts[-1]['id']
    ws.send(json.dumps({
        'id': 2,
        'method': 'Runtime.evaluate',
        'params': {
            'expression': 'document.title',
            'contextId': ctx_id,
            'returnByValue': True
        }
    }))
    result = json.loads(ws.recv())
    print(f"Page title: {result.get('result', {}).get('result', {}).get('value', 'N/A')}")

ws.close()
print("Done.")
