# Multi-Agent Communication Protocol Benchmark

这是一个用于比较多智能体通信协议的可复现实验平台。协议实现按照
《Communication Protocols for Multi Agent LLM Systems》的实验设计，benchmark 使用项目当前已有的 B–E 四组任务：

- 1 个 Single Agent 基线；
- 1 个 Unstructured Group Chat 对照；
- 6 个结构化通信协议；
- 6 类、共 24 道 benchmark 任务；
- 独立 Agent 与 Judge 模型；
- 条件级日志隔离、成本统计、失败模式分析和可复现实验清单。

项目主体使用 Python 标准库；本地 PDF 论文提取使用 `pypdf`。首次运行前安装：

    python3 -m pip install -r requirements.txt

## 1. 实验术语

- Agent：执行任务的模型实例。多智能体条件下由 Planner、Researcher、Analyst、Critic、Writer 等角色组成。
- Quality Judge：独立盲评模型，只读取完整 benchmark 评分字段和 Agent 最终答案。
- Failure Analyzer：与质量评分隔离的日志分析调用，只判定 failure，不产生或修改质量分数。
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

    python3 scripts/experiment.py --list-protocols

协议轮数和交互次数可在 configs/experiment_config.json 的 `protocols` 中修改。
每次 run 的总 token 预算统一放在 `run_policy` 中，也可用 `--max-total-tokens` 临时覆盖。

## 3. Benchmark

完整入口是 benchmark/benchmark-full.json。它只引用 benchmark-B.json、
benchmark-C.json、benchmark-D.json 和 benchmark-E.json，共 24 道题，一共 6 类问题，每类 4 道：

- Literature Review
- Technical Analysis
- Software Engineering
- Market Research
- Educational Content
- Strategic Planning

每道题都有稳定 task_id、difficulty、tool_requirement、required_output_format、
evaluation_criteria、ground_truth、scoring_rubric、required_evidence 和
expected_failure_risks。工具策略由任务自己的 `available_tools` 和 `tool_expectations`
定义；Required 题还包含结构化、仅 Judge 可见的 `evidence_policy`。

Benchmark C 是当前规范格式。Benchmark D 保留原文件不变，加载时由代码在内存中把旧版
`evaluation_rubric` 转换为当前 Judge 字段，并为其中的 Required 题补充兼容工具策略；转换结果
只用于运行和评分，不会写回 benchmark 文件。其他尚未包含任务级工具字段的旧任务，会根据其
`evidence_policy` 推导最小工具集合；显式声明了 `available_tools` 的任务始终以声明值为准。

运行和评分在读取 benchmark 时会自动检查必需字段、task_id 格式和重复 ID，
因此不需要额外的验证步骤。项目不生成内容哈希或版本字段。

## 4. Agent 与 Judge 的数据边界

Agent 默认只能看到：

    task_id
    category
    difficulty
    tool_requirement
    available_tools
    tool_expectations
    prompt
    required_output_format

Quality Judge 始终使用完整字段评分，除上述字段外还包括：

    author
    evaluation_criteria
    ground_truth
    expected_failure_risks
    scoring_rubric
    required_evidence
    evidence_policy（Required 题）
    notes（题目存在时）

在 Agent 生成的内容中，Quality Judge 只能看到 `final_output`：不会收到 protocol 名称、角色、
中间消息、handoff、工具调用、运行错误、token 或通信指标。Failure Analyzer 才会单独读取
`intermediate_messages`、运行摘要和 `final_output`，其输出只写入 failure 字段，无法参与质量分计算。
工具与格式约束由模型调用之外的确定性审计执行。

查看某道题实际提供给 Agent 的内容：

    python3 scripts/experiment.py --tasks TA-04 --print-agent-view

查看所有可选字段：

    python3 scripts/experiment.py --list-task-fields

