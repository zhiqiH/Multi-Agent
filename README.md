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

Judge 始终使用完整字段评分，除上述字段外还包括：

    author
    evaluation_criteria
    ground_truth
    expected_failure_risks
    scoring_rubric
    required_evidence
    evidence_policy（Required 题）
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
|---|---|
| gpt_4o_mini | 默认 Agent，也可作为 Judge |
| gpt_4_1_mini | Agent 或 Judge |
| deepseek_v4_pro | Agent 或 Judge |
| gpt_5_4_mini | 默认 Judge，也可作为 Agent |
| gpt_5_5 | Agent 或 Judge |
| gpt_5_nano | 低成本 Agent 或 Judge |
| deepseek_v4_flash | 可选 Agent 或 Judge |

列出解析后的模型配置：

    python3 scripts/run_experiment.py --list-models

列表输出只保留模型名和密钥环境名；profile 本身仍然可以完整配置：

- display_name、description、supported_roles；
- provider、base_url、api_key_env、model；
- max_tokens_param；
- max_tokens、role_max_output_tokens、judge_max_tokens；
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

    python3 scripts/run_experiment.py

对完整 24 道 benchmark 使用当前默认 OpenAI Agent 运行正式全量条件：

    python3 scripts/run_experiment.py \
      --benchmark benchmark/benchmark-full.json \
      --agent-profile gpt_4o_mini \
      --protocols all

比较多个 Agent 模型：

    python3 scripts/run_experiment.py \
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

    python3 scripts/run_experiment.py --max-total-tokens 80000

运行器在每一次模型请求前检查预算，包括工具调用后的后续模型请求。检查会保守估算下一次输入，
并结合最大输出额度和安全余量决定是否继续；前置 Agent 达到非最终预算线时会停止调用并保留 Writer
额度。日志中的 `role_usage`、`budget_utilization`、`budget_remaining_tokens`、
`budget_limited_call_count` 和 `budget_skipped_call_count` 可用于定位成本。100,000 只约束 Agent
run；Judge 是独立评分调用，由 `judge_max_tokens` 限制单次输出。

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

    python3 scripts/score.py

选择或比较 Judge：

    python3 scripts/score.py --judge-profile gpt_5_4_mini
    python3 scripts/score.py --judge-profiles gpt_5_4_mini,deepseek_v4_pro

只评分指定 Agent 模型：

    python3 scripts/score.py --agent-models gpt-4o-mini

如需只按 protocol 聚合：

    python3 scripts/score.py --group-by protocol

故障分析默认把同任务、同模型、同 Judge 的 Single Agent 作为 baseline。当 multi-agent 分数比该
baseline 低超过 15% 时记录异常退化信号；阈值可调整，但只有 raw log 同时满足某类故障的可观察
证据门槛时才会写入具体 `failure_type`：

    python3 scripts/score.py --relative-failure-drop 0.15

所有评分与聚合文件固定写入同一结果目录。默认为 `results/current/`，也可整体切换：

    python3 scripts/score.py --results-dir results/gpt4o_mini

运行与评分默认使用 `logs/raw/current`。评分脚本只读取 `--logs-dir` 指定目录的第一层 JSON 文件，
不会递归混入其他历史实验目录。
评分记录使用任务、protocol、Agent model、replicate 和 Judge model 组成可读 score_id。Judge 始终读取
完整 benchmark 评分字段。评分前会比较 raw log 与当前 benchmark 的 `tool_requirement`、工具白名单、
工具契约，以及新日志保存的完整 Agent 可见任务快照；不一致时会在调用 Judge 前终止，要求先重跑实验，
避免把旧条件日志计为误导性的零分。
已有同一个 score_id 时，默认跳过完全相同的评分；如 Judge token 上限或字段集发生变化，
程序会要求显式加上 `--overwrite`，然后用当前完整字段重新评分并替换旧记录。单条评分失败会写入错误
JSONL 并继续处理其他日志；`--fail-fast` 可改为立即停止。

Judge token 上限由 judge_max_tokens 控制，避免较长逐项评分因为通用 max_tokens 太小而被截断。

## 9. 第三步：生成可视化

评分完成后运行：

    python3 scripts/plot_figures.py

