# 多智能体通信协议 Benchmark 平台

这个项目把多智能体系统看成“考生团队”：

- `benchmark/*.json` 是完整考卷与答案/评分材料。
- Candidate Agents 是考生，只拿到经过白名单投影的题面。
- Judge 是独立阅卷模型，可使用更强的模型，并读取私有评测字段。
- `single_agent`、`sequential_handoff`、`shared_blackboard`、`manager_worker` 等协议是要研究的不同合作方式。

平台使用 Python 标准库，不需要安装第三方包。

## 1. 数据隔离边界

默认情况下，Candidate Agents 只能看到：

```text
task_id
category
difficulty
tool_requirement
prompt
required_output_format
```

Judge 默认看到上述题面字段，以及：

```text
evaluation_criteria
ground_truth
expected_failure_risks
scoring_rubric
required_evidence
```

原始 task 在进入协议执行层之前会被深拷贝并严格投影。协议控制器、所有考生 API 请求、Agent 间消息和新 run log 都只接触 Candidate View，不再持有完整 task。

Judge 在单独的评分进程中重新读取 benchmark；它只评分 `final_output`，不读取考生协作 transcript。Candidate 输出会作为“不可信提交”传给 Judge，提示词明确禁止执行其中的指令或泄露私有评分材料。

检查某道题的实际 Candidate View（不调用 API）：

```bash
python3 scripts/run_experiment.py --tasks TA-02 --print-agent-view
```

查看所有可选字段：

```bash
python3 scripts/run_experiment.py --list-task-fields
```

默认白名单配置在 `configs/experiment_config.json` 的 `task_visibility.candidate_fields`。也可以临时覆盖：

```bash
python3 scripts/run_experiment.py \
  --tasks TA-02 \
  --agent-visible-fields task_id,category,difficulty,tool_requirement,prompt,required_output_format,author \
  --dry-run
```

`evaluation_criteria`、`ground_truth`、`expected_failure_risks`、`scoring_rubric`、`required_evidence` 被标记为保护字段。若确实要做“开卷”消融实验，除了把字段加入白名单，还必须显式传入 `--allow-protected-agent-fields`；日志会记录该实验不再是 blind evaluation。

## 2. 模型 Profiles

统一模型配置在 `configs/model_config.json`。当前示例包含：

| Profile | Provider | 用途示例 |
|---|---|---|
| `deepseek_flash` | DeepSeek | 默认 Candidate |
| `deepseek_pro` | DeepSeek | 更强 DeepSeek 条件 |
| `openai_candidate` | OpenAI | OpenAI Candidate 条件 |
| `openai_judge` | OpenAI | 默认独立 Judge |

列出配置：

```bash
python3 scripts/run_experiment.py --list-models
```

每个 profile 可独立设置：

- `provider`
- `base_url`
- `model`
- `api_key_env`
- `max_tokens_param`
- `request_options`
- token、超时、重试和价格估算参数

DeepSeek 和 OpenAI 都通过 OpenAI-compatible Chat Completions 适配器调用；provider 特有参数只放在对应 profile 中，不会再把 DeepSeek 的 `thinking` 参数发给 OpenAI。