如需让 Multi-Agent 同时接收评分字段，必须在运行阶段显式允许。例如：

    python3 scripts/experiment.py \
      --tasks LR-02 \
      --agent-visible-fields task_id,category,difficulty,tool_requirement,prompt,required_output_format,evaluation_criteria,ground_truth,expected_failure_risks,scoring_rubric,required_evidence \
      --allow-protected-agent-fields

这只改变第一步实际传给 Agents 的字段。日志直接记录 `agent_visible_fields`，不再额外定义模式标签；
评分命令对所有日志使用同一套完整 Judge 字段，不跳过任何字段配置。

## 5. 模型 Profiles

统一配置位于 configs/model_config.json。当前示例 profile：

| Profile | 默认用途 |
|---|---|
| gpt_4o_mini | 默认 Agent，也可作为 Judge |
| gpt_4_1_mini | Agent 或 Judge |
| deepseek_v4_pro | Agent 或 Judge |
| gpt_5_4_mini | 默认 Judge，也可作为 Agent |
| gpt_5_5 | Agent 或 Judge |
| gpt_5_nano | 低成本 Agent 或 Judge |
| deepseek_v4_flash | 可选 Agent 或 Judge |

列出解析后的模型配置：

    python3 scripts/experiment.py --list-models

列表输出只保留模型名和密钥环境名；profile 本身仍然可以完整配置：

- display_name、description、supported_roles；
- provider、base_url、api_key_env、model；
- max_tokens_param；
- max_tokens、role_max_output_tokens、judge_max_tokens、failure_analysis_max_tokens；
- timeout_seconds、max_retries；
- request_options；
- capabilities；
- pricing_per_1m_tokens.input 与 pricing_per_1m_tokens.output。

修改模型 ID、token 上限、价格或请求参数时，应新建或改名 profile，以便实验记录更易追踪。
Agent 协议和评分逻辑只依赖 src/llm_client.py 中的通用 `LLMClient` 接口。当前 DeepSeek 和
OpenAI 使用 `ChatCompletionsClient` HTTP 实现。新增支持同类请求格式的 provider 只需添加 model profile；
如果未来使用 Google 原生 API，只需新增实现 `LLMClient` 的 provider client，不需要修改 protocol 或评分代码。

## 6. API Key

不要把密钥写入配置或命令行。运行：

    python3 scripts/configure_models.py

密钥保存到已被忽略的 .secrets/model_keys.json，文件权限为 0600。也可使用环境变量：

    export DEEPSEEK_API_KEY='...'
    export OPENAI_API_KEY='...'

环境变量优先于本地 secrets 文件。

## 7. 第一步：运行实验

使用当前默认 benchmark、8 个 protocol 和 `defaults.agent` 真实模型：

    python3 scripts/experiment.py

对完整 24 道 benchmark 使用当前默认 OpenAI Agent 运行正式全量条件：

    python3 scripts/experiment.py \
      --benchmark benchmark/benchmark-full.json \
      --agent-profile gpt_4o_mini \
      --protocols all

比较多个 Agent 模型：

    python3 scripts/experiment.py \
      --agent-profiles gpt_4o_mini,gpt_5_nano \
      --protocols all

当前默认成本限制如下：

| 角色 | 每次交互最大输出 token |
|---|---:|
| Planner | 900 |
| Researcher | 1800 |
| Analyst | 1300 |
| Critic | 900 |
| Manager | 1300 |
| Writer | 6400 |
| Single Agent | 6400 |

这些值由 model_config.json 的 `role_max_output_tokens` 控制。实验中的每个“任务 × protocol ×
Agent model × replicate”是一个独立 run，默认最多消耗 100,000 个实际 API 输入+输出 token，
并为含最终 Writer 的 protocol 预留 20,000（Single Agent 与 Voting 不需要这项预留）。总预算由
experiment_config.json 的 `run_policy` 控制，也可临时覆盖：

    python3 scripts/experiment.py --max-total-tokens 80000

