# Agent Wiki

[English](README.md) · [安装 Skill](skills/agent-wiki-setup/SKILL.md) · [完整工作流](docs/workflow.md)

给多个 Agent 共用的长期知识库，默认创建一个独立的 Obsidian Vault，名称为 `Agent Wiki`，以普通 Markdown 文件保存。
它记录值得保留的决策、原因、项目约束与可复用经验，让 Agent 在需要时找回上下文，减少重复推演。
无需每次对话加载整个知识库。

这个公开仓库只包含工作流、安装 Skill 和工具，不包含任何人的私人笔记或对话。
理念参考 [Andrej Karpathy 的 LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)，实现独立维护。

## 让 Agent 帮你安装

把下面这段发给你的 Agent：

```text
请使用 https://github.com/ryangandev/agent-wiki/tree/main/skills/agent-wiki-setup
中的 Skill，在我的电脑上配置私人 Agent Wiki。
请阅读 SKILL.md，取得完整的 Skill 目录，包括 scripts 和 assets。
请默认推荐新建独立的 Agent Wiki Vault，并询问创建位置。
如果我选择现有 Vault，或者说明当前文件夹就是 Vault，请直接使用它的根目录。
要接入的 Agent 或时区不明确时，请询问。
安装后运行隔离验证；如果当前 Agent 支持定时任务，请通过其正式接口配置维护。
请分别说明文件安装、各 Agent 的实际访问能力以及定时任务是否验证成功。
```

Codex 用户也可以让内置 Skill Installer 安装这个 Skill URL，然后调用 `$agent-wiki-setup`。
Claude Code 或其他兼容 Agent 可以将完整 Skill 目录安装到自己的 Skill 目录，或克隆仓库后直接指定 `SKILL.md`。
安装 Skill 后仍需执行一次配置，选择你的私人知识库位置。

## 先选择在哪里创建

| 方式 | 结果 |
| --- | --- |
| **新建独立 Vault，默认推荐** | 在你选择的位置创建 `Agent Wiki`，这个文件夹本身就是 Vault |
| **使用现有 Vault 或当前文件夹** | 确认该文件夹就是 Vault 后，直接在根目录配置，保留其他笔记和设置 |
| **放进现有 Vault 的子文件夹** | 只有明确选择时，才创建 `<现有 Vault>/Agent Wiki` |

安装 Skill 会先确认尚未明确的位置和方式，不会因为当前工作目录存在就擅自把它当作 Vault。
独立 Vault 便于单独管理 Agent 的权限、同步和备份，也让 Agent 知识与个人笔记分开。
如果你希望与现有笔记在同一个 Vault 内互相链接，可以选择后两种方式。

默认生成：

```text
Agent Wiki/        ← 这个文件夹本身就是 Vault
├── .obsidian/
├── Home.md
├── wiki/
├── sources/
└── _system/
```

生成后，在 Obsidian 中选择“Open folder as vault”，打开这个文件夹。
安装器负责准备文件，不会自动把 Vault 注册或打开到 Obsidian 中。
如果现有 Vault 中已有同名工作流目录或不同内容的 `Home.md`，安装器会停止并报告冲突。

## 从开始到结束的循环

1. **按需检索：** 当前任务缺少历史决策或约束时，先检索精简索引，再读取相关段落；需要追溯时才打开来源。
2. **选择性记录：** 出现经过授权、有依据、值得长期保留的新知识时，写入最小必要来源；日常进度和代码里能查到的事实不重复存储。
3. **每日整理：** 建议每天当地时间 00:00，由 Agent 处理尚未整理的来源，更新项目、决策、主题或方法页面。
4. **每周复盘：** 建议周日检查发生变化的相关主题，合并重复、处理冲突、压缩冗余，同时保留决策演变和依据。
5. **没有新增就不动：** 不创建空笔记，不刷新时间戳，不发送例行报告。

默认工作内容是各 Agent 已经记录到库里的来源，不会自动扫描所有聊天。
没有写入来源的会话，不会在夜间整理时自动被发现。

## 文件放在哪里

| 层 | 内容 | 什么时候读取 |
| --- | --- | --- |
| 精简索引 | 标题、摘要、关键词、路径 | 查找相关知识时 |
| `wiki/` | 可直接复用的结论、决策与项目背景 | 命中相关内容后 |
| `sources/` | 支撑结论的最小必要依据 | 核对、追溯或解决冲突时 |
| `_system/` | 工作规则、工具、处理账本与修订历史 | 对应操作需要时 |

Obsidian 负责存储、链接和编辑，Agent 负责理解和整理，Python 工具负责索引、校验、精确去重和安全写入。
安装器可以接入 Codex、Claude Code；其他 Agent 可以使用生成的入口说明接入同一个库。

## 安装条件与边界

需要 Python 3.10 或以上，以及你选定的新 Vault 创建位置或现有 Vault。
工具本身没有第三方 Python 依赖，不需要 Obsidian 插件或 API Key。
命令行安装方法见 [英文 README](README.md#set-up-from-the-command-line)。

安装器会先预览修改，再按授权执行，保留已有全局指令；遇到已有配置冲突会停止并说明原因。
实际知识库应放在这个公开仓库之外。
安装后的隔离测试不会向你的真实知识库写入测试内容。

定时任务需要在你的 Agent 环境中单独启用并验证，安装 Skill 本身不会创建后台服务。
没有可用的调度器时，可以手动触发同一套维护流程。
多个同步设备应约定同一时间只在一台设备写入，因为本地锁无法协调不同电脑。
重要资料仍需私人备份。

MIT 开源，欢迎复用与改进。
