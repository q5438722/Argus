# Engineer：Verus API 规格与证明修复（中文审阅稿）

对应[英文角色 Skill](../verus-spec-generation-and-repair.md)。
写 API spec 前，先读[共享规范](../../../references/verus-spec-generation-and-repair.zh-CN.md)、
Manager 范围和 Planner 的子模块/依赖图。
如果直接任务缺少这张图，先补齐必要的子模块与 view 依赖，不能跳过。

## 每个子模块、每个 API 的循环

1. 复用足够的现有 view，或先定义所需 view 并明确对应义务，再写依赖它的合同。
   依赖 constructor 的义务与源代码实现证明一起完成，且必须在验收前闭合。
   遵循已规划的 bottom-up 顺序，或有明确理由的其他顺序。
2. 同时阅读 API 源代码和 docstrings，包括委托调用及边界。
   保留签名和合法输入。
   用确定的 view 及现有借用支持写模块规格，包含必要的 `old`/`final` 写回和 frame。
3. 建立逐 API 源代码实现证明，让 Verus 检查实际有关的函数体/义务。
   源码转换要保留忠实映射；可执行代码重写遵守下面的 issue/review 规则。
   仅调用外部 API、利用其假定合同得到结论，只是客户端证明，不是实现证明。
4. 对同一版当前合同运行真实 `spec-determin-tool` 入口。
   保留逐 API completeness proof/harness、比较关系、query 输入、结果和重放命令。
   不得换工具或削弱比较关系。
5. 任一轴失败或无结论时，根据反馈修复 spec、view、忠实源码证明或检查编码，
   再跑受影响的两条证明链。
   共享 view 变化也会重新打开依赖 API。
   `UNKNOWN` 和零义务运行都不算通过。
6. 当前候选两轴都通过才结束该 API 的 repair。
   若有具体限制无法闭合，保留尝试并报告 blocker；
   不得标记 API 完成，也不能静默改变 Verus 的可信基础。

## 实现可观察协议，而不只是元数据

遵循[抽象接入参考](../../../references/spec-abstraction-integration.zh-CN.md)。
实现足够的既有规格接口，把 constructor 后置接到 consumer 使用的值和状态转换。
Iterator 通过标准剩余序列建模实际返回的 item；仅展平源内容并没有规定这些 item。
用已有借用机制保留可变 item 的初始内容、最终写回与未影响区域的 frame。
不能仅凭构造时等式，就假定消费后辅助 observer 仍等于标准状态。
必要 helper 要有源码依据并接通语义；这不放宽明确的 zero-UF 要求，
也不授权新增可信假设。
在仓库已有验证测试中加入使用真实合同的有界客户端，
覆盖消费和适用的边界/写回情况。

## 编码已批准的相等比较边界

遵循 [TB-PARTIAL-EQ](../../../references/trust-boundaries/partial-eq.zh-CN.md)
的 **conditional-posts-v2**，写入 `trust_boundaries/TB-PARTIAL-EQ.md`。
**如果有需要**，把整个后置集合而非仅返回关系放在
`T::obeys_eq_spec() ==>` 右侧。移除仅由旧规则给 API 添加的 B 前置，
保留原安全前提、签名、可执行体及无关函数。
不统一假设 B 来证明条件合同；显式区分 analysis-only 适配入口，
不把其分析前提加回 API，也不声称无条件确定性。
检查生成比较/reexecute，并按版本保留旧证据。guard 内的内容和状态仍须证明，
不假设目标答案或改写固定 vstd。

## 提出 issue，而不是静默修改 implementation

遇到已复现的不支持 Rust／验证器 feature，遵循
[任务本地 Verus Skill](../../../references/verus-campaign-local-toolchain.zh-CN.md)：
在本任务中从固定 commit 派生，构建匹配 vstd，保留 patch 和二进制来源，
所有相关结果明确标注为本地工具链结果；不修改共享官方工具链。

