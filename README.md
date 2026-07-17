# Multi-Agent Communication Protocol Benchmark

这是一个用于比较多智能体通信协议的可复现实验平台。协议实现按照
《Communication Protocols for Multi Agent LLM Systems》的实验设计，benchmark 使用项目当前已有的 B–E 四组任务：

- 1 个 Single Agent 基线；
- 1 个 Unstructured Group Chat 对照；
- 6 个结构化通信协议；
- 6 类、共 24 道 benchmark 任务；
- 独立 Agent 与 Judge 模型；
- 条件级日志隔离、成本统计、失败模式分析和可复现实验清单。

项目主体只依赖 Python 标准库。

## 1. 实验术语

- Agent：执行任务的模型实例。多智能体条件下由 Planner、Researcher、Analyst、Critic、Writer 等角色组成。
- Judge：独立评分模型，只读取 Agent 最终答案及允许的评测字段。
- Protocol：Agent 之间的消息流、可见性、轮数和终止规则。
- Condition：benchmark、Agent 模型、protocol、字段可见性、工具策略等配置的完整组合。
- Run：某个 Condition 在一道题上的一次重复实验。

代码、命令行参数和日志统一使用 Agent/Judge 命名，不包含旧命名或旧日志兼容接口。

## 2. 八个实验 Protocol

| ID | 通信条件 | 核心消息流 | 默认终止方式 |
|---|---|---|---|
| single_agent | Single Agent baseline | 一个通用 Agent 独立作答 | 首次最终答案 |
| unstructured_group_chat | Protocol 0 | 所有角色共享群聊，自由迭代 | 达到轮数上限后 Writer 汇总 |
| sequential_handoff | Protocol A | Planner → Researcher → Analyst → Writer | 单向交接完成 |
| shared_blackboard | Protocol B | 各角色分轮写入共享黑板 | 两轮更新后 Writer 汇总 |
| manager_worker | Protocol C | Manager 分配任务，Workers 返回结果 | Manager/Writer 汇总完成 |
| debate | Protocol D | 独立方案 → 交叉批评 → 综合 | 辩论轮次结束后 Writer 综合 |
| voting | Protocol E | 独立方案 → 匿名投票 | 多数票；平票按固定规则决胜 |
| dynamic_task_allocation | Protocol F | 能力提议 → 动态分配 → 执行 → 缺口复核 | Writer 根据分配结果与复核汇总 |

列出当前协议及默认预算：

    python3 scripts/run_experiment.py --list-protocols

协议级 max_rounds、max_interactions 和 max_total_tokens 可在
configs/experiment_config.json 的 protocols.config 中修改，也可通过命令行临时覆盖。

## 3. Benchmark

完整入口是 benchmark/benchmark-full.json。它只引用 benchmark-B.json、
benchmark-C.json、benchmark-D.json 和 benchmark-E.json，共 24 道题，每类 4 道：

- Literature Review
- Technical Analysis
- Software Engineering
- Market Research
- Educational Content
- Strategic Planning

每道题都有稳定 task_id、difficulty、tool_requirement、required_output_format、
evaluation_criteria、ground_truth、scoring_rubric、required_evidence 和
expected_failure_risks。

验证题数、类别分布、字段结构和重复 ID：

    python3 scripts/validate_benchmark.py

运行和评分都直接使用 benchmark 文件、task_id 与可读配置，不生成内容哈希或版本字段。

## 4. Agent 与 Judge 的数据边界

Agent 默认只能看到：

    task_id
    category
    difficulty
    tool_requirement
    prompt
    required_output_format

Judge 始终使用完整字段评分，除上述字段外还包括：

    author
    evaluation_criteria
    ground_truth
    expected_failure_risks
    scoring_rubric
    required_evidence
    notes（题目存在时）

查看某道题实际提供给 Agent 的内容：

    python3 scripts/run_experiment.py --tasks TA-04 --print-agent-view

查看所有可选字段：

    python3 scripts/run_experiment.py --list-task-fields

如需让 Multi-Agent 同时接收评分字段，必须在运行阶段显式允许。例如：

    python3 scripts/run_experiment.py \
      --tasks LR-02 \
      --agent-visible-fields task_id,category,difficulty,tool_requirement,prompt,required_output_format,evaluation_criteria,ground_truth,expected_failure_risks,scoring_rubric,required_evidence \
      --allow-protected-agent-fields

这只改变第一步实际传给 Agents 的字段。日志直接记录 `agent_visible_fields`，不再额外定义模式标签；
评分命令对所有日志使用同一套完整 Judge 字段，不跳过任何字段配置。

## 5. 模型 Profiles

统一配置位于 configs/model_config.json。当前示例 profile：

| Profile | 默认用途 |
|---|---|---|
| deepseek_v4_flash | Agent |
| deepseek_v4_pro | Agent 或 Judge |
| openai_gpt_5_4_mini | 默认 Judge，也可作为 Agent |
| openai_gpt_5_5 | Agent 或 Judge |
| openai_gpt5_nano | 低成本 Agent 或 Judge |

列出解析后的模型配置：

    python3 scripts/run_experiment.py --list-models

列表输出只保留模型名和密钥环境名；profile 本身仍然可以完整配置：

- display_name、description、supported_roles；
- provider、base_url、api_key_env、model；
- max_tokens_param；
- max_tokens、agent_max_tokens、final_max_tokens、judge_max_tokens；
- timeout_seconds、max_retries；
- request_options；
- capabilities；
- pricing_per_1m_tokens.input 与 pricing_per_1m_tokens.output。

