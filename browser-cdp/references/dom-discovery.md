# DOM Discovery Patterns

General-purpose patterns for exploring unknown page structures via CDP.

## Probe Page Structure

Run this to quickly understand what's on the page:

```python
expr = """
(() => {
    const r = {};
    // Containers
    ['TiMu', 'questionLi', 'singleQuesId', 'question'].forEach(c => {
        const n = document.querySelectorAll('.' + c).length;
        if (n) r[c] = n;
    });
    // Clickable elements
    ['li[onclick]', 'div[onclick]', 'label[onclick]'].forEach(s => {
        const n = document.querySelectorAll(s).length;
        if (n) r[s] = n;
    });
    // Answer storage
    r['answerInputs'] = document.querySelectorAll('input[id*="answer"], input[name*="answer"]').length;
    r['editors'] = document.querySelectorAll('iframe[id*="ueditor"], [contenteditable]').length;
    r['iframes'] = document.querySelectorAll('iframe').length;
    return JSON.stringify(r);
})()
"""
```

## Discover Option Structure

Once you find clickable elements, inspect one to understand the pattern:

```python
expr = """
(() => {
    const el = document.querySelector('li[onclick], div[onclick]');
    if (!el) return 'no clickable options found';
    return JSON.stringify({
        tag: el.tagName,
        onclick: el.getAttribute('onclick'),
        classes: el.className,
        parentTag: el.parentElement.tagName,
        parentClass: el.parentElement.className,
        optionLetters: [...el.querySelectorAll('[data]')].map(s => s.dataset),
        outerHTML: el.outerHTML.substring(0, 800)
    }, null, 2);
})()
"""
```

## Find All Question Types

```python
expr = """
(() => {
    const questions = document.querySelectorAll('.TiMu, .questionLi, .singleQuesId');
    return JSON.stringify(Array.from(questions).map((q, i) => ({
        idx: i + 1,
        id: q.id,
        classes: q.className.substring(0, 60),
        type: q.getAttribute('typename') || q.querySelector('[class*="type"]')?.textContent || '',
        hasRadio: !!q.querySelector('input[type=radio"]'),
        hasCheckbox: !!q.querySelector('input[type=checkbox"]'),
        hasEditor: !!q.querySelector('iframe, [contenteditable]'),
        optionCount: q.querySelectorAll('li[onclick], div[onclick]').length
    })));
})()
"""
```

## Click Options by Letter

Find option by text content (not `data` attribute — may be scrambled by anti-cheat):

```python
expr = """
(() => {
    const letter = 'A';  // change as needed
    // Match by textContent, not data attribute (data may be scrambled)
    const spans = document.querySelectorAll('.num_option, .num_option_dx');
    const span = Array.from(spans).find(s => s.textContent.trim() === letter);
    if (!span) return 'option not found';
    const clickable = span.closest('[onclick]');
    if (!clickable) return 'no clickable parent found';
    clickable.click();
    return 'clicked ' + letter;
})()
"""
```

For exam/quiz pages, `.click()` on the parent div works. For iframe-based pages, call `contentWin.addChoice(el)` instead. For site-specific patterns, see the `chaoxing-autopilot` skill.

## Click All Options (for pre-selecting)

```python
expr = """
(() => {
    document.querySelectorAll('li[onclick], div[onclick]').forEach(el => el.click());
    return 'clicked all options';
})()
"""
```

## Read All Questions & Options

```python
expr = """
(() => {
    const questions = document.querySelectorAll('.TiMu, .questionLi, .singleQuesId');
    return JSON.stringify(Array.from(questions).map((q, i) => {
        const title = q.querySelector('h3, .mark_name, .Zy_TItile');
        const options = q.querySelectorAll('li[onclick], div[onclick]');
        return {
            idx: i + 1,
            title: title?.textContent?.trim().substring(0, 100),
            options: Array.from(options).map(o => {
                const letter = o.querySelector('[data]')?.getAttribute('data');
                const text = o.querySelector('.answer_p, p')?.textContent?.trim();
                return { letter, text: text?.substring(0, 80) };
            })
        };
    }));
})()
"""
```

