# Ludos v0.1.0 API 文档

## CLI 使用

```bash
# 从文件输入
ludos input.txt --output result.md

# 从标准输入
cat narrative.txt | ludos --output result.md

# 指定会话ID（用于恢复）
ludos input.txt --session-id my-session-01
```

## 核心模块 API

### `src.graphs.orchestrator`

#### `build_orchestrator_graph(checkpointer=None) -> CompiledStateGraph`
构建并编译顶层编排图。

**参数:**
- `checkpointer`: 可选的状态持久化器，默认使用 `InMemorySaver`

**返回:** 编译后的 LangGraph 图

### `src.main`

#### `async run_deduction(narrative_text, session_id=None) -> dict`
运行完整的叙事推演会话。

**参数:**
- `narrative_text`: 叙事纲要文本
- `session_id`: 可选的会话ID

**返回:** 包含 `raw_interaction_log` 和 `polished_narrative` 的字典

### `src.agents.moderator`

#### `async parse_narrative(outline: str) -> dict`
将叙事纲要解析为结构化 JSON。

#### `async announce_scene(...) -> dict`
生成场景播报。

#### `async determine_turn_order(...) -> list[str]`
决定回合中角色行动顺序。

#### `async assess_round(...) -> dict`
评估回合进展。

### `src.agents.character`

#### `async decide_action(...) -> ActionPack`
角色自主决策，输出行动包。

### `src.agents.polisher`

#### `async polish_narrative(...) -> str`
将原始交互日志润色为文学叙事文本。

## 数据类型

### `ActionPack`
```python
{
    "character_id": str,
    "round": int,
    "turn": int,
    "interaction_type": "speak" | "action" | "composite",
    "spoken_content": str | None,
    "action_content": str | None,
    "inner_reasoning": str,
    "targets": list[str],
}
```

### `CharacterDossier`
```python
{
    "character_id": str,
    "core_identity": str,       # 第一人称
    "private_understanding": str, # 第一人称
    "goals": list[CharacterGoal],
    "known_info": list[TaggedInfo],
    "secrets": list[SecretEntry],
}
```

### `ObjectiveFacts`
```python
{
    "时空状态": str,
    "物理状态": str,
    "交互基础": str,
    "起始事件": str,
}
```

## 配置

通过 `.env` 文件配置：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| LLM_MODEL | LLM 模型名称 | deepseek-reasoner |
| LLM_API_KEY | API 密钥 | - |
| LLM_BASE_URL | API 基础URL | https://api.deepseek.com |
| SECRET_PRESSURE_THRESHOLD | 秘密压力阈值 | 80 |
| MAX_ROUNDS | 最大推演轮次 | 20 |
| LOG_LEVEL | 日志级别 | INFO |
| DB_URL | PostgreSQL 连接串 | - |
| ENV | 运行环境 | development |
| TOOL_PLUGINS | 插件工具模块（逗号分隔） | - |

## 插件化工具注册

通过 `TOOL_PLUGINS` 指定插件模块路径，模块导入时注册工具函数：

```python
from src.tools.registry import register_tool

def my_tool(x: str) -> str:
    return x.upper()

register_tool("my_tool", my_tool)
```
