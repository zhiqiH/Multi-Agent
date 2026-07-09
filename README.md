# 多智能体通信协议 Benchmark 程序运行指南

本项目实现了一个轻量版多智能体通信协议实验平台。原标准要求 30 个 benchmark task；为了减少 token 使用，本版本按你的要求只冻结 3 个 task，但保留统一任务字段、统一模型配置、统一日志 schema、统一评分公式和 baseline + 至少 3 种通信协议的实验结构。

## 1. 项目结构

```text
multi_agent_protocol_benchmark/
  benchmark/
    final/                    # 3 个冻结 task 的 md/yaml 文件
    benchmark_v1.0.json       # 程序实际读取的冻结 benchmark
    scoring_rubric.md         # 共享评分公式
    config.yaml               # JSON-compatible YAML 配置
    changelog.md
  configs/
    model_config.json         # DeepSeek 模型、temperature、token、价格估算配置
    experiment_config.json
  scripts/
    run_experiment.py         # 运行 baseline 和通信协议
    score_outputs.py          # 使用同一 rubric 对输出评分
    aggregate_results.py      # 汇总协议平均表现
  src/                        # 核心程序
  logs/raw/                   # 运行后生成 run log
  results/                    # 评分和汇总结果
```

## 2. 环境要求

- Python 3.10 或更高版本。
- 不需要安装第三方 Python 包。
- 真实运行 DeepSeek 时需要设置环境变量 `DEEPSEEK_API_KEY`。

DeepSeek 官方 API 当前采用 OpenAI-compatible 格式，默认 base URL 是 `https://api.deepseek.com`。本项目默认模型使用 `deepseek-v4-flash`，配置文件里也支持改成 `deepseek-v4-pro`。

## 3. 先跑本地 dry-run

dry-run 不会调用 API，也不会消耗 token，适合检查程序是否能完整跑通。

```bash
cd /Users/zhiqi/SummerBootcamp/test

python3 scripts/run_experiment.py --dry-run --overwrite
python3 scripts/score_outputs.py --dry-run --overwrite
python3 scripts/aggregate_results.py
```

运行后重点查看：

```text
logs/raw/*.json
results/scores.csv
results/aggregate_results.csv
results/experiment_summary.md
```

## 4. 设置 DeepSeek API

不要把 API key 写进代码或提交到仓库。推荐只在当前终端设置：

```bash
export DEEPSEEK_API_KEY='sk-XXXXXX'
export DEEPSEEK_BASE_URL='https://api.deepseek.com'
export DEEPSEEK_MODEL='deepseek-v4-flash'
```

如果你想用更强但更贵的模型：

```bash
export DEEPSEEK_MODEL='deepseek-v4-pro'
```

## 5. 真实运行轻量实验

默认运行 3 个 task × 4 个条件：

- `single_agent`
- `sequential_handoff`
- `shared_blackboard`
- `manager_worker`

命令：

```bash
python3 scripts/run_experiment.py --overwrite
python3 scripts/score_outputs.py --overwrite
python3 scripts/aggregate_results.py
```

这会生成原始日志、评分结果和协议平均表现汇总。

## 6. 运行更多协议

程序还实现了：

- `unstructured_group_chat`
- `debate`

查看全部协议：

```bash
python3 scripts/run_experiment.py --list-protocols
```

运行所有已实现协议：

```bash
python3 scripts/run_experiment.py --protocols all --overwrite
python3 scripts/score_outputs.py --overwrite
python3 scripts/aggregate_results.py
```

## 7. 只跑一个 task 或少量协议

如果想进一步省 token：

```bash
python3 scripts/run_experiment.py \
  --tasks LR-01 \
  --protocols single_agent,sequential_handoff \
  --overwrite
```

然后照常评分和汇总：

```bash
python3 scripts/score_outputs.py --overwrite
python3 scripts/aggregate_results.py
```

## 8. 结果文件说明

### `logs/raw/*.json`

每个 task-protocol 条件生成一个 JSON run log，包含：

- `run_id`
- `task_id`
- `category`
- `difficulty`
- `protocol`
- `model`
- `temperature`
- `tool_requirement`
- `start_time`
- `end_time`
- `runtime_seconds`
- `input_tokens`
- `output_tokens`
- `total_tokens`
- `estimated_cost`
- `message_count`
- `communication_density`
- `intermediate_messages`
- `final_output`
- `errors`

### `results/scores.csv`

每个 run 的评分记录，包含：

- `accuracy_raw`
- `accuracy_norm`
- `completeness_norm`
- `helpfulness_raw`
- `helpfulness_norm`
- `hallucination_rate`
- `overall_quality_score`
- `failure_type`
- `notes`

### `results/aggregate_results.csv`

按协议汇总平均质量、平均 token、平均消息数、平均成本等指标。

## 9. 评分公式

程序使用项目文档推荐公式：

```text
overall_quality_score =
  0.35 * accuracy_norm
  + 0.30 * completeness_norm
  + 0.20 * helpfulness_norm
  + 0.15 * (1 - hallucination_rate)
```

其中：

- `accuracy_raw` 和 `helpfulness_raw` 是 1 到 5 分，归一化为 `(raw - 1) / 4`。
- `completeness_norm` 是覆盖评价标准的比例。
- `hallucination_rate` 是无支持事实声明比例。

## 10. 常见问题

### 没有设置 API key 会怎样？

真实运行会报错。先用 `--dry-run` 检查程序，确认没问题后再设置 `DEEPSEEK_API_KEY`。

### 为什么默认不是 `deepseek-chat`？

DeepSeek 官方文档显示 `deepseek-chat` 和 `deepseek-reasoner` 将在 2026-07-24 15:59 UTC 弃用；本项目默认使用更新的 `deepseek-v4-flash`。

### 会不会使用外部工具搜索？

不会。本轻量 benchmark 的 3 个 task 都标记为 `Tool Requirement: Prohibited`，所有协议必须在同一无外部工具条件下运行。

### 如何避免重复覆盖结果？

默认如果日志已存在会跳过；加 `--overwrite` 才会覆盖。课程实验中建议固定一次 run，不要因为某个协议表现差而单独重跑。

