---
name: chaoxing-autopilot
description: 超星学习通自动答题技能。通过 CDP 控制浏览器，在超星学习通的测验、作业、考试页面自动选择答案。包含页面 DOM 结构、anti-cheat 机制、iframe 穿越、答案选择模板等。依赖 browser-cdp skill 的基础连接能力。触发词：超星, 学习通, chaoxing, 自动答题, 选答案, 考试, 测验, 作业.
---

# 超星学习通自动答题

超星学习通 (chaoxing.com) 专用 DOM 选择器和答题模板。需要配合 `browser-cdp` skill 使用。**默认用 Edge 浏览器**，除非用户明确要求 Chrome。

## Safety Rules

- **永远不要自动提交。** 选完答案后告诉用户"已选好，请手动提交"。
- 不要点击 `submit`、`confirm` 等按钮，除非用户明确要求。

## 三种页面类型

| 页面 | URL 特征 | 容器 class | 有无 iframe |
|------|----------|------------|-------------|
| 测验 (Quiz) | `mycourse/studentstudy` + `doHomeWorkNew` | `.TiMu` | 3层嵌套 |
| 作业 (Homework) | `dowork` | `.singleQuesId` / `.questionLi` | 无 |
| 考试 (Exam) | `exam-ans/mooc2/exam` | `.singleQuesId` | 无 |

**每次先跑 DOM Discovery 确认页面类型，不要复用其他页面的 selector。**

## 测验页面 (Quiz)

### DOM 结构
- 容器: `.TiMu` 元素
- 选项: `<ul class="Zy_ulTop">` → `<li onclick="addChoice(this);">`
- 选项字母: `<span class="num_option" data="A">`
- **注意**: UL class 是 `Zy_ulTop` 不是 `Zy_ulBottom`

### Iframe 穿越 (3层)
```
main page → #iframe (knowledge/cards) → iframe[src*="work/index.html"] → iframe[name="frame_content"]
```

必须用 `contentDocument` 穿越，不能用 isolated world。

### 答案选择
```python
js = r"""(() => {
    // 穿越 iframe (参考 browser-cdp 的 Nested Iframe Access)
    const f3 = ...; // 第3层 iframe
    const doc = f3.contentDocument;
    const contentWin = f3.contentWindow;

    // 单选: 找到选项字母，点击父元素
    const span = doc.querySelector('span[data="A"]');
    const opt = span.closest('[onclick]');
    contentWin.addChoice(opt);  // 必须用 contentWin 调用

    // 多选: 逐个点击
    for (const ch of 'ABCD') {
        const s = doc.querySelector('span[data="' + ch + '"]');
        if (s) contentWin.addMultipleChoice(s.closest('[onclick]'));
    }
    return 'done';
})()"""
```

### 填空题 (UEditor)
```python
js = """var editor = UE.instants['ueditor1'];
if (editor) { editor.setContent('<p>答案文本</p>'); 'set'; } else { 'no editor'; }"""
```

## 作业页面 (Homework)

### DOM 结构
- 容器: `.singleQuesId` 或 `.questionLi`
- 选项: `<div onclick="addMultipleChoice(this);">` (不是 `<li>`)
- 选项字母: `<span class="num_option_dx" data="A">` (注意 `_dx` 后缀)
- 无 iframe — 扁平 DOM
- 可能有 5 个选项 (A-E)
- 答案存储: 隐藏 `<input id="answer{id}">`，默认 "ABCD"

### 答案选择
```python
js = """(() => {
    const questions = document.querySelectorAll('.singleQuesId');
    // 按索引选答案
    const answers = {0: 'A', 1: 'BC', 2: 'D'};
    for (const [idx, ans] of Object.entries(answers)) {
        const q = questions[parseInt(idx)];
        if (!q) continue;
        const spans = q.querySelectorAll('.num_option_dx');
        for (const ch of ans) {
            const span = Array.from(spans).find(s => s.textContent.trim() === ch);
            if (span) span.closest('[onclick]').click();
        }
    }
    return 'done';
})()"""
```

## 考试页面 (Exam)

### DOM 结构
- 容器: `.singleQuesId`
- 题目标签: `.mark_name` — 格式: `N. (单选题/多选题/判断题, X.X 分)`
- 选项容器: `div.clearfix.answerBg` 带 onclick
- **单选**: `onclick="saveSingleSelect(this,'{qid}')"` — span class `num_option`
- **多选**: `onclick="clickSaveMultiSelect(this,'qid')"` — span class `num_option_dx` (不是 `num_option`)
- **判断**: 同单选 (`saveSingleSelect`)，A=对, B=错
- `.click()` 在 `div.answerBg` 上可直接触发 onclick

### Anti-cheat 机制
- `data` 属性是**混淆的** — 不要用 `data` 匹配！
- **必须用 `textContent.trim()` 匹配选项字母**
- 例如: `<span data="D" class="num_option">C</span>` — 显示 C 但 data 是 D

### 答案选择
```python
js = """(() => {
    const answers = {
        0: 'A',    // Q1 单选
        15: 'ABCD', // Q16 多选
        35: 'B',    // Q36 判断 (A=对 B=错)
    };
    const questions = document.querySelectorAll('.singleQuesId');
    let clicked = 0;
    for (const [idx, ans] of Object.entries(answers)) {
        const q = questions[parseInt(idx)];
        if (!q) continue;
        const spans = q.querySelectorAll('.num_option, .num_option_dx');
        if (ans.length === 1) {
            const span = Array.from(spans).find(s => s.textContent.trim() === ans);
            if (span) { span.closest('[onclick]').click(); clicked++; }
        } else {
            for (const ch of ans) {
                const span = Array.from(spans).find(s => s.textContent.trim() === ch);
                if (span) { span.closest('[onclick]').click(); clicked++; }
            }
        }
    }
    return 'clicked ' + clicked + ' options';
})()"""
```

## Gotchas

| 问题 | 解决 |
|------|------|
| 点击 span 没反应 | 必须点击有 onclick 的父元素 (`li` 或 `div`) |
| `data` 属性值不对 | anti-cheat 混淆，用 `textContent.trim()` 匹配 |
| 测验页面 iframe 穿越失败 | 用 `contentDocument`，不用 isolated world |
| iframe 内函数找不到 | 用 `contentWin.addChoice(el)`，函数在 contentWindow 上 |
| `.click()` 不触发选中 | 测验页面用 `contentWin.addChoice(el)`；考试页面 `.click()` 可用 |
| 多选题 span class 不同 | 单选用 `num_option`，多选用 `num_option_dx`，两个都查 |
| 答案没保存到 hidden input | 检查 `input[id*="answer"]` 的 value |
| 页面刷新后答案丢失 | 答案是临时状态，刷新会清空，选完不要刷新 |
