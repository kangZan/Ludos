# 世界观分层与角色可获得性方案（草案）

目标：在保持世界设定清晰的同时，避免把角色不应知道的信息泄露给角色，支持“乡下小子/穿越者”等知识缺失型角色。

## 1. 核心原则

- **世界观分层**：将世界设定按“可获得性”分段，而非一次性全量注入。
- **角色分级读取**：角色按自身 `knowledge_level` 读取对应层级的信息。
- **主持人可全量**：主持人可读取全量世界观，但对角色输出仍需过滤。
- **最小输入**：必读内容保持短小，避免 prompt 膨胀。

## 2. 世界档案结构建议

```
data/world/
├── 00_world_background.md        # 必读：世界基调/常识/规则（短）
├── 01_combat_rules.md             # 战斗设定（战斗场景读取）
├── 02_factions.md                 # 组织势力（按需）
├── 03_magic_or_tech.md            # 超凡/科技规则（按需）
├── 04_geography.md                # 地理/地域（按需）
├── 05_history_timeline.md         # 历史关键节点（按需）
└── 06_society_norms.md            # 社会秩序/法律/禁忌（按需）
```

## 3. 分层标记（建议格式）

在世界观文件中使用层级标记段：

```text
[COMMON]
全体角色都应知道的常识。

[REGIONAL:北境]
只对特定地域的人可见的知识。

[SPECIAL:天启教会]
只对特定组织/职业可见的知识。

[SECRET]
默认不对角色可见的知识。
```

## 4. 角色档案建议

### 4.1 社会背景（私有）

```
data/characters/<session_id>/<角色ID>.social.txt
```

建议字段：
- `knowledge_level`: `common` | `common+regional` | `special:<org>` | `outsider` 等
- `region`: 角色地域（用于匹配 REGIONAL）
- `affiliation`: 组织（用于匹配 SPECIAL）

### 4.2 战斗档案（私有）

```
data/characters/<session_id>/<角色ID>.combat.txt
```

包含角色可用战斗技能/限制，不包含世界级规则（由 `01_combat_rules.md` 提供）。

## 5. 读取策略（建议）

- 角色默认读取 `00_world_background.md` 的 `COMMON` 段。
- 若 `knowledge_level` 包含 `regional`，读取相应地域段。
- 若 `knowledge_level` 包含 `special:<org>`，读取该组织段。
- `SECRET` 永不直接注入角色。
- 主持人可读取全量世界档案，但对角色输出仍需过滤。

## 6. 风险与注意事项

- **信息泄露**：务必确保角色 prompt 仅包含其权限内的段落。
- **长度膨胀**：必读文件应保持短小（建议 200–400 字）。
- **缺省处理**：角色缺少 `social.txt` 时需有默认 `knowledge_level=common`。
- **一致性**：同一角色不应在不同阶段获得“跳跃式”知识，除非通过剧情获取。

## 7. 实施清单（最小落地）

1. 新建 `data/world/` 目录与模板文件。
2. 新建角色 `social.txt` 与 `combat.txt` 模板。
3. 在角色 prompt 组装处加入层级过滤逻辑。
4. 增加最小测试：不同 `knowledge_level` 是否正确过滤。
