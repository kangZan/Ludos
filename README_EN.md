# Ludos — Character-Driven Narrative Deduction Agent

A LangGraph-based multi-agent narrative deduction system for fiction writing assistance.

中文版本: [README.md](README.md)

## Core Features

- **Autonomous characters**: Each character decides based on its own dossier instead of author-imposed plot
- **Cognition traffic light**: Strict information isolation so characters only use what they know
- **Secret pressure system**: Secrets surface organically through dialogue rather than mechanical triggers
- **Non-numeric conflict**: Qualitative, literary resolution instead of numeric checks
- **Three-stage architecture**: Initialization → autonomous deduction loop → literary polishing

## Quick Start

### Environment Setup

```bash
# Create conda environment
conda create -n ludos python=3.12 -y
conda activate ludos

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and fill in your LLM API Key
```

### Health Check

```bash
# Basic health check (includes LLM connectivity)
python -m src.main --health

# Health check via launcher script
python scripts/run.py --health
```

### Plugin Tool Registration

Use environment variable `TOOL_PLUGINS` with comma-separated module paths. Tools must be registered on import.

Example:
```bash
export TOOL_PLUGINS=plugins.tools.extra,plugins.tools.more
```

Register tools inside your plugin module:
```python
from src.tools.registry import register_tool

def my_tool(x: str) -> str:
    return x.upper()

register_tool("my_tool", my_tool)
```

### Run

```bash
# Input from file
python -m src.main input.txt --output result.md

# Input from stdin
echo "your narrative outline..." | python -m src.main

# Use launcher script (includes environment check)
python scripts/run.py input.txt
```

### Runtime Logs and Character Memory

Two kinds of logs are generated:

- Public broadcast log: `logs/session_<id>.public.log`
- Raw interaction log: `logs/session_<id>.raw.log`

Watch the public broadcast log in real time:

```bash
tail -f logs/session_<id>.public.log
```

Each character maintains a memory file (semi-structured protocol):

```
data/characters/<session_id>/<character_id>.mem.txt
```

### Example (Excerpt: session `3cbd2932`)

> Purpose: show the minimal “input → process docs → output” loop. All snippets below are excerpts, not full content.

Input (narrative outline file, omitted):

Process docs (public log, excerpt, from `logs/session_3cbd2932.public.log`):
```text
[场景：**时间：** 无明确时间标识，空间内弥漫的灰雾未呈现昼夜变化，时间流速难以感知。 ...]
[角色-王信球（上首身影）] [说话] "“此处的访客，欢迎你们。你们的祈祷……已在此处得到响应。”"
[角色-李梓萌（右侧下首身影）] [说话] "（声音尽量保持平稳，但带着一丝不易察觉的激动与敬畏）伟大的存在，感谢您的响应与接纳。..."
```

Process docs (raw interaction log, excerpt, from the “Raw Interaction Log” section in `result.md`):
```text
[场景：时间：感知不明，无昼夜变化。地点：无垠灰雾中的古老宫殿内部。中央的青铜长桌与高背椅构成场景焦点。...]
[角色-王信球（上首身影）] [动作] 维持端坐的姿态，被灰雾包裹的轮廓似乎更加稳定、凝实了一些。... [说话] "“此处的访客，欢迎你们。你们的祈祷……已在此处得到响应。”"
[角色-李梓萌（右侧下首身影）] [动作] 身体在椅子上微微前倾，做出一个恭敬倾听的姿态... [说话] "（声音尽量保持平稳，但带着一丝不易察觉的激动与敬畏）伟大的存在，感谢您的响应与接纳。..."
```