运行器在每一次模型请求前检查预算，包括工具调用后的后续模型请求。检查会保守估算下一次输入，
并结合最大输出额度和安全余量决定是否继续；前置 Agent 达到非最终预算线时会停止调用并保留 Writer
额度。日志中的 `role_usage`、`budget_utilization`、`budget_remaining_tokens`、
`budget_limited_call_count` 和 `budget_skipped_call_count` 可用于定位成本。100,000 只约束 Agent
run；评分阶段包含相互隔离的 Quality Judge 与 Failure Analyzer 调用，输出分别由
`judge_max_tokens` 和 `failure_analysis_max_tokens` 限制。

工具交互也设置为每次 Agent 交互最多 3 轮、4 个调用，单个工具结果最多 24,000 字符；批量读取时
这个字符额度会在各来源之间分配，避免一次批量 PDF/网页读取把后续所有请求都推高。

文件名和 run_id 只包含任务、protocol、model 和 replicate。切换模型或 protocol 不会与旧日志冲突。
如果改变 Agent 可见字段、benchmark 或 protocol 参数，请使用不同的 `--out-dir` 或 `--run-number`；
日志内部保留全部可读配置，程序发现同名文件配置不一致时会拒绝覆盖。

默认不覆盖已有 run。--overwrite 只允许覆盖同一个 run_id 且配置完全一致的文件，不会删除
其他模型或其他 condition 的日志。每次调用还会生成可读 manifest；如 manifest 名称相同但实验范围
不同，程序同样会拒绝覆盖。项目不生成或校验哈希，也不维护项目版本字段。

## 8. 第二步：评分并聚合

默认 Judge 来自 model_config.json 的 `defaults.judge`。一次命令会完成逐条评分、
评分 CSV、聚合 JSON/CSV 和 Markdown 汇总：

    python3 scripts/judge.py

选择或比较 Judge：

    python3 scripts/judge.py --judge-profile gpt_5_4_mini
    python3 scripts/judge.py --judge-profiles gpt_5_4_mini,deepseek_v4_pro

只评分指定 Agent 模型：

    python3 scripts/judge.py --agent-models gpt-4o-mini

如需只按 protocol 聚合：

    python3 scripts/judge.py --group-by protocol

故障类型与质量分数相互独立：分类只依据 raw log、工具执行记录和 final output 中可观察的行为，
不会再通过 Single Agent 分数差或任何质量阈值推断故障。

每条日志会产生两次隔离调用：Quality Judge 只看完整 benchmark 评分字段和 Writer 最终输出；
Failure Analyzer 才看 protocol log。中间 Agent 交互不会进入 Quality Judge 的 prompt，failure 结果也不会
反馈给质量评分公式。确定性工具与格式审计在两次模型调用之外应用。

所有评分与聚合文件固定写入同一结果目录。默认为 `results/current/`，也可整体切换：

    python3 scripts/judge.py --results-dir results/gpt4o_mini

运行与评分默认使用 `logs/current`。评分脚本只读取 `--logs-dir` 指定目录的第一层 JSON 文件，
不会递归混入其他历史实验目录。
评分记录使用任务、protocol、Agent model、replicate 和 Judge model 组成可读 score_id。Quality Judge 始终读取
完整 benchmark 评分字段。评分前会比较 raw log 与当前 benchmark 的 `tool_requirement`、工具白名单、
工具契约，以及新日志保存的完整 Agent 可见任务快照；不一致时会在调用 Judge 前终止，要求先重跑实验，
避免把旧条件日志计为误导性的零分。
已有同一个 score_id 时，默认跳过完全相同的评分；如 Judge token 上限或字段集发生变化，
程序会要求显式加上 `--overwrite`，然后用当前完整字段重新评分并替换旧记录。单条评分失败会写入错误
JSONL 并继续处理其他日志；`--fail-fast` 可改为立即停止。