修改模型 ID、token 上限、价格或请求参数时，应新建或改名 profile，以便实验记录更易追踪。
DeepSeek 和 OpenAI 都由 src/llm_client.py 中的统一 OpenAI-compatible HTTP client 调用。

## 6. API Key

不要把密钥写入配置或命令行。运行：

    python3 scripts/configure_models.py

密钥保存到已被忽略的 .secrets/model_keys.json，文件权限为 0600。也可使用环境变量：

    export DEEPSEEK_API_KEY='...'
    export OPENAI_API_KEY='...'

环境变量优先于本地 secrets 文件。

## 7. 运行实验

先用 Mock 模型检查完整 8 协议流程：

    python3 scripts/run_experiment.py \
      --benchmark benchmark/benchmark-full.json \
      --tasks TA-04 \
      --protocols all \
      --out-dir /tmp/multi-agent-check \
      --dry-run

运行正式全量条件：

    python3 scripts/run_experiment.py \
      --benchmark benchmark/benchmark-full.json \
      --agent-profile deepseek_v4_flash \
      --protocols all

比较多个 Agent 模型：

    python3 scripts/run_experiment.py \
      --agent-profiles deepseek_v4_flash,openai_gpt_5_4_mini \
      --protocols all

文件名和 run_id 只包含任务、protocol、model 和 replicate。切换模型或 protocol 不会与旧日志冲突。
如果改变 Agent 可见字段、benchmark 或 protocol 参数，请使用不同的 `--out-dir` 或 `--run-number`；
日志内部保留全部可读配置，程序发现同名文件配置不一致时会拒绝覆盖。

默认不覆盖已有 run。--overwrite 只允许覆盖同一个 run_id 且配置完全一致的文件，不会删除
其他模型或其他 condition 的日志。每次调用还会生成可读 manifest；如 manifest 名称相同但实验范围
不同，程序同样会拒绝覆盖。项目不生成或校验哈希，也不维护项目版本字段。

## 8. 独立评分

默认 Judge 来自 model_config.json 的 defaults.judge：

    python3 scripts/score_outputs.py \
      --benchmark benchmark/benchmark-full.json

选择或比较 Judge：

    python3 scripts/score_outputs.py --judge-profile openai_gpt_5_4_mini
    python3 scripts/score_outputs.py --judge-profiles openai_gpt_5_4_mini,deepseek_v4_pro

只评分指定 Agent 模型：

    python3 scripts/score_outputs.py --agent-models deepseek-v4-flash

运行与评分默认使用 `logs/raw/current`。评分脚本只读取 `--logs-dir` 指定目录的第一层 JSON 文件，
不会递归混入其他历史实验目录。
评分记录使用任务、protocol、Agent model、replicate 和 Judge model 组成可读 score_id。Judge 始终读取
完整 benchmark 评分字段；评分时只要求日志的 task_id 存在于所选 benchmark，不校验日志来源文件。
已有同一个 score_id 时，默认跳过完全相同的评分；如 Judge token 上限或字段集发生变化，
程序会要求显式加上 `--overwrite`，然后用当前完整字段重新评分并替换旧记录。单条评分失败会写入错误
JSONL 并继续处理其他日志；`--fail-fast` 可改为立即停止。

Judge token 上限由 judge_max_tokens 控制，避免较长逐项评分因为通用 max_tokens 太小而被截断。

## 9. 聚合结果

    python3 scripts/aggregate_results.py \
      --scores-jsonl results/scores.jsonl \
      --group-by condition


可按 condition 或 protocol 聚合。主要指标包括：

- overall_quality_score；
- accuracy、completeness、helpfulness；
- hallucination_rate；
- total_tokens、runtime_seconds、estimated_cost；
- interaction_count、rounds_completed；
- agreement_rate、critique_acceptance_rate、tool_call_count；
- quality_token_ratio 与 quality_api_cost_ratio；

质量公式为：

    0.35 × accuracy
    + 0.30 × completeness
    + 0.20 × helpfulness
    + 0.15 × (1 - hallucination_rate)

硬性失败 cap 会在统一公式后应用。

## 10. 工具任务限制

benchmark 中 tool_requirement=Required 的任务需要真实工具执行层。当前 runner 只调用
LLM API，尚未实现浏览、代码执行或检索工具。因此这类 run 会明确记录
tool_access_used=false 并输出警告，不能当作受控有效结果。

扩大 Agent 字段可见性并不等于获得外部工具。不要仅通过配置
available_tools 来隐藏警告；在实现真实工具调用、调用日志和工具结果注入前，应保留该警告。

## 11. 失败分析与复现

configs/experiment_config.json 定义论文中的完整失败分类：

- Coordination Failure
- Communication Failure
- Role Confusion
- Hallucination Propagation
- Premature Consensus
- Over-Collaboration
- Manager Bottleneck
- Noise Accumulation

建议对每个主要 condition 至少人工复核 5 个失败样本或 20% 的 run。正式报告应保存：

- benchmark-full.json 与 B–E 四个 shard；
- model_config.json、experiment_config.json；
- experiment manifest；
- raw JSONL 日志、评分 JSONL/CSV；
- 聚合摘要；
- 运行时环境和实际 API 模型 ID。

## 12. 运行检查

执行 benchmark 与 Python 语法检查：

    python3 scripts/validate_benchmark.py
    python3 -m compileall -q src scripts

项目不会自动删除已有 raw log 或 results。若要归档大型实验，建议为不同条件使用独立 `--out-dir`，
整体复制该目录，而不是每跑一次就手动打包全部日志。