脚本默认读取 `results/current/scores.csv`，并将 PNG 图片统一写入
`results/current/figures/`。如果评分时使用了其他结果目录，可保持相同目录运行：

    python3 scripts/plot_figures.py --results-dir results/gpt4o_mini

脚本只生成以下五张图片：

- `protocol_quality.png`：protocol 平均质量与 95% 置信区间；
- `category_protocol_quality.png`：任务类别与 protocol 的平均质量热力图；
- `failure_distribution.png`：固定显示九类故障和 `No Failure`，包括计数为 0 的类别；`scores.csv` 中每一次
  评分恰好计入一个类别，包括 `Single Agent` 和无效执行。图中所有类别使用同一种颜色，故障类型
  完全来自评分阶段对 raw log 的审计，不再由绘图脚本按绝对分数二次判断；
- `protocol_token_quality.png`：每个 protocol 一个散点，横坐标为平均 Agent token，纵坐标为平均
  quality score；token 轴使用对数坐标；
- `protocol_parallel_coordinates.png`：按 `Protocol → Mean tokens → Mean time → Mean quality`
  展示每个 protocol 的平均资源—质量路径；token 和 time 使用对数变换，quality 保持 0–1 线性刻度。

再次运行时会移除本脚本过去生成的其他旧图，包括已停用的 `quality_vs_tokens.png`，避免
`figures` 目录混入已经停用的指标。

## 10. 结果文件

执行 `score.py` 后会在同一个 `--results-dir` 中同时得到：

- `scores.jsonl`：完整评分记录；
- `scores.csv`：表格化逐条分数；
- `scoring_errors.jsonl`：本次评分错误；
- `aggregate_results.json` 和 `aggregate_results.csv`：聚合分数；
- `summary.md`：可直接阅读的汇总；
- `figures/*.png`：第三步生成的可视化图片。

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

评分采用三层机制，避免“答案看起来可信但没有真正读取来源”仍获得高分：

1. 确定性执行审计从 raw log 重建实际工具轨迹，区分发现型调用和实质证据调用，并提取
   已抓取 URL、论文 DOI/ArXiv ID、本地文档、来源标题和检索时间。
2. Judge 除完整 benchmark 字段与最终答案外，还会收到压缩后的证据账本和来源摘录。
   最终答案中的 URL、论文标识和标题必须能够与实际访问记录对齐；只在搜索结果中出现、
   没有抓取、或完全未出现于工具日志中的引用均视为未验证。
3. 确定性响应审计直接检查 Markdown 表头、必需章节、精确项目数量、题目数量和学术标识符，
   并把这些可机械验证的事实作为对应 criterion 的上限，避免 Judge 把缺失矩阵或错误数量误判为满分。

执行审计还会比较 benchmark 白名单、运行时实际暴露的工具面和真实调用轨迹。暴露或调用未声明
工具、以及工具输出不符合 `tool_expectations.required_output`，都会令该次执行无效并将主分数上限
设为 0；Judge 不能覆盖这一确定性结论。

每道 Required 题的 `evidence_policy` 把自然语言要求转成确定性门槛，包括最低实质来源数、
最低学术记录数、必需官方域名组、本地文档数、统一学术平台、共同检索日期和最低引用
可追溯率。未满足策略时主分数会应用该题配置的证据上限，即使 Judge 忽略了来源缺口也
不能突破该上限。

Judge 返回的 evidence cap 只作为诊断记录，不再直接覆盖主分数。最终 evidence cap 只来自上述
确定性执行与证据审计；因此 Prohibited 任务在正确地不调用工具时不会因为“缺少外部来源”被归零，
Required 任务也不会被 Judge 自报的、与工具轨迹冲突的 cap 二次处罚。Judge 仍负责事实准确性、
语义支持度和帮助性评分，但普通缺项或事实错误必须反映在逐项 criterion、accuracy 和 hallucination 中，
不能擅自创造 benchmark 未定义的硬性封顶。

Required 题没有实质证据调用，或 Prohibited 题出现工具调用时，`evidence_execution_status`
为 `invalid`、`score_eligible=false`，主 `overall_quality_score` 的确定性上限为 0。系统仍保留
`judge_capped_quality_score`，用于区分“文字答案本身看起来不错”和“实验执行有效”。聚合结果
使用主分数，因此无效 run 不会因为 Judge 被表面可信的引用误导而抬高 protocol 平均分。

