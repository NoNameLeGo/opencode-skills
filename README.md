# OpenCode Skills

OpenCode (opencode.ai) agent skill collection. Browser automation, exam helpers, and more.

## Skills

| Skill | Description |
|-------|-------------|
| `browser-cdp` | Chrome DevTools Protocol automation via Python websocket-client |
| `chaoxing-autopilot` | 超星学习通自动答题 (quiz/homework/exam) |

## Installation

### Prerequisites

- [OpenCode](https://opencode.ai) installed
- Python 3.8+
- Edge or Chrome browser

### Install skills

Clone this repo into your OpenCode skills directory:

```bash
# Find your skills directory
# Usually: ~/.config/opencode/skills/ or <project>/.opencode/skills/

# Option 1: Clone to global skills
git clone https://github.com/NoNameLeGo/opencode-skills.git ~/.config/opencode/skills/opencode-skills

# Option 2: Clone to project-local skills
git clone https://github.com/NoNameLeGo/opencode-skills.git /path/to/your/project/.opencode/skills/opencode-skills
```

### Install dependencies

```bash
pip install websocket-client
```

### Enable in OpenCode

Add the skill paths to your `opencode.json`:

```json
{
  "skills": [
    ".opencode/skills/opencode-skills/.opencode/skills/browser-cdp",
    ".opencode/skills/opencode-skills/.opencode/skills/chaoxing-autopilot"
  ]
}
```

## Usage

### browser-cdp

Launch browser with remote debugging:

```bash
# Edge (default)
"& 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' --remote-debugging-port=9222 --remote-allow-origins=*"
```

Then ask OpenCode to automate: "用 browser-cdp 读取页面内容" or "fill the login form".

### chaoxing-autopilot

Navigate to a quiz/homework/exam page on chaoxing.com, then ask OpenCode:

- "自动答题" — discovers DOM, reads questions, selects answers
- "选答案" — select specific answers

**Safety**: Answers are selected but never auto-submitted. You review and submit manually.

## License

[GPL-3.0](LICENSE)
