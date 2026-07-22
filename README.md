# Multi-Agent Communication Protocol Benchmark

用于比较不同多智能体通信协议的可复现实验框架。项目把 **通信协议** 作为主要实验变量，在相同 benchmark、Agent 模型、工具约束与预算下运行任务，再用独立 Judge 评分，并对执行轨迹进行失败分析。

当前完整 benchmark 为 `benchmark/benchmark-full.json`，由 B、C、D、E 四个分片组成，共 24 个任务、6 个类别。

## 核心设计

一次完整实验分为三步：

```text
Benchmark
  -> 按字段边界生成 Agent 输入
  -> 使用指定模型和通信协议执行
  -> 保存完整 raw log
  -> 独立 Quality Judge 评分
  -> Failure Analyzer 分析协作轨迹
  -> 确定性工具、证据和格式审计
  -> 聚合结果并绘图
```

关键原则：

- **控制实验变量**：同一任务可使用不同 Agent 模型和 protocol 重复运行。
- **Agent/Judge 隔离**：Agent 默认看不到 ground truth、rubric 等评分字段。
- **盲评最终答案**：Quality Judge 只读取完整评分标准与 `final_output`，不读取 protocol 名称和中间消息。
- **失败分析独立**：Failure Analyzer 读取 raw log，但其标签不会参与质量分计算。
- **确定性审计**：工具白名单、Required/Prohibited 约束、证据可追溯性和输出格式由代码检查，不能由 Judge 覆盖。
- **可复现记录**：每个 run 保存模型、protocol、任务快照、预算、token、工具调用和中间消息。

## 环境与依赖

实验运行和评分主体使用 Python 标准库，不需要安装第三方包。

按实际用途安装可选依赖：

```bash
# 生成结果图
python3 -m pip install "matplotlib>=3.7"

# 读取 benchmark/documents 中的 PDF
python3 -m pip install pypdf

# 两项功能都需要
python3 -m pip install "matplotlib>=3.7" pypdf
```

`matplotlib` 只由 `scripts/plot.py` 使用；`pypdf` 只在 Agent 读取 PDF 时加载。

## 快速开始

以下命令均在项目根目录执行。

### 1. 配置 API Key

交互式保存所需 provider 的密钥：

```bash
python3 scripts/configure_models.py
```

密钥保存在已被 Git 忽略的 `.secrets/model_keys.json`，也可以使用环境变量：

```bash
export DEEPSEEK_API_KEY='...'
export OPENAI_API_KEY='...'
```

环境变量优先于本地 secrets 文件。不要把密钥写入模型配置或命令行。

查看当前模型 profile：

```bash
python3 scripts/experiment.py --list-models
```

Profile 是命令行使用的配置名，例如 `deepseek_v4_flash`、`gpt_5_nano`、`deepseek_v4_pro`、`gpt_5_mini`；它们与 API model ID 不一定相同。

### 2. 运行实验并生成日志

先用测试 benchmark 检查环境：

```bash
python3 scripts/experiment.py \
  --benchmark benchmark/benchmark-test.json \
  --agent-profile deepseek_v4_flash \
  --protocols single_agent \
  --out-dir logs/test
```

运行完整 benchmark、全部 protocol：

```bash
python3 scripts/experiment.py \
  --benchmark benchmark/benchmark-full.json \
  --agent-profile deepseek_v4_flash \
  --protocols all \
  --runs 1 \
  --out-dir logs/2026-07-22-full-deepseekflash
```

另一个 Agent 模型应写入独立目录：

```bash
python3 scripts/experiment.py \
  --benchmark benchmark/benchmark-full.json \
  --agent-profile gpt_5_nano \
  --protocols all \
  --runs 1 \
  --out-dir logs/2026-07-22-full-gpt5nano
```

已有完全相同的 run 默认跳过；`--overwrite` 只覆盖 run ID 和配置都匹配的记录。改变 benchmark、字段可见性或协议预算时，建议使用新的日志目录。

### 3. 评分并聚合

日志只需生成一次，可以交给不同 Judge 重复评分。每套评分建议使用独立结果目录：

```bash
python3 scripts/judge.py \
  --benchmark benchmark/benchmark-full.json \
  --logs-dir logs/2026-07-22-full-deepseekflash \
  --judge-profile deepseek_v4_pro \
  --results-dir results/2026-07-22-full-deepseekflash-deepseekpro
```