## Set Rich Text (UEditor)

For fill-in-the-blank questions using UEditor (common in chaoxing.com):

```python
expr = """
var editor = UE.instants['ueditor1'];
if (editor) { editor.setContent('<p>answer text</p>'); 'set'; } else { 'no editor found'; }
"""
```

For chaoxing.com-specific patterns, see the `chaoxing-autopilot` skill.

## Check Answer Storage

See how answers are stored after clicking:

```python
expr = """
(() => {
    const inputs = document.querySelectorAll('input[id*="answer"], input[name*="answer"]');
    return JSON.stringify(Array.from(inputs).map(i => ({
        id: i.id,
        name: i.name,
        value: i.value
    })));
})()
"""
```

## Navigate iframe Tree

```python
ws.send(json.dumps({'id': 1, 'method': 'Page.getFrameTree'}))
tree = json.loads(ws.recv())

def walk(t, depth=0):
    f = t['frame']
    print('  ' * depth + f['id'][:20] + '... name=' + f.get('name','') + ' url=' + f['url'][:80])
    for child in t.get('childFrames', []):
        walk(child, depth + 1)

walk(tree['result']['frameTree'])
```

## Access Nested Iframes via DOM Traversal

When isolated worlds or `contextId` evaluation fails, traverse the iframe tree via `contentDocument` from the main page:

```python
expr = r"""(() => {
    // Layer 1: main page → knowledge cards iframe
    const f1 = document.getElementById('iframe');
    if (!f1) return 'layer1 not found';
    const d1 = f1.contentDocument || f1.contentWindow.document;

    // Layer 2: knowledge cards → work module
    const f2 = d1.querySelector('iframe[src*="work/index.html"]');
    if (!f2) return 'layer2 not found';
    const d2 = f2.contentDocument || f2.contentWindow.document;

    // Layer 3: work module → content frame (quiz/homework)
    const f3 = d2.querySelector('iframe[name="frame_content"]');
    if (!f3) return 'layer3 not found';
    const doc = f3.contentDocument || f3.contentWindow.document;

    // Now query `doc` like any normal document
    return JSON.stringify({
        questions: doc.getElementsByClassName('TiMu').length,
        divOnclick: doc.querySelectorAll('div[onclick]').length,
        liOnclick: doc.querySelectorAll('li[onclick]').length,
        title: doc.title
    });
})()"""
```

## Call Functions in Iframe Context

Functions like `addChoice()` and `addMultipleChoice()` live on the iframe's `contentWindow`. Must call them explicitly:

```python
expr = r"""(() => {
    // ... traverse to get f3 (the iframe) and doc (its document) ...
    const contentWin = f3.contentWindow;

    // Find option by letter
    const span = doc.querySelector('span[data="C"]');
    const opt = span.closest('[onclick]');

    // Call the handler from the iframe's window
    contentWin.addChoice(opt);           // single-choice
    // contentWin.addMultipleChoice(opt); // multiple-choice

    // Verify via hidden input
    const input = doc.querySelector('input[id^="answer"]');
    return input.id + '=' + input.value;
})()"""
```

**Why not `.click()`?** jQuery-bound event handlers may not fire from synthetic clicks. Calling the function directly is reliable.

## Access Nested Iframes via DOM Traversal (Generic Pattern)

When isolated worlds or `contextId` evaluation fails, traverse the iframe tree via `contentDocument` from the main page:

```python
expr = r"""(() => {
    // Generic: find iframes by id or src pattern
    const frames = document.querySelectorAll('iframe');
    if (frames.length === 0) return 'no iframes found';

    // Try traversing to the deepest frame
    let doc = document;
    let depth = 0;
    while (depth < 5) {
        const f = doc.querySelector('iframe');
        if (!f) break;
        doc = f.contentDocument || f.contentWindow.document;
        depth++;
    }

    // Now query `doc` like any normal document
    return JSON.stringify({
        title: doc.title,
        bodyLength: doc.body?.innerHTML?.length || 0
    });
})()"""
```