Quality Judge token 上限由 `judge_max_tokens` 控制；Failure Analyzer 由
`failure_analysis_max_tokens` 控制。输出会分别记录两次调用的 token 和成本，并同时保存合计值。
Failure Analyzer 的字段缺失、引用数量、引用顺序或单个类型的证据格式不会产生 analysis error：代码会逐类
归一化并保留所有已检测 failure。只有模型响应本身不可用时，`failure_analysis_complete` 才为 false，已经
完成的质量分与确定性 raw-log failure 仍会保留。

## 9. 第三步：生成可视化

评分完成后运行：

    python3 scripts/plot.py

脚本默认读取 `results/current/scores.csv`，并将 PNG 图片统一写入
`results/current/figures/`。如果评分时使用了其他结果目录，可保持相同目录运行：

    python3 scripts/plot.py --results-dir results/gpt4o_mini

脚本只生成以下五张图片：

- `protocol_quality.png`：protocol 平均质量与 95% 置信区间；
- `category_protocol_quality.png`：任务类别与 protocol 的平均质量热力图；
- `failure_distribution.png`：固定显示九类故障和 `No Failure`，包括计数为 0 的类别；`scores.csv` 中每一次
  评分至少计入一个状态，一条 log 若有多个协作故障会分别计入多根柱，因此标签计数之和可以大于 run 数；
  只有没有任何故障时才计入 `No Failure`。图中所有类别使用同一种颜色，故障类型完全来自评分阶段对
  raw log 的审计，不再由绘图脚本按绝对分数二次判断；
- `protocol_token_quality.png`：每个 protocol 一个散点，横坐标为平均 Agent token，纵坐标为平均
  quality score；token 轴使用对数坐标；
- `protocol_parallel_coordinates.png`：按 `Protocol → Mean tokens → Mean time → Mean quality`
  展示每个 protocol 的平均资源—质量路径；token 和 time 使用对数变换，quality 保持 0–1 线性刻度。

再次运行时会移除本脚本过去生成的其他旧图，包括已停用的 `quality_vs_tokens.png`，避免
`figures` 目录混入已经停用的指标。

## 10. 结果文件

执行 `judge.py` 后会在同一个 `--results-dir` 中同时得到：

- `scores.jsonl`：完整评分记录；
- `scores.csv`：表格化逐条分数；
- `scoring_errors.jsonl`：本次评分错误；
- `aggregate_results.json` 和 `aggregate_results.csv`：聚合分数；
- `summary.md`：可直接阅读的汇总；
- `figures/*.png`：第三步生成的可视化图片。

聚合文件同时包含 `runs_with_any_failure`、`multi_failure_runs`、`avg_failure_count`，以及每类 failure 的
run count/rate。多标签 rate 的总和允许超过 100%。

默认按 Agent model、Judge model 和 protocol 的完整 condition 聚合，也可按 protocol 聚合。
主要指标包括：

- overall_quality_score；
- accuracy、completeness、helpfulness；
- hallucination_rate；
- total_tokens、budget_utilization、runtime_seconds、estimated_cost；
- role_usage 与每个角色的输入、输出、模型调用次数；
- interaction_count、rounds_completed；
- agreement_rate、critique_acceptance_rate、tool_call_count；
- tool_requirement_satisfied 与工具约束通过率；
- quality_token_ratio 与 quality_api_cost_ratio；

质量公式为：

    0.35 × accuracy
    + 0.30 × completeness
    + 0.20 × helpfulness
    + 0.15 × (1 - hallucination_rate)

硬性失败 cap 会在统一公式后应用。

## 11. 模型工具调用

每道任务的 `available_tools` 是 Agent 实际可见工具的完整白名单，`tool_expectations` 定义这些
工具在该任务中的用途和输出契约。`Prohibited` 任务不会在 API 请求中携带任何工具定义。
`configs/experiment_config.json` 的 `tool_policy.available_tools` 只定义本项目已实现、允许被
benchmark 引用的工具目录；任务只能从目录中选择，不能获得未声明工具：