使用另一 Judge：

```bash
python3 scripts/judge.py \
  --benchmark benchmark/benchmark-full.json \
  --logs-dir logs/2026-07-22-full-deepseekflash \
  --judge-profile gpt_5_mini \
  --results-dir results/2026-07-22-full-deepseekflash-gpt5mini
```

`judge.py` 会同时生成逐条分数、错误记录、聚合结果和 Markdown 摘要。重复 Judge 实验时，请使用不同的 `--results-dir`，避免与已有 score ID 混合或冲突。

### 4. 生成图表

```bash
python3 scripts/plot.py \
  --results-dir results/2026-07-22-full-deepseekflash-deepseekpro
```

图片写入该结果目录下的 `figures/`。

## 通信协议

| Protocol ID | 设计逻辑 |
|---|---|
| `single_agent` | 单个 Agent 独立完成任务，作为基线 |
| `unstructured_group_chat` | 多角色共享对话，自由交流后汇总 |
| `sequential_handoff` | Planner → Researcher → Analyst → Writer 顺序交接 |
| `shared_blackboard` | 多角色分轮读写共享工作区 |
| `manager_worker` | Manager 分解和分配任务，Worker 执行后统一汇总 |
| `debate` | 独立方案、交叉批评、最终综合 |
| `voting` | 生成候选方案并匿名投票决定结果 |
| `dynamic_task_allocation` | 按角色能力动态分配子任务并复核缺口 |

查看代码当前采用的协议及默认轮数、交互预算：

```bash
python3 scripts/experiment.py --list-protocols
```

## 命令行参数

### `scripts/experiment.py`

运行 Agent 实验并写入 raw logs。

| 参数 | 作用 |
|---|---|
| `--benchmark PATH` | benchmark 文件；默认是 `benchmark/benchmark-test.json` |
| `--model-config PATH` | 模型 profile 配置文件 |
| `--experiment-config PATH` | protocol、工具和预算配置文件 |
| `--out-dir DIR` | 日志目录；默认 `logs/current` |
| `--agent-profile NAME` | 单个 Agent profile |
| `--agent-profiles A,B` | 逗号分隔的多个 profile；`all` 表示全部 |
| `--protocols A,B` | 逗号分隔的 protocol；`all` 表示全部 |
| `--tasks ID1,ID2` | 只运行指定 task ID；留空表示全部 |
| `--runs N` | 每个 condition 的重复次数；`0` 使用实验配置 |
| `--run-number N` | replicate 的起始编号 |
| `--model MODEL_ID` | 临时覆盖所选 Agent profile 的 API model ID |
| `--max-rounds N` | 临时覆盖所选协议的最大轮数 |
| `--max-interactions N` | 临时覆盖最大模型交互次数 |
| `--max-total-tokens N` | 临时覆盖单个 run 的总 token 预算；`0` 使用配置 |
| `--strict-tool-requirements` | 工具要求不满足时采用严格处理 |
| `--overwrite` | 覆盖配置完全匹配的已有 run |
| `--agent-visible-fields A,B` | 自定义 Agent 可见的 benchmark 字段 |
| `--allow-protected-agent-fields` | 允许把受保护评分字段提供给 Agent |
| `--print-agent-view` | 打印 Agent 实际输入后退出 |
| `--list-protocols` | 列出 protocol 后退出 |
| `--list-models` | 列出模型 profile 后退出 |
| `--list-task-fields` | 列出 benchmark 字段后退出 |

示例：只运行两道题、两个协议和两个 Agent profile：

```bash
python3 scripts/experiment.py \
  --benchmark benchmark/benchmark-full.json \
  --tasks LR-01,TA-01 \
  --protocols single_agent,manager_worker \
  --agent-profiles deepseek_v4_flash,gpt_5_nano \
  --runs 2 \
  --out-dir logs/subset
```

### `scripts/judge.py`

读取日志，执行质量评分、失败分析和聚合。