模型 ID 和可用性可能随账号及 API 更新变化。可以直接编辑 profile 的 `model`；OpenAI 当前模型目录见 [OpenAI Models](https://developers.openai.com/api/docs/models)。

## 3. 一次性配置 API Key

不要把 key 写进 `model_config.json`，也不要用命令行参数传 key。

运行：

```bash
python3 scripts/configure_models.py
```

程序使用隐藏输入读取 DeepSeek/OpenAI key，并保存到：

```text
.secrets/model_keys.json
```

该文件权限会设置为 `0600`，`.secrets/` 已加入 `.gitignore`。运行时优先级为：

```text
环境变量 > .secrets/model_keys.json
```

因此 CI 或临时终端仍可使用：

```bash
export DEEPSEEK_API_KEY='...'
export OPENAI_API_KEY='...'
```

只更新一个 provider：

```bash
python3 scripts/configure_models.py --provider openai
```

## 4. 运行 Candidate Benchmark

默认使用 `defaults.candidate`（当前是 `deepseek_flash`）：

```bash
python3 scripts/run_experiment.py --overwrite
```

选择一个 Candidate profile：

```bash
python3 scripts/run_experiment.py \
  --candidate-profile openai_candidate \
  --overwrite
```

一次运行多个 Candidate 模型：

```bash
python3 scripts/run_experiment.py \
  --candidate-profiles deepseek_flash,openai_candidate \
  --overwrite
```

临时覆盖单个 profile 的模型 ID：

```bash
python3 scripts/run_experiment.py \
  --candidate-profile openai_candidate \
  --model YOUR_MODEL_ID \
  --overwrite
```

只跑少量题目/协议：

```bash
python3 scripts/run_experiment.py \
  --tasks TA-02,SE-02 \
  --protocols single_agent,sequential_handoff,shared_blackboard \
  --candidate-profile deepseek_flash \
  --overwrite
```

查看协议：

```bash
python3 scripts/run_experiment.py --list-protocols
```

新 `run_id` 包含 task、protocol、Candidate profile/model 和 run number，因此不同模型不会互相覆盖或被错误跳过。

## 5. 使用独立 Judge 评分

默认使用 `defaults.judge`（当前是 `openai_judge`）：

```bash
python3 scripts/score_outputs.py --overwrite
```

选择 Judge：

```bash
python3 scripts/score_outputs.py \
  --judge-profile openai_judge \
  --overwrite
```

一次比较多个 Judge：

```bash
python3 scripts/score_outputs.py \
  --judge-profiles openai_judge,deepseek_pro \
  --overwrite
```

只给某个 Candidate profile 评分：

```bash
python3 scripts/score_outputs.py \
  --candidate-profiles openai_candidate \
  --judge-profile openai_judge
```

每条分数使用独立 `score_id = run_id + Judge profile/model`。`--overwrite` 只重算相同 run/Judge 组合，不删除其他 Judge 的结果。

Judge 返回逐项 `criterion_scores`、检测到的 failure risks、硬性 cap、准确性、完整性、帮助性和 hallucination rate。Python 使用统一公式计算并应用 cap：

```text
overall_quality_score =
  0.35 * accuracy_norm
  + 0.30 * completeness_norm
  + 0.20 * helpfulness_norm
  + 0.15 * (1 - hallucination_rate)
```

其中 completeness 优先由逐项 criterion score 按权重确定性计算。

## 6. 汇总结果

```bash
python3 scripts/aggregate_results.py
```

默认按完整实验条件分组：

```text
Candidate provider/profile/model
+ Candidate visibility status
+ Judge provider/profile/model
+ protocol
```

因此不同模型或不同 Judge 不会混进同一个协议平均值。若只想得到旧式“按协议汇总”：

```bash
python3 scripts/aggregate_results.py --group-by protocol
```

主要输出：

- `logs/raw/*.json`：Candidate run logs
- `results/scores.jsonl` / `scores.csv`：Judge 评分
- `results/aggregate_results.json` / `.csv`：条件汇总
- `results/experiment_summary.md`：摘要与低分案例

## 7. Dry-run 与测试

Dry-run 不调用 API：

```bash
python3 scripts/run_experiment.py \
  --tasks TA-02 \
  --protocols single_agent,debate \
  --candidate-profile deepseek_flash \
  --dry-run \
  --overwrite

python3 scripts/score_outputs.py \
  --judge-profile openai_judge \
  --dry-run \
  --overwrite

python3 scripts/aggregate_results.py
```

运行回归测试：

```bash
python3 -m unittest discover -s tests -v
```

测试覆盖模型 profile/key 安全、DeepSeek/OpenAI 请求差异、字段投影、Judge 私有视图、六种协议的 canary 泄露检查、run/score 唯一标识和多模型聚合隔离。

## 8. 现有日志与数据污染说明

修复前的现有 24 个 `logs/raw/*.json` 把 `evaluation_criteria` 和 `required_evidence` 发给了 Candidate，并写进 prompts，因此这些结果不能作为 blind benchmark 与新结果直接比较。

代码不会删除这些历史文件。`score_outputs.py` 默认检测并跳过它们：

```text
legacy-contaminated
```

如果仅为了历史复核而确实需要评分，可显式使用：

```bash
python3 scripts/score_outputs.py --include-compromised-logs
```

建议新实验使用新的 run ID 和新的结果文件，或在论文中把旧数据明确标为 contaminated/legacy。

## 9. Tool Requirement 限制

当前协议执行器还没有外部网页/检索工具层，但 benchmark 中存在 `tool_requirement = Required` 的题目。这类 run 会写入 `validity_warnings`，并记录 `tool_access_used=false`，不能视为满足相同工具条件的有效实验。

需要严格阻止这类运行时：

```bash
python3 scripts/run_experiment.py --strict-tool-requirements
```

将来加入工具时，Candidate 应在独立沙箱中运行，不能直接读取 `benchmark/`、Judge 结果或其他 run logs；仅过滤 prompt 不足以防止文件工具绕过白名单。

## 10. 项目结构

```text
benchmark/                  完整 benchmark JSON 与评分说明
configs/model_config.json  Provider/model profiles（不含 key）
configs/experiment_config.json
scripts/configure_models.py
scripts/run_experiment.py
scripts/score_outputs.py
scripts/aggregate_results.py
src/llm_client.py          统一 OpenAI-compatible 客户端
src/tasks.py               schema 与 Candidate/Judge 字段投影
src/prompts.py             Candidate/Judge 独立提示词
src/protocols.py           多智能体协议
src/scorer.py              Judge 结果解析与统一评分
src/analysis.py            多条件聚合
tests/                     回归测试
```