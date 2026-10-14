# 企业基本面研究 Skills

一组面向上市公司基本面研究的 Codex Skills，分离“形成投资判断”和“独立核查判断”两种职责。

## 包含的 Skills

### `company-fundamentals-analysis`

基于最新公开披露完成完整的企业基本面与估值分析，覆盖：

- 主营业务、行业格局、上下游、客户与盈利模式；
- 品牌、专利/技术、产品、转换成本、客户依赖、主营集中度、市占率、网络效应、牌照/资源九维护城河；
- 五年现金流、ROE、ROIC、盈利质量与资产负债表；
- 商业模式、企业文化、管理层、治理和资本配置；
- 分红回购、十大流通股东及机构持仓变化；
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

## 安装

将两个 Skill 目录复制到 Codex Skills 目录：

```bash
cp -R company-fundamentals-analysis ~/.codex/skills/
cp -R company-fundamentals-audit ~/.codex/skills/
```

重启或刷新 Codex 后即可使用。

## 调用示例

```text
使用 $company-fundamentals-analysis，基于最新公开数据分析法拉电子（600563.SH），给出三情景估值、安全边际和未来 12 个月验证点。
```

```text
使用 $company-fundamentals-audit，核查这份法拉电子基本面报告。模式=full；独立复算所有关键指标，并执行 moat stress test。
```

```text
使用 $company-fundamentals-audit 对法拉电子执行 red-team，只输出最强反证、七维风险和五年预验尸。
```

## 设计原则

- 原始披露优先，关键事实保留日期、期间、单位、口径和可定位来源；
- 事实、公司口径、第三方估计、计算结果和分析判断分层表达；
- 企业质量与股票价格分开评价；
- 护城河既要证明形成机制，也要主动寻找反例；
- 无法核验的内容标为证据不足，不用推测填空；
- 价格区间和行动条件是情景分析，不构成个性化投资建议。

## 目录结构

```text
company-fundamentals-skills/
├── company-fundamentals-analysis/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── references/
│   └── scripts/dcf_valuation.py
└── company-fundamentals-audit/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── references/
    └── scripts/verify_metrics.py
```