对于执行有效的 Required 题，确定性审计还会比对答案中的 URL、DOI、ArXiv ID 和已访问
来源标题：完全不可追溯的机器可读引用将把主分数上限设为 0.4；可追溯比例低于一半且没有
匹配来源标题时上限为 0.6；完全没有机器可追溯引用或来源标题时上限为 0.5。更细的“来源
是否为官方、摘录是否支持具体主张”等语义判断仍由看到证据账本的 Judge 完成。

逐条评分还会保存 `citation_traceability_rate`、`substantive_source_count`、
`unaccessed_citation_count`、`judge_evidence_assessment` 和压缩后的 `evidence_audit`。

## 13. 失败分析与复现

`configs/experiment_config.json` 和 Judge 共用以下九类故障分类，另以 `None / No Failure` 表示没有
任何一类故障通过证据门槛：

| 故障类型 | 严格定义 | 判定所需的可观察信号 |
|---|---|---|
| None / No Failure | 没有发现主导性的多智能体协作故障；普通事实错误或小缺项不属于协作故障。 | 九类故障均未通过证据门槛；Single Agent 通常为 `None`，但客观工具约束失败时可为 `Tool Failure`。Figure 显示为 `No Failure`。 |
| Coordination Failure | 任务拆分、执行顺序、依赖、所有权或结果整合失败，造成遗漏、重复、冲突或不完整。 | 子任务无人完成、依赖未满足、工作重复或冲突未解决，或 final output 未整合已有成果。 |
| Communication Failure | 已产生的重要信息没有沿预期路径传给下游，或内容为空、截断、丢失，最终没有使用。 | 必须同时指出上游消息、预期接收方或后续阶段，以及受影响的 final output。 |
| Role Confusion | Agent 执行了与角色不符的工作，或没有履行角色职责，并实质影响结果。 | 具体角色消息与职责不匹配，例如 Researcher 只写计划、Writer 返回计划而非成品。 |
| Hallucination Propagation | 上游 Agent 引入错误或无证据主张，下游未验证便接受、重复或扩展，最终进入答案。 | 同一可识别主张必须出现在上游消息和 final output；只在最终答案出现的幻觉不属于传播。 |
| Premature Consensus | Agent 在关键事实、约束、反例或明确批评尚未验证时过早收敛，且该共识进入最终答案。 | 必须同时引用初始方案、另一 Agent 的明确接受或投票，以及没有解决的可观察问题；高 agreement rate 或全票一致单独不足。 |
| Over-Collaboration | 过多轮次、消息或 token 用于重复协调或劳动，却没有改善结果，甚至降低质量。 | 必须同时出现高开销、重复内容和不完整、嘈杂或整合较差的 final output；高 token 单独不足。 |
| Manager Bottleneck | 在层级协议中，Manager 的遗漏、错误分配、失真汇总或阻断协作成为结果失败的直接原因。 | 必须引用一条具体 Manager 消息、一条受影响的下游 Agent 消息和 final output；单纯的 worker 错误不够。 |
| Noise Accumulation | 共享工作区累积无关、重复、矛盾或误导信息，后续 Agent 没有清理并将其带入最终整合。 | 必须引用至少两条具体 blackboard 消息及 final output；工作区很长或消息很多单独不足。 |
| Tool Failure | 显式工具要求或工具输出契约失败，导致必需证据未取得、使用了禁止工具或最终答案依赖无效执行。 | Required run 的 `tool_requirement_satisfied=false`、Prohibited run 出现调用、未授权工具、工具契约失败；无害的 Optional 调用失败不够。 |

Judge 会读取 raw log 中完整的中间 Agent 消息和可观察运行指标，评分器随后执行与 protocol 无关的
确定性日志审计。任何非 `None` 分类都必须保存 `failure_evidence` 并引用评分提示显式列出的真实 trace；
`Tool Failure` 必须引用 `tool_execution`，`Over-Collaboration` 必须引用 `run_metrics` 和至少两条重复消息，
Manager 与 blackboard 专属故障还必须满足相应 protocol 和消息 channel 的证据门槛。
分数相对 Single Agent 下降超过阈值只产生“疑似故障”信号；只有工具失败、预算终止并伴随重复劳动，
或 Judge 从消息传递链观察到其他严格信号时才分类。这样 failure 的因果来源始终是 log，而不是分数本身。

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
