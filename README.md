# Ludos — 角色驱动叙事推演智能体

基于 LangGraph 的多智能体叙事推演系统，用于小说创作辅助。

## 核心特性

- **角色自主驱动**：角色基于自身档案独立决策，而非作者预设剧情
- **认知红绿灯**：严格的信息隔离机制，确保角色只能使用自身已知信息
- **秘密压力系统**：秘密在自然对话中有机暴露，而非机械触发
- **非数值化冲突**：文学化定性描述替代数值化判定
- **三阶段架构**：初始化 → 自主推演循环 → 文学润色

## 快速开始

### 环境准备

```bash
# 创建 conda 环境
conda create -n ludos python=3.12 -y
conda activate ludos

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key
```

### 健康检查

```bash
# 基础健康检查（含 LLM 连通性）
python -m src.main --health

# 启动脚本健康检查
python scripts/run.py --health
```

### 插件化工具注册

通过环境变量 `TOOL_PLUGINS` 以逗号分隔指定模块路径，模块导入时需注册工具。

示例：
```bash
export TOOL_PLUGINS=plugins.tools.extra,plugins.tools.more
```

插件模块中注册工具：
```python
from src.tools.registry import register_tool

def my_tool(x: str) -> str:
    return x.upper()

register_tool("my_tool", my_tool)
```

### 运行

```bash
# 从文件输入
python -m src.main input.txt --output result.md

# 从标准输入
echo "你的叙事纲要..." | python -m src.main

# 使用启动脚本（含环境检查）
python scripts/run.py input.txt
```

### 运行中日志与角色记忆

运行时会生成两类日志：

- 公共广播日志：`logs/session_<id>.public.log`
- 原始交互日志：`logs/session_<id>.raw.log`

可实时查看公共广播日志：

```bash
tail -f logs/session_<id>.public.log
```

每个角色会维护自己的记忆文件（半结构化协议）：

```
data/characters/<session_id>/<角色ID>.mem.txt
```

### 测试

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=term-missing
```

## 架构概览

```
用户输入（叙事纲要）
        ↓
  [初始化] 解析为结构化JSON → 角色记忆 seed
        ↓
  [推演循环] 场景播报 → 角色逐个行动 → 压力更新 → 回合评估（角色自评）
        ↓  (循环直到结束条件满足)
  [润色] 原始日志文件 → 文学叙事文本
        ↓
  输出：原始交互日志 + 润色叙事文本
```

### 公共/私有记忆数据流示意

```
           ┌──────────────────────────────┐
           │          主持人 (Moderator)  │
           │  - 场景播报                  │
           │  - 公共交互日志               │
           │  - 公共记忆维护               │
           └───────────────┬──────────────┘
                           │ 公共广播
                           ▼
┌───────────────────────────────────────────────────────────┐
│                    公共日志 (public.log)                  │
└───────────────┬───────────────────────────────────────────┘
                │ 仅新增部分
                ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│ 角色A 私有记忆 (mem.txt)       │    │ 角色B 私有记忆 (mem.txt)       │
│ - 稳定记忆                    │    │ - 稳定记忆                    │
│ - 工作记忆                    │    │ - 工作记忆                    │
│ - 目标/秘密/压力              │    │ - 目标/秘密/压力              │
└───────────────┬──────────────┘    └───────────────┬──────────────┘
                │                                   │
                └──────────────┬────────────────────┘
                               ▼
                       角色对外交互输出
                               │
                               ▼
                      主持人转发并同步公共信息
```

## 项目结构

```
src/
├── config/     # 配置管理与提示词模板
├── models/     # 领域类型与Pydantic模型
├── agents/     # 智能体（主持人/角色/润色）
├── graphs/     # LangGraph图定义
├── tools/      # 工具集（信息过滤/压力追踪等）
├── memory/     # 持久化模块
└── utils/      # 工具函数
```

## 文档

- [架构设计](doc/v0.1.0/design.md)
- [API文档](doc/v0.1.0/api.md)
- [变更日志](doc/v0.1.0/changelog.md)

## 许可证

MIT

## 改造记录

已完成：
- 角色记忆半结构化协议（无 JSON 解析依赖）
- 主持人仅维护公共广播与公开交互日志
- 原始交互日志运行时落盘并用于润色
- 角色自管目标状态与秘密压力值（从全局 state 中剥离）
- 主持人评估仅基于公共日志汇总，不读取角色私有记忆

下一步计划：
1. 角色对外交互新增“小动作”字段，用于记录角色为达成目标的细微动作。
2. 主持人维护小动作记忆，并在后续根据情境判定是否被其他角色发现。
3. 该机制复杂度较高，暂以计划形式记录，后续逐步实现。