回调 API 遵循[回调 triage](../../../references/verus-callback-api-triage.zh-CN.md)。
能够 sound 地生成就生成；有界忠实尝试后仍需要大量未支持回调语义时，
保留候选和失败并登记 callback-support local skip，继续其他 API。
不能缩小回调域，也不能把跳过计为完成。

遵循[API 后置直接展开](../../../references/verus-inline-api-postconditions.zh-CN.md)：
在真实 API 的 `ensures` 展开整份 post 包装，保留全部 guard，并展示实际绑定，
不能只证明模型谓词。产物使用指定的[统一根目录](../../../references/spec-artifact-workspace.zh-CN.md)，
旧兼容链接仅用于历史引用，不作为新产物根。

隐私阻碍 correctness 时，使用[仅用于证明的字段可见性 Skill](../../../references/verus-proof-only-field-visibility.zh-CN.md)。
只在隔离副本公开字段，保留执行正文并记录构建如何使用该副本。
内部证明可访问这些字段，正式 spec 与 completeness 则用原类型/view，不依赖临时字段。
这一可见性权限已获批准，但不允许发明不变量、以无对应的镜像替代目标或改其他可见性。

修改 implementation 前，在 `issues/` 中提出 issue，
包括源码证明副本的可执行重写或 verifier workaround。
探索性 patch 仅作为隔离提案保留，附原实现/提案差异和源码对应，
经过严格独立 review 和必要授权后才能采纳。
改写后的代码证明通过，不等于原始实现得到认证。
普通 ghost 注解或 lemma 不属于可执行代码改动。

发现不支持某种 Rust 语法或其他可复现的 Verus 限制时，
保留目标基线上的最小复现与诊断，提出 `verus-limitation` issue。
怀疑 std 实现/docstring 错误时，先排查 spec/view/proof 问题，再提交独立 review；
review 确认后才能标记为已确认缺陷。`UNKNOWN` 本身不是上游 bug 的证据。

遵守 Manager 确定的 issue 提交授权，外部提交成功后才记录真实 URL。
未发布草稿保持明确状态。关联失败 proof 和受影响 API，同根因去重。
未解决 API 保持未完成，不得为了变绿而悄悄改源码或文档。

## 产出四类交付物

按照模块图维护 `specs/<submodule>/`、必要的共享 view 和全模块可构建聚合入口，
不把无关 API 混在扁平候选文件中。
每个范围内 API 都在 `proofs/correctness/` 和 `proofs/completeness/`
下有可识别入口，采用共享规范的布局或明确映射的仓库等价布局。
包含 `issues/INDEX.md` 和发现的问题/提案；没有问题时也说明已 review 的范围。

用简明索引把 API 和源码/docstring 位置、spec/view、
两个 proof 路径、命令、结果和相关 issue ID 连接起来。
共享 proof helper 不替代逐 API 入口；被阻塞的 API 保留失败尝试和 issue 状态。
检查规格聚合入口，避免重复注册已有 vstd 声明。

## 交接

把实际合同差异和两轴当前证明结果交给 Reviewer。
客户端、原生测试与负控可以补充发现语义问题，但不能替代任一必要维度。
先检查受影响范围，复用未变化构建，保留准确诊断，
不要反复跑未改变的大套件，也不能从某个子模块通过推导全模块完成。

## 复制输入前检查存储

每次 discover/analyze/reexecute 和 witness 批次通过项目的 guarded checker
入口及 `storage-policy.json`；保持原 selector、verifier 参数、合法域和完整依赖。
检查真实 snapshot manifest，而不只看 `targets.include`；
排除全部旧输出、缓存和无关下载源码树，新输出与输入隔离。
超限明确记录并停止批次，不能换用裸 specdet 绕过。开工检查不等于验证通过。
保留唯一 spec/proof/query/review receipt；
经操作者授权并验证可恢复的重复输入才可被归档替代，原 manifest 不变。
这不授权改写 implementation。