- `google_search_tool`：Benchmark C 兼容搜索工具，返回 title、URL/DOI 和 snippet；学术型查询优先使用
  Semantic Scholar/OpenAlex，普通网页搜索作为回退，并过滤与查询明显无关的结果；
- `web_search`：检索当前公开网页，可指定官方网站域名；
- `fetch_url` / `fetch_urls`：读取单个或一组网页、公开 PDF 正文；
- `academic_search` / `academic_lookup`：在 Semantic Scholar 或 OpenAlex 检索单篇或一组论文及引用量；
- `calculator`：执行受限算术计算；
- `list_local_documents`、`read_local_document` 和 `read_local_documents`：列出并读取单个或一组允许的本地论文。

Benchmark C 的 LR-03 显式只暴露 `google_search_tool`；MR-03 因要求当前官网价格和产品限制，
暴露 `web_search`、`fetch_url`、`fetch_urls` 和 `calculator`。Benchmark D 的 Required 题因原文件没有
任务级工具字段，内存兼容层同样提供该单一工具。其他旧任务会按照本地文档数、学术记录数和官方
域名组等 `evidence_policy` 门槛推导窄化工具面；Prohibited 题始终不暴露工具。

`Optional` 任务使用 `tool_choice=auto`；`Required` 任务在尚未取得实质证据时，会对
Researcher、Analyst、Writer 或 Single Agent 使用 `tool_choice=required`，取得实质来源后恢复为
`auto`。模型始终只能在当前任务白名单内选择。运行器按照 OpenAI 的
[function calling 流程](https://developers.openai.com/api/docs/guides/tools)执行工具后，
以 `role=tool` 回传结果，直到模型返回最终文本或达到工具预算。每次调用的名称、
参数、输出、角色、轮次、成功状态和耗时都保存在 raw log 的 `tool_calls` 中。

`web_search` 和 `list_local_documents` 只负责发现来源，不计为已经读取证据；
`google_search_tool` 按 Benchmark C 的任务级输出契约产生可审计来源记录。Required 任务必须
成功执行一个已声明的证据工具，且输出满足该任务的 `tool_expectations`。完全相同的重复工具请求
会被拒绝，避免模型在无效搜索上反复消耗 token。

运行进度行只显示实际 token 数和单一 `tool=success|failed|not_required` 信号；最大预算及利用率仍
保存在原始 JSON 日志中供复现和聚合分析，但不在终端进度中重复展示。评分进度行使用同一个工具
信号，不再同时打印 execution、policy 和 citation 三组内部审计状态。

LR-05 要求的七篇本地 PDF 需放入 `benchmark/documents/`。当该目录无文件、
Required 任务没有成功执行证据检索/读取工具，或 Prohibited 任务出现工具调用时，
日志会记录 `validity_warnings`。`tool_requirement_satisfied` 明确记录该 run 是否满足
工具约束。网页工具仅允许公网 HTTP(S) 地址，会拒绝本机、内网、带凭据 URL 和越界
本地文件路径。

## 12. 证据感知评分

评分采用三层机制，同时保持 Quality Judge 的严格盲评边界：

1. 确定性执行审计从 raw log 重建实际工具轨迹，区分发现型调用和实质证据调用，并提取
   已抓取 URL、论文 DOI/ArXiv ID、本地文档、来源标题和检索时间。
2. Quality Judge 只依据完整 benchmark 评分字段和最终答案评价准确性、完整性、帮助性及答案中
   可见的证据表达；它不会收到证据账本、来源摘录、工具轨迹或任何中间 Agent 消息。
3. Judge 返回后，确定性证据与响应审计检查引用是否对应实际访问记录，以及 Markdown 表头、
   必需章节、精确项目数量、题目数量和学术标识符，
   并把这些可机械验证的事实作为对应 criterion 的上限，避免 Judge 把缺失矩阵或错误数量误判为满分。

执行审计还会比较 benchmark 白名单、运行时实际暴露的工具面和真实调用轨迹。暴露或调用未声明
工具、以及工具输出不符合 `tool_expectations.required_output`，都会令该次执行无效并将主分数上限
设为 0；Judge 不能覆盖这一确定性结论。

每道 Required 题的 `evidence_policy` 把自然语言要求转成确定性门槛，包括最低实质来源数、
最低学术记录数、必需官方域名组、本地文档数、统一学术平台、共同检索日期和最低引用
可追溯率。未满足策略时主分数会应用该题配置的证据上限，即使 Judge 忽略了来源缺口也
不能突破该上限。

Quality Judge 返回的 evidence cap 只描述最终答案中可见的证据情况，并作为诊断记录，不直接覆盖主分数。最终 evidence cap 只来自上述
确定性执行与证据审计；因此 Prohibited 任务在正确地不调用工具时不会因为“缺少外部来源”被归零，
Required 任务也不会被 Judge 自报的 cap 二次处罚。Quality Judge 仍负责事实准确性、
语义支持度和帮助性评分，但普通缺项或事实错误必须反映在逐项 criterion、accuracy 和 hallucination 中，
不能擅自创造 benchmark 未定义的硬性封顶。

Required 题没有实质证据调用，或 Prohibited 题出现工具调用时，`evidence_execution_status`
为 `invalid`、`score_eligible=false`，主 `overall_quality_score` 的确定性上限为 0。系统仍保留
`judge_capped_quality_score`，用于区分“文字答案本身看起来不错”和“实验执行有效”。聚合结果
使用主分数，因此无效 run 不会因为 Judge 被表面可信的引用误导而抬高 protocol 平均分。

对于执行有效的 Required 题，确定性审计还会比对答案中的 URL、DOI、ArXiv ID 和已访问
来源标题：完全不可追溯的机器可读引用将把主分数上限设为 0.4；可追溯比例低于一半且没有
匹配来源标题时上限为 0.6；完全没有机器可追溯引用或来源标题时上限为 0.5。更细的“来源
是否为官方、摘录是否支持具体主张”等过程证据不再暴露给 Quality Judge；如需审计，应直接检查
评分文件保存的 `evidence_audit` 与 raw tool log。

逐条评分还会保存 `citation_traceability_rate`、`substantive_source_count`、
`unaccessed_citation_count`、`judge_evidence_assessment` 和压缩后的 `evidence_audit`。

## 13. 失败分析与复现

`src/failure_taxonomy.py` 是 Judge、汇总与绘图共用的唯一 failure taxonomy，包含以下九类故障，另以 `None / No Failure` 表示没有
任何一类故障通过证据门槛。八类协作故障是多标签：同一 log 可以同时记录多类；`Other Failure` 与八类
协作故障互斥；`No Failure` 只能单独出现。

| 故障类型 | 严格定义 | 判定所需的可观察信号 |
|---|---|---|
| None / No Failure | 协议允许的协作故障和具体 residual failure 都没有足够证据。 | 不由模型直接选择；代码在所有逐类检查均为 false 时生成。答案仍可能低分。 |
| Coordination Failure | 任务拆分、执行顺序、依赖、所有权或结果整合失败，造成遗漏、重复、冲突或不完整。 | 子任务无人完成、依赖未满足、工作重复或冲突未解决，或 final output 未整合已有成果。 |
| Communication Failure | 已产生的重要信息没有沿预期路径传给下游，或内容为空、截断、丢失、失真。 | 同时指出上游信息和下游丢失/失真位置；正常收到后产生分歧不属于通信失败。 |
| Role Confusion | Agent 的实际工作与记录的角色、phase 或 `expected_action` 不符；即使后来恢复也可记录。 | 对比消息 sender、phase、expected_action 与 content；例如 allocation 阶段的 Planner 直接提交结论。 |
| Hallucination Propagation | 上游引入同一错误或无证据主张，下游未验证便接受、重复或扩展。 | 同一可识别主张至少出现在上游和一条下游消息；只在单条消息中出现不属于传播。 |
| Premature Consensus | 关键事实、约束、反例或批评尚未验证时，协作提前收敛并关闭或显著缩窄探索。 | 指出未解决问题和至少两个收敛/投票记录；全票或高 agreement rate 单独不足，ballot 数字是 proposal index。 |
| Over-Collaboration | 多轮或多条消息进行近重复工作，没有增加实质信息、纠错或覆盖。 | 引用 `run_metrics` 和至少两条高度重复消息并说明没有信息增益；高 token 单独不足。 |
| Manager Bottleneck | `manager_worker` 中 Manager 的遗漏、错误分配、失真汇总或阻断成为协作瓶颈。 | 引用一条具体 Manager 消息和至少一条受影响的下游消息；可与传播类故障同时出现。 |
| Noise Accumulation | protocol 的共享对话、工作区、辩论、层级或分配上下文积累无关、重复、矛盾或误导信息并被继续使用。 | 至少两条 context-visible 消息及后续复用或未解决证据；不再只限于 blackboard。 |
| Other Failure | 八类协作故障都不成立后仍存在的具体非协作故障。 | 必须给出 subtype：`tool_failure`、`runtime_error`、`malformed_output`、`single_agent_answer_error` 或 `unmapped_non_collaboration_failure`；低分、泛化的“答案不好”或不确定性均不够。 |

各 protocol 的允许集合由 `src/failure_taxonomy.py` 固定：Single Agent 只允许 `No Failure/Other`；
Sequential Handoff 允许 Communication、Role Confusion、Hallucination Propagation；Voting 在此基础上增加
Premature Consensus；Manager-Worker 额外允许 Manager Bottleneck；其余 protocol 按各自通信结构开放
Coordination、Premature Consensus、Over-Collaboration 与 Noise Accumulation。白名单外标签只忽略该标签，
不会影响同一 log 中其他 failure。

Failure Analyzer 会读取 raw log 中完整的中间 Agent 消息、工具记录、运行指标和 final output；Quality Judge
不会看到这些过程内容。Analyzer 对当前 protocol 白名单中的每一类逐一检查，代码再生成
`failure_types` 和逐类 `failure_assessments`。每个阳性类型都有自己的 evidence、是否恢复以及是否影响最终
输出；确定性工具/预算审计与模型结果采用集合合并，不再覆盖已有协作标签。若任一协作类型成立，代码会
抑制 `Other Failure`；若全部不成立且没有 residual failure，代码生成唯一的 `None`。引用数量不设上限；
缺失的 `final_output` 或 `run_metrics` 指针会根据对应声明自动补齐，任何单类格式差异都不会清空其他类型。

failure 与 score 没有直接逻辑关系：高分运行仍可能有日志可证的协作故障，低分运行也可能是
`No Failure`。`No Failure` 约 70% 只作为人工校准预期，不是 Judge 必须凑出的配额。

给 Codex/Failure Analyzer 的最短判定 prompt：

> Independently check every failure type allowed for this protocol; multiple types may coexist. Use only trace-backed
> process evidence, never score. If any collaboration failure is present, omit Other. Use Other only for a concrete
> residual non-collaboration failure after all collaboration checks are false. Code derives No Failure when all checks
> are false; recovered failures still count.

建议对每个主要 condition 至少人工复核 5 个失败样本或 20% 的 run。正式报告应保存：

- benchmark-full.json 与 B–E 四个 shard；
- model_config.json、experiment_config.json；
- experiment manifest；
- raw JSONL 日志、评分 JSONL/CSV；
- 聚合摘要；
- 运行时环境和实际 API 模型 ID。

## 14. 运行检查

如果修改了代码，可执行 Python 语法检查：

    python3 -m compileall -q src scripts

项目不会自动删除已有 raw log 或 results。若要归档大型实验，建议为不同条件使用独立 `--out-dir`，
整体复制该目录，而不是每跑一次就手动打包全部日志。
