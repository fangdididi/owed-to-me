# owed-to-me（我该拿多少）

[English](README.md) | **中文**

> 在开口要一分钱之前，先弄清楚：单位欠你多少、你有几成把握、最晚哪天必须动手。

`owed-to-me` 是一个站在劳动者一侧的 Agent Skill（适用于 Claude Code、Codex、Cursor 以及任何会读 `SKILL.md` 的智能体）。它把"那么多周末都白干了"变成一张索赔清单：每一笔钱都有公式、有证据、有老实的证据等级、有截止日、有路线，并告诉你和解时不该低于的底线。

它是准备工具，不是法律意见。

## 它解决什么问题

- 要少了：不知道还有哪些钱可以要（未休年假、代通知金、未签合同的双倍工资）。
- 要多了：报出证明不了的数字，连本来能证明的那几项也跟着失去可信度。
- 要晚了：时效过了，或者工作账号一关、证据就没了。
- 签早了：没算账就签了"自愿离职 / 无其他争议"。

## 功能

- **案情卡**：日期、工资、谁以什么理由结束劳动关系、当事人真正想要什么，集中在一处。
- **先抢救证据清单**：HARD / FIRM / THIN 三级，`at_risk` 风险标记，以及合法保全的做法。
- **钱项**：WAGE_GAP、OVERTIME、LEAVE、NO_CONTRACT、SEVERANCE、NOTICE_MONTH、UNLAWFUL_2N、EXPENSE、OTHER，每项按**最弱**的关键证据定级。
- **计算器**（`scripts/owed.py`）：按考勤记录算加班费（支持跨零点、调休、按证据等级拆分）、按比例折算年假、N / N+1 / 2N 经济补偿（含高收入封顶）、时效倒计时。
- **规则包**：`rules/cn.json`（中国大陆，每个数字都注明法律出处）和 `rules/blank.json`（其他地区模板）；数值为空时脚本停下，绝不猜。
- **路线表**：ASK 书面索要、COMPLAIN 投诉、MEDIATE 调解、ARBITRATE 仲裁、SETTLE 和解，并标出花钱 / 花时间 / 耗精力。
- **带检查的索赔清单**：13 项检查，READY / FIX 结论，SOLID / ARGUABLE / LONGSHOT 三档合计和和解底线。
- **冷静的书面请求**：一封日后仲裁员看了也挑不出毛病的邮件或信的结构。
- 完整中英文版本；仅用 Python 标准库；15 个测试。

## 安装

```bash
git clone https://github.com/fangdididi/owed-to-me.git
```

| 智能体 | 放在哪里 |
|---|---|
| Claude Code | `~/.claude/skills/owed-to-me/`（或项目内 `.claude/skills/`） |
| Codex | `~/.codex/skills/owed-to-me/`，或在 `AGENTS.md` 里引用 `SKILL.md` |
| Cursor | `.cursor/skills/owed-to-me/`，或把 `SKILL.md` 加为项目规则 |
| 其他智能体 | 让它读 `SKILL.zh-CN.md`（中文）或 `SKILL.md`（英文） |

然后直接问，例如：*"我干了 4 年 7 个月被裁了，月均 12,000，周末加班有工作群消息为证，我能拿多少？"*

## 直接使用计算器

```bash
python3 scripts/owed.py hours examples/hours.csv --rules rules/cn.json --monthly 12000
python3 scripts/owed.py leave --rules rules/cn.json --monthly 12000 --career-years 6 --taken 1 --days-employed 304
python3 scripts/owed.py severance --rules rules/cn.json --start 2022-03-14 --end 2026-10-31 --monthly-avg 12000 --route N
python3 scripts/owed.py clock --rules rules/cn.json --event 2026-10-31
python3 scripts/owed.py sheet examples/case.json --rules rules/cn.json
python3 -m unittest discover -s tests
```

## 输出示例

```
| id | type | amount | proof | tier | route | last day |
| M1 | OVERTIME | CNY 1534.48 | FIRM | ARGUABLE | ARBITRATE | 2027-10-31 (OPEN) |
| M2 | OVERTIME | CNY 827.59 | THIN | LONGSHOT | ARBITRATE | 2027-10-31 (OPEN) |
| M3 | LEAVE | CNY 3310.34 | HARD | SOLID | ASK | 2027-10-31 (OPEN) |
| M4 | SEVERANCE | CNY 60000.00 | HARD | SOLID | ASK | 2027-10-31 (OPEN) |
| M5 | NOTICE_MONTH | CNY 12000.00 | HARD | SOLID | ASK | 2027-10-31 (OPEN) |

settlement floor (SOLID only): CNY 75310.34
L13 evidence E4 may vanish (work chat account removal) - secure a copy first
```

（单位和数字均为虚构。）

## 文件结构

```
owed-to-me/
├── SKILL.md             # 技能说明（英文）
├── SKILL.zh-CN.md       # 技能说明（中文）
├── README.md
├── README.zh-CN.md
├── LICENSE
├── rules/
│   ├── cn.json          # 中国大陆规则包，附法律出处
│   └── blank.json       # 其他地区模板
├── scripts/
│   └── owed.py          # hours / leave / severance / clock / sheet
├── examples/
│   ├── hours.csv        # 示例考勤记录
│   └── case.json        # 示例案情：案情卡、证据、钱项
└── tests/
    └── test_owed.py     # 15 个测试
```

## 重要提示

规则会变，且各地不同。使用前请对照最新官方原文核对规则包里的每个数值；正在进行的案子，请找法律援助、劳动部门或律师。

## 许可证

MIT © fangdididi
