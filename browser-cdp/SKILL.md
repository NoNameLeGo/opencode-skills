---
name: browser-cdp
description: Generic browser automation via Chrome DevTools Protocol (CDP) using Python websocket-client. Use when needing to control an existing Chrome/Edge browser session — reading page content, clicking elements, filling forms, extracting data, or running JS in specific frames/contexts. Use this when Playwright/Puppeteer MCP servers fail to connect, when reusing an existing logged-in browser session, or when interacting with deeply nested iframes that other tools can't reach. For site-specific selectors (e.g., chaoxing.com), see the `chaoxing-autopilot` skill. Trigger phrases: browser automation, CDP, control browser, read page, click element, fill form, extract data, websocket debugger, Chrome DevTools Protocol, 自动化浏览器, 操作页面.
---

# Browser CDP Automation

Control Chrome/Edge via Python + WebSocket. Reuse existing sessions (logged-in state), run JS in any frame/context.

## Safety Rules

- **NEVER auto-submit forms.** Fill/select answers but stop before submission. Tell user "已选好，请手动提交" or wait for user to explicitly say "提交".
- Do not click `submit`, `confirm`, or similar buttons unless user explicitly requests.

## Exam Workflow (Optional Steps)

For automated exam/quiz answering, follow this workflow. Steps marked `[optional]` depend on environment capabilities — skip if unable (e.g., no internet access).

### Step 1: Connect & Discover DOM
Connect via CDP, run DOM Discovery Pattern (below), identify page type and question structure.

### Step 2: Read All Questions
Extract question text, type (single/multi/true-false), and all options. Store in a structured list.

### Step 3: Research Answers `[optional]`
If internet access is available, search for answer keys or verified solutions. If search is unavailable, ask the user to provide answers or make best-effort selections.

### Step 4: Select Answers
Click options or call handlers. For each question:
- **Single choice**: click the matching option once
- **Multiple choice**: click each correct letter individually
- **True/false**: A = 对 (correct), B = 错 (incorrect)

### Step 5: Verify & Stop
Tell the user answers are selected. **Do not submit.** Let the user review before manually submitting.

## Launch Browser

```bash
# Edge
"& 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' --remote-debugging-port=9222 --remote-allow-origins=*"

# Chrome
"& 'C:\Program Files\Google\Chrome\Application\chrome.exe' --remote-debugging-port=9222 --remote-allow-origins=*"
```

Both flags required: `--remote-debugging-port=9222` + `--remote-allow-origins=*`

## Connect & Execute

```python
import websocket, json, urllib.request, time

# 1. Get page list
pages = json.loads(urllib.request.urlopen('http://localhost:9222/json').read())

# 2. Find target page
target = [p for p in pages if p['type'] == 'page' and 'KEYWORD' in p['url']][0]

# 3. Connect WebSocket
ws = websocket.create_connection('ws://localhost:9222/devtools/page/' + target['id'], timeout=15)

# 4. Enable Runtime (required before executing JS)
ws.send(json.dumps({'id': 1, 'method': 'Runtime.enable'}))

# 5. Collect executionContextCreated events
contexts = []
ws.settimeout(2)
try:
    while True:
        msg = json.loads(ws.recv())
        if 'params' in msg and 'context' in msg.get('params', {}):
            ctx = msg['params']['context']
            contexts.append({'id': ctx['id'], 'origin': ctx.get('origin',''), 'name': ctx.get('name','')})
except:
    pass

# 6. Pick context (usually the last one for main frame, or match by origin)
context_id = contexts[-1]['id'] if contexts else 1

# 7. Execute JS
ws.send(json.dumps({
    'id': 2,
    'method': 'Runtime.evaluate',
    'params': {
        'expression': 'document.title',
        'contextId': context_id,
        'returnByValue': True
    }
}))
result = json.loads(ws.recv())
print(result)
ws.close()
```

## Find Frame Contexts

For nested iframes, enable `Page` domain to get frame tree:

```python
ws.send(json.dumps({'id': 1, 'method': 'Page.enable'}))
# recv framesTree event
ws.send(json.dumps({'id': 2, 'method': 'Page.getFrameTree'}))
tree = json.loads(ws.recv())
# tree['result']['frameTree']['childFrames'] recursively
```

Then match frame ID to execution context via `Page.frameNavigated` or `Runtime.executionContextCreated` events.

## DOM Discovery Pattern

**Never assume selectors.** Different page types (quiz, homework, exam) use different DOM structures. Always explore first.

### Step 1: Check frame structure

```python
# Flat page (no iframes) — simpler, run JS directly
ws.send(json.dumps({'id': 1, 'method': 'Page.getFrameTree'}))
tree = json.loads(ws.recv())
has_iframes = len(tree['result']['frameTree'].get('childFrames', [])) > 0
```

### Step 2: Probe for interactive elements

Run this discovery script to find what's on the page:

```javascript
(() => {
    const result = {};

    // Question containers — try multiple patterns
    const qPatterns = ['.TiMu', '.questionLi', '.singleQuesId', '.question', '[class*="question"]'];
    for (const sel of qPatterns) {
        const els = document.querySelectorAll(sel);
        if (els.length > 0) result['questions:' + sel] = els.length;
    }

    // Clickable options — look for onclick handlers
    const clickPatterns = ['li[onclick]', 'div[onclick]', 'label[onclick]', '[role="checkbox"]', '[role="radio"]'];
    for (const sel of clickPatterns) {
        const els = document.querySelectorAll(sel);
        if (els.length > 0) result['clicks:' + sel] = els.length;
    }

    // Answer storage
    const answerInputs = document.querySelectorAll('input[name*="answer"], input[id*="answer"]');
    result['answerInputs'] = answerInputs.length;

    // Rich text editors
    result['ueditor'] = document.querySelectorAll('iframe[id*="ueditor"]').length;
    result['contenteditable'] = document.querySelectorAll('[contenteditable]').length;

    return JSON.stringify(result, null, 2);
})()
```

### Step 3: Inspect one element's structure

Once you find clickable options, get one element's HTML to understand the pattern:

```javascript
// Get first option's parent structure
const el = document.querySelector('li[onclick], div[onclick]');
el ? el.parentElement.outerHTML.substring(0, 2000) : 'none found'
```

### Step 4: Identify the click handler

Check what function the onclick calls:

```javascript
const el = document.querySelector('[onclick]');
el?.getAttribute('onclick')  // e.g., "addChoice(this)" or "addMultipleChoice(this)"
```

The handler name tells you the interaction model (single-select vs multi-select).

## Nested Iframe Access

When content is inside deeply nested iframes (e.g., chaoxing quiz pages), isolated worlds and `Runtime.evaluate` with `contextId` often fail. **Traverse via `contentDocument` from the main page instead.**

### Pattern: DOM Traversal

```python
js = r"""(() => {
    // Step down through iframe layers
    const f1 = document.getElementById('iframe');           // or querySelector('iframe[src*="..."]')
    const d1 = f1.contentDocument || f1.contentWindow.document;
    const f2 = d1.querySelector('iframe[src*="work/index.html"]');
    const d2 = f2.contentDocument || f2.contentWindow.document;
    const f3 = d2.querySelector('iframe[name="frame_content"]');
    const doc = f3.contentDocument || f3.contentWindow.document;

    // Now `doc` is the quiz DOM — query it normally
    return doc.getElementsByClassName('TiMu').length;
})()"""
```

### Calling Functions in Iframe

Functions like `addChoice()` live on the **iframe's `contentWindow`**, not the parent. Call them explicitly:

```python
js = r"""(() => {
    // ... traverse to get contentWin and doc (see above) ...
    const contentWin = f3.contentWindow;

    const opt = doc.querySelector('span[data="A"]').closest('[onclick]');
    contentWin.addChoice(opt);        // NOT addChoice(opt)
    return 'clicked A';
})()"""
```

**Key**: `.click()` may not trigger jQuery event handlers. Call the function directly via `contentWin.addChoice(el)` or `contentWin.addMultipleChoice(el)`.

### Finding the Right Frame

Use `Page.getFrameTree` to identify which frame contains the content:

```python
ws.send(json.dumps({'id': 1, 'method': 'Page.getFrameTree'}))
tree = json.loads(ws.recv())

def walk(t, depth=0):
    f = t['frame']
    if 'doHomeWorkNew' in f.get('url', '') or 'work' in f.get('url', ''):
        print(f"QUIZ FRAME: {f['id']}  url={f['url'][:100]}")
    for child in t.get('childFrames', []):
        walk(child, depth + 1)

walk(tree['result']['frameTree'])
```

Then use the frame ID to verify via traversal, not via isolated worlds.

## Click Elements

Always click the element with the event handler, not its children:

```javascript
// Find element by its data attribute, then click the PARENT with onclick
const option = document.querySelector('span[data="A"]');
const clickable = option.closest('[onclick]');  // go up to find handler
clickable.click();
```

**Key rule**: If a `<div>` or `<li>` has `onclick`, click that element — not the `<span>` or `<p>` inside it. Children without handlers won't trigger the action.

**Better approach**: Call the handler function directly instead of `.click()`:
```javascript
// Instead of: clickable.click()
// Do:
addChoice(clickable);           // single-choice
addMultipleChoice(clickable);   // multiple-choice
```

## Gotchas — Universal

| Issue | Fix |
|-------|-----|
| 403 Forbidden on WebSocket | Add `--remote-allow-origins=*` flag |
| GBK encoding error (Windows) | Run `sys.stdout.reconfigure(encoding='utf-8')` at script start |
| Can't find frame context | Call `Runtime.enable` first, collect events with `ws.settimeout(2)` loop |
| MCP tools timeout/fail | Use Python `websocket-client` directly — more reliable for custom setups |
| Clicking option doesn't select it | Call handler directly: `addChoice(el)` not `.click()` |
| Answer not updating | Check hidden `<input>` — some pages store answers there, not in the clicked element |
| `Page.createIsolatedWorld` returns context but DOM is empty | Isolated worlds can't access DOM. Use `contentDocument` traversal instead |
| Function not found when calling in iframe | Use `contentWin.addChoice(el)` — functions live on iframe's `contentWindow` |
| `data` attribute doesn't match expected value (A/B/C/D) | Anti-cheat scrambling — match by `textContent.trim()` instead of `data` attribute |

**Rule**: Run the DOM Discovery script first. Don't reuse selectors from a different page type. For site-specific selectors (e.g., chaoxing.com), see the `chaoxing-autopilot` skill.

## Install Dependency

```bash
pip install websocket-client
```