Process docs (character memory, excerpt, from `data/characters/3cbd2932/李梓萌（右侧下首身影）.mem.txt`):
```text
[GOALS]
李梓萌（右侧下首身影）_goal_0|active|向上首身影表达恰当的敬意与感激之情，试探性地询问此次会面的缘由或目的，以确认其安全性。
李梓萌（右侧下首身影）_goal_1|active|优雅地介绍自己（可隐去真名但表明身份阶层），并含蓄地表达对神秘知识的渴求，观察“主宰者”的反应。

[STABLE]
身份：一名对神秘世界充满向往但苦无门路的贵族少女。我正在进行的冥想似乎引来了超乎想象的回应。
私人理解：灰雾、古老宫殿、神秘的青铜桌……这和我读过的隐秘典籍描述的场景如此相似！
```

Output (polished narrative, excerpt, from `result.md`):
```text
无垠的灰雾如亘古的帷幕，笼罩着寂静的宫殿。稀薄的雾气在空气中缓缓流转，恒定不变，仿佛时间在此失去了刻度。
宫殿中央，青铜长桌与高背椅是这片混沌中唯一确切的焦点。
桌面上，古老而繁复的纹路镌刻其中，持续散发着非自然的、微弱的光晕，像沉睡巨兽皮肤下缓慢流淌的血液。
```

### Tests

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=term-missing
```

## Architecture Overview

```
User input (narrative outline)
        ↓
  [Initialization] Parse into structured JSON → seed character memory
        ↓
  [Deduction Loop] Scene announcement → character turns → pressure updates → round assessment
        ↓  (loop until end condition is met)
  [Polishing] Raw log file → literary narrative
        ↓
  Output: raw interaction log + polished narrative
```

### Public/Private Memory Flow (Sketch)

```
           ┌──────────────────────────────┐
           │          Moderator           │
           │  - Scene announcements       │
           │  - Public interaction log    │
           │  - Public memory maintenance │
           └───────────────┬──────────────┘
                           │ Public broadcast
                           ▼
┌───────────────────────────────────────────────────────────┐
│                    Public Log (public.log)                │
└───────────────┬───────────────────────────────────────────┘
                │ Append-only
                ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│ Character A private memory    │    │ Character B private memory   │
│ (mem.txt)                     │    │ (mem.txt)                    │
│ - Stable memory               │    │ - Stable memory              │
│ - Working memory              │    │ - Working memory             │
│ - Goals/Secrets/Pressure      │    │ - Goals/Secrets/Pressure     │
└───────────────┬──────────────┘    └───────────────┬──────────────┘
                │                                   │
                └──────────────┬────────────────────┘
                               ▼
                      Character outward actions
                               │
                               ▼
                     Moderator relays to public info
```

## Project Structure

```
src/
├── config/     # Configuration and prompt templates
├── models/     # Domain types and Pydantic models
├── agents/     # Agents (moderator/character/polisher)
├── graphs/     # LangGraph definitions
├── tools/      # Tooling (info filter/pressure tracker, etc.)
├── memory/     # Persistence
└── utils/      # Utilities
```

## Docs

- [Architecture](doc/v0.1.0/design.md)
- [API](doc/v0.1.0/api.md)
- [Changelog](doc/v0.1.0/changelog.md)
- [Parallel Decision Optimization Plan](doc/v0.1.0/并行决策优化计划.md)
- [World Knowledge Layering Plan](doc/v0.1.0/world_knowledge_plan.md)

## License

MIT

## Refactor Notes

Completed:
- Semi-structured character memory protocol (no JSON parsing dependency)
- Moderator only maintains public broadcast and public interaction logs
- Raw interaction log is persisted during runtime and used for polishing
- Characters own goal states and secret pressure values (removed from global state)
- Moderator assessment is based only on public log summaries, without reading private memory

Next steps:
1. Parallel decision optimization (parallel intent collection → moderator adjudication → failure notifications). See `doc/v0.1.0/并行决策优化计划.md`.
1. Add a “micro action” field to character outward interaction, to capture subtle goal-directed behavior.
2. Moderator maintains micro-action memory and later determines whether others discover it.
3. This mechanism is complex; it is recorded as a plan and will be implemented incrementally.