| 参数 | 作用 |
|---|---|
| `--benchmark PATH` | 必须与生成日志时使用的 benchmark 对应 |
| `--model-config PATH` | 模型 profile 配置文件 |
| `--logs-dir DIR` | raw log 所在目录；只读取第一层 JSON 文件 |
| `--results-dir DIR` | 分数、错误、聚合和摘要输出目录 |
| `--judge-profile NAME` | 单个 Judge profile |
| `--judge-profiles A,B` | 逗号分隔的多个 Judge profile；`all` 表示全部 |
| `--tasks ID1,ID2` | 只评分指定任务 |
| `--agent-models A,B` | 只评分指定 API Agent model ID，例如 `gpt-5-nano` |
| `--model MODEL_ID` | 临时覆盖所选 Judge profile 的 API model ID |
| `--group-by condition\|protocol` | 按完整条件或只按 protocol 聚合 |
| `--overwrite` | 重新评分匹配的 Judge/run 条件 |
| `--fail-fast` | 第一条评分错误出现时立即停止 |
| `--list-models` | 列出模型 profile 后退出 |

### `scripts/plot.py`

| 参数 | 作用 |
|---|---|
| `--results-dir DIR` | 包含 `scores.csv` 的结果目录 |
| `--dpi N` | PNG 输出分辨率 |

### `scripts/configure_models.py`

| 参数 | 作用 |
|---|---|
| `--config PATH` | 模型 profile 配置文件 |
| `--secrets PATH` | 本地密钥文件；默认 `.secrets/model_keys.json` |
| `--provider NAME` | 只配置指定 provider；可重复或使用逗号分隔 |
| `--list-profiles` | 显示非敏感 profile 信息后退出 |

任意脚本均可使用 `--help` 查看代码当前支持的完整参数。

## Benchmark、工具与评分边界

Agent 默认可见字段：

```text
task_id, category, difficulty, tool_requirement,
available_tools, tool_expectations, prompt, required_output_format
```

`ground_truth`、`scoring_rubric`、`evaluation_criteria`、`required_evidence` 等字段只提供给 Judge。可用以下命令检查实际边界：

```bash
python3 scripts/experiment.py \
  --benchmark benchmark/benchmark-full.json \
  --tasks LR-01 \
  --print-agent-view
```

任务的 `tool_requirement` 分为：

- `Required`：必须成功使用任务声明的证据工具，并满足证据策略。
- `Optional`：允许 Agent 自主决定是否调用白名单工具。
- `Prohibited`：不向模型暴露工具；出现工具调用会使执行无效。

任务级 `available_tools` 是实际白名单，运行器记录调用参数、结果、角色、轮次和状态。网页工具限制为公网 HTTP(S) 地址，本地文档工具限制在配置允许的目录内。

质量分由 Judge 的四项评估组成：

```text
0.35 × accuracy
+ 0.30 × completeness
+ 0.20 × helpfulness
+ 0.15 × (1 - hallucination_rate)
```

之后再应用确定性的工具、证据和格式上限。Failure Analyzer 使用 `src/failure_taxonomy.py` 中的协议相关多标签分类，但 failure 不直接提高或降低质量分。

## 配置与输出

主要配置：

- `configs/model_config.json`：provider、model ID、token 上限、超时、重试和价格。
- `configs/experiment_config.json`：协议预算、Agent 可见字段、工具策略和每个 condition 的运行次数。
- `benchmark/benchmark-full.json`：完整任务入口。

主要代码：

- `scripts/experiment.py`：实验入口。
- `scripts/judge.py`：评分与聚合入口。
- `scripts/plot.py`：可视化入口。
- `src/protocols.py`：协议实现。
- `src/llm_client.py`：统一模型调用接口。
- `src/tools.py`：受控工具执行。
- `src/scorer.py`：质量评分与失败分析。
- `src/evidence.py`、`src/response_audit.py`：确定性审计。

日志目录包含每个 run 的 JSON 和实验 manifest。评分目录通常包含：

```text
scores.jsonl
scores.csv
scoring_errors.jsonl
aggregate_results.json
aggregate_results.csv
summary.md
figures/*.png
```

`scores.jsonl` 保留最完整的 Judge、failure、证据审计和成本信息；`scores.csv` 用于统计与绘图。

## 运行检查

修改代码后可执行语法检查：

```bash
python3 -m compileall -q src scripts
```

项目不会自动删除历史 logs 或 results。正式实验应为不同条件使用独立目录，并保留 benchmark、配置文件、manifest、raw logs 和评分结果。
