# 通用企业基本面研究 Agent Skills

企业基本面研究 Skills，分为“形成投资判断”和“独立核查判断”两种职责。

仓库采用通用的 `SKILL.md + YAML frontmatter + references + scripts` 目录结构，不包含特定厂商的 UI 元数据、专属调用语法、工具名称或安装路径。任何能够加载 Markdown Skill、读取相对路径文件的 Agent 运行时都可以集成；联网检索和 Python 脚本执行能力按任务需要提供。

## 包含的 Skills

### `company-fundamentals-analysis`

基于最新公开披露完成完整的企业基本面与估值分析，覆盖：

- 主营业务、行业格局、上下游、客户与盈利模式；
- 品牌、专利/技术、产品、转换成本、客户依赖、主营集中度、市占率、网络效应、牌照/资源九维护城河；
- 五年现金流、ROE、ROIC、盈利质量与资产负债表；
- 商业模式、企业文化、管理层、治理和资本配置；
- 分红回购、主要股东及机构持仓变化；
- 行业空间、DCF/相对估值/PEG、机构观点、安全边际和验证点。

内置 `scripts/dcf_valuation.py`，用于复算多情景 FCFF DCF，避免手工算术错误。

### `company-fundamentals-audit`

独立核查既有基本面报告或投资论点：

- 将报告拆为可验证的主张账本；
- 回到原始披露，核对时点、单位、会计口径与来源；
- 独立复算财务指标和估值；
- 先做长期财务与护城河正向验证，再执行七维证伪；
- 完成红队演练、蓝队回应和五年预验尸；
- 分别给出企业护城河评级、报告可信度和受限事项。

内置 `scripts/verify_metrics.py`，支持 ROE、ROIC、FCF、现金转化率、分红率、股息率、净债务、CAGR 和 DCF 每股价值的批量复算与容差比较。

## 通用集成方式

1. 将所需 Skill 的完整目录复制到目标 Agent 平台的 Skill、Prompt 或 Capability 目录。
2. 按该平台的机制注册目录中的 `SKILL.md`；保持 `references/` 和 `scripts/` 的相对路径不变。
3. 让运行时在命中 frontmatter 的 `description` 时加载 `SKILL.md`，并按入口指引按需读取引用文件。
4. 若运行时允许执行本地脚本，使用 Python 3.10 或更高版本；若不允许，Agent 可按引用文件中的公式独立复算，并明确说明未执行脚本。

不同平台的安装目录和显式调用标记并不统一，因此本仓库不预设 `~/.某产品/skills`、斜杠命令或 `$skill-name` 语法。

## 通用调用示例

```text
请使用 company-fundamentals-analysis，基于最新公开数据分析法拉电子（600563.SH），给出三情景估值、安全边际和未来 12 个月验证点。
```

```text
请使用 company-fundamentals-audit 核查这份法拉电子基本面报告。模式为 full；独立复算所有关键指标，并执行 moat stress test。
```

```text
请使用 company-fundamentals-audit 对目标公司执行 red-team，只输出最强反证、七维风险和五年预验尸。
```

实际调用时也可以不写 Skill 名称，由支持自动路由的 Agent 根据 `description` 选择。

## 运行能力

完整执行通常需要以下通用能力，但不绑定具体工具或供应商：

- 读取本地 Markdown、JSON 和用户提供的报告；
- 检索并打开交易所、监管机构、公司公告和行业来源；
- 记录可点击引用以及文档页码、表名或章节；
- 执行 Python 脚本，或以等价方式完成可复算计算；
- 获取基准日对应的证券价格与公开股东数据。

若某项能力不可用，Skill 会要求完成可完成部分、标注证据缺口，并避免把旧数据或推测描述成当前事实。

## 设计原则

- 原始披露优先，关键事实保留日期、期间、单位、口径和可定位来源；
- 事实、公司口径、第三方估计、计算结果和分析判断分层表达；
- 企业质量与证券价格分开评价；
- 护城河既要证明形成机制，也要主动寻找反例；
- 无法核验的内容标为证据不足，不用推测填空；
- 价格区间和行动条件是情景分析，不构成个性化投资建议。

## 目录结构

```text
company-fundamentals-skills/
├── company-fundamentals-analysis/
│   ├── SKILL.md
│   ├── references/
│   └── scripts/dcf_valuation.py
└── company-fundamentals-audit/
    ├── SKILL.md
    ├── references/
    └── scripts/verify_metrics.py
```

