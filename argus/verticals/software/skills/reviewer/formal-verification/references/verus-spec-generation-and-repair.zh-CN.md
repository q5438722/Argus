# Reviewer：Verus 正确性与完备性验收（中文审阅稿）

对应[英文角色 Skill](../verus-spec-generation-and-repair.md)。
先读[共享规范](../../../references/verus-spec-generation-and-repair.zh-CN.md)。
使用自己的 OWN Skill，不能只参考 Engineer 的方法或自报结果。

## 检查真实范围与语义

核对子模块/API 清单、依赖顺序、view 定义及源码对应。
确认所需 view 先于依赖它的 spec；其他 API 顺序必须有真实依据。
不能把缺失 constructor 关系或任意 observer 当作完整 family。

每条被修改的合同都与实现和 docstring 对照。
检查签名、合法输入、返回分支、内容、修改 frame、已消费的 iterator 状态及有关回调。
检查共享依赖和代表性的 API 组合，不只看孤立声明。

## 通过实际 consumer 检查接入

采用[抽象接入参考](../../../references/spec-abstraction-integration.zh-CN.md)，
独立检查既有规格接口和实际加载合同中的 constructor -> consumer -> observer 链。
检查返回 item 的内容/顺序、适用的耗尽和可变借用写回，
以及启用条件或辅助状态桥接。
拒绝用元数据-only 客户端、仅构造时成立的等式证明后续状态行为。
按有依据的语义连接判断 helper，不只按是否使用 uninterpreted 语法；
任务明确提出的额外限制仍要执行。
客户端验证支持接入审查，但本身不认证任一必要证明维度。

## 独立检查两个证明维度

Correctness：用目标 Verus 基线重放受影响的源代码实现证明。
确认实际检查了当前候选对应的函数体/义务，源码转换的对应义务也已完成。
拒绝循环使用目标假设、跳过函数体、synthetic 占位实现、新增可信答案和零义务运行。
类型检查、原生测试或客户端证明不能替代这一轴。

Completeness：对当前合同运行真实 `spec-determin-tool` 路径，
检查生成的 proof/query、输出比较关系、前提和结果。
拒绝通过削弱比较、输入携带答案、错误前置条件、`UNKNOWN` 或替代工具取得的“成功”。
检查有关合法正例。确定的错误答案仍然错误；仅实现证明也不说明完备。

重放被修改 API 及受影响依赖。
只有确认候选、证明输入和基线仍对应，才能复用未改变的证据。
任何一轴都不能仅从 Engineer 的文字报告推出通过。

## 在声明的信任边界内 review

阅读 [TB-PARTIAL-EQ](../../../references/trust-boundaries/partial-eq.zh-CN.md)
的 **conditional-posts-v2** 及 `trust_boundaries/TB-PARTIAL-EQ.md`。
核对**如果有需要**的理由，以及每个选定函数的全部后置均位于
`T::obeys_eq_spec() ==>` 右侧。拒绝遗留的 API `requires B`、统一 B 假设、
只保护部分后置或给无关 API 新加界限；原前置保持。
检查原域源码正确性及准确的条件完整性/reexecute 结论；
!B 调用仍合法，但不承诺确定结果。B 为假时的空真不能代替 B 为真时的保证证明。
迁移证据确认后才能称旧前提式结果符合新版本；源码/内容桥接、状态效果和真实模型
仍是义务，额外信任仍需单独批准。

## 严格 review implementation 改动和 issues

对[任务本地 Verus](../../../references/verus-campaign-local-toolchain.zh-CN.md)
结果，核对准确的 Verus/vstd patch、原最小复现、生成义务、正负回归、
构建 manifest 和二进制 digest。拒绝把它改写成官方基线结果，
也拒绝通过假定或删除失败义务取得成功。

对[回调 triage](../../../references/verus-callback-api-triage.zh-CN.md)，
核对跳过建立在真实有界尝试上、保持原回调域，并明确仍是不完整结果。
接受 local skip 只允许模块继续，不等于接受该 API 的 correctness/completeness。
核对[API 后置直接展开](../../../references/verus-inline-api-postconditions.zh-CN.md)：
仅把整份合同转发给一个谓词的 `ensures` 不是要求的交付物，
辅助/投影证明也不证明真实 API 绑定。
检查[产物根及搬迁边界](../../../references/spec-artifact-workspace.zh-CN.md)，
不改写历史证据，也不扩大读取权限。

对这一已授权适配，执行[proof-only 字段可见性检查](../../../references/verus-proof-only-field-visibility.zh-CN.md)：
源码差异只改变字段修饰符，verifier 确实使用指定副本，类型/view 对应及原可达状态
依据成立。拒绝正式 spec 或 completeness 对临时字段的依赖，两者仍须使用未改库。
public 镜像可编译不是源码证明，也不批准其他执行或可见性改动。

任何 implementation 改动都要先有 issue 提案，包括源码证明副本的可执行重写。
独立对照原实现/提案差异，检查源码与 docstrings、可观察行为及安全影响、
源码到 proof 的对应，以及受影响的证明。
不能因为另一份实现容易证明，就批准替换原实现。
在 issue 中记录 review 决定；修改原始 std 或 Verus 仍需要用户明确授权。

在目标基线上复现报告的 Verus 限制，包括不支持的 Rust 语法。
确认 std 实现/docstring 缺陷前，先排除 spec/view/proof 或检查编码错误，
指出真实的源码/docstring 错误。证明失败或 `UNKNOWN` 不足以支持该结论。
未确认的诊断保持 `needs-review`。

核对必要问题和修改提案已进入 `issues/`，关联受影响 API/proof，
且 review 与提交状态真实。本地草稿不是上游 issue URL。
Issue 经过 review，不等于任何证明轴通过，也不等于 API 已修复。

## 交付与裁定

对齐按子模块组织的 specs、逐 API 的 Verus correctness proof 目录、
独立的 completeness proof 目录，以及包含索引的 `issues/`。
每个范围内 API 对应其 spec、两类 proof、两个明确结果/重放命令及相关 issues。
没有发现问题时明确已 review 的范围，不能编造报告。
只有状态标签、缺失 proof 文件，或重复计算 helper，都不等于 API 证明覆盖。

同一候选两轴都通过才接受 API；模块完成还要求全覆盖与可用的聚合入口。
规划/view 子任务可以完成较窄目标，但不能据此认证依赖 API。
未通过时指出最小失败义务与下一步 repair，或具体 blocker/replan 理由；不得降低标准。
Verifier 修改仍需作为工具任务另行批准。

## 独立执行相同的存储检查

读取 `storage-policy.json`，在既有只读 project/input 与可写 scratch 边界内
使用 guarded checker；重放前检查真实快照大小、依赖闭包和空闲空间。
不能使用裸 checker 绕过，也不能扩挂载权限。
归档后仍检查 comparison、implementation 对应与原 review receipt。
已归档而缺失的输入必须在获准根内验证恢复，不能假定旧运行已经重放。
开工检查或归档成功不替代任一 proof 维度；清理不得抹去失败或改变接受计数。
