# Planner：Verus 子模块与证明规划（中文审阅稿）

对应[英文角色 Skill](../verus-spec-generation-and-repair.md)。
安排 API 生成前，先读[共享规范](../../../references/verus-spec-generation-and-repair.zh-CN.md)和 Manager 的范围。

## 首先建立模块图

检查实际子模块、类型/impl 所属位置、重导出、委托调用和跨模块依赖。
为 API 分配 canonical identity，不能把重导出或注释镜像重复计为 API。
记录已有 vstd 覆盖与有明确依据的排除项，不得静默缩小范围。

每个子模块要说明源码、docstrings、既有或所需 view、支撑 lemma、API 和依赖。
可以复用项目 inventory，不要求新增一套规划文件协议。

## 工作顺序

1. 先安排共享 view 定义，并明确源码对应义务。
   每个子模块要么指出复用的 view 及其充分性，要么先建立 view 定义任务，
   再安排依赖它的 API spec。
   依赖 constructor 的对应证明与该 API 一起完成，不制造循环前置门槛；
   验收前必须闭合证明。
2. 按实现与证明依赖 bottom-up；采用其他顺序时说明理由。
   相互依赖的 API family 一起处理并明确共同义务。
   依赖 constructor 关系的 observer 不能被孤立验收。
3. 每个 API 任务携带源码和 docstring 位置、选定 view、准确公开签名、
   前置依赖合同和输出路径；不能只给 API 名字或想要的后置条件。
4. 确认真实 Verus 与 `spec-determin-tool` 入口。
   每个 API 规划两类独立证明：源码到合同的 correctness，以及同一合同的工具生成 completeness。
   两类检查进入每个 API 的 repair 循环，不能推迟到全模块写完之后。
5. 将每个子模块映射到 `specs/<submodule>/` 文件及全模块聚合入口，
   同时规划两个证明目录和 `issues/`。
   每个范围内 API 在两条证明链都有独立可识别的入口；
   已有合同若也属于本次验证范围，同样需要这些入口，并关联适用的 issue。
6. Implementation-change 提案必须先成为 issue，经过严格独立 review，
   才能采纳 implementation 修改任务。
   为疑似 Verus 限制安排最小复现，为疑似 std 实现/docstring 缺陷安排 review。
   不能从一个未决证明直接假定上游存在 bug。

## 扩展 family 前先规划协议连接

字段隐私阻碍源码证明时，先考虑已授权的[proof-only 可见性路线](../../../references/verus-proof-only-field-visibility.zh-CN.md)，
不要直接把隐私判为不可避免。适配 correctness 构建与原库下的 spec/completeness 分开；
规划精确字段 diff、类型/view 对应及独立审阅。
opaque 类型支持或 callee 合同缺失仍是不同的义务。

采用[抽象接入参考](../../../references/spec-abstraction-integration.zh-CN.md)。
规划平行 view 前，检查既有 trait 规格、真实 item/返回类型、consumer 合同及启用条件。
在现有依赖图中包含 constructor -> consumer -> observer，
以及适用的耗尽或可变借用写回义务。
将同一模型推广到更多 API 前，先安排一个代表性客户端组合。
区分 constructor-only 桥接与消费后需要的关系，明确不能支持的义务。
客户端是补充工作，不是可替代必要证明的第三条证明链。

## 规划中携带信任边界

使用 [TB-PARTIAL-EQ](../../../references/trust-boundaries/partial-eq.zh-CN.md)
的 **conditional-posts-v2** 及 `trust_boundaries/TB-PARTIAL-EQ.md`。
逐函数判断**如果有需要**，再将全部后置放在准确配对的
`T::obeys_eq_spec() ==>` 右侧；不把 guard 传成额外 API `requires`，
不给无关工作增加比较界限。规划原调用域内的正确性与明确的条件唯一性，
包括 B 为真的正例及仍合法的 !B 情况。
为旧前提式合同安排有界迁移，只复用候选及结论仍匹配的证据。
!B 时无条件唯一性不成立不反驳条件完整性；真实源码/内容桥接及模型定义仍是义务。

## 反馈与重规划

按[任务本地 Verus 规则](../../../references/verus-campaign-local-toolchain.zh-CN.md)
规划范围明确的验证器 feature 工作，并单独安排 patch、测试和 review 依赖；
不能让它串行阻塞无关 API。按[回调 triage](../../../references/verus-callback-api-triage.zh-CN.md)
安排有界且实质不同的尝试；若需要大规模新回调语义，则登记 callback-support
local skip 后继续其他工作。

按[直接 API 后置规则](../../../references/verus-inline-api-postconditions.zh-CN.md)
规划实际绑定/协议接入和展开后的保证，不用仅辅助函数里程碑替代 API。
全部交付物使用指定的[统一产物目录](../../../references/spec-artifact-workspace.zh-CN.md)；
保留搬迁检查点，不重新把旧绝对路径当作新产物根。

用实际 correctness 失败义务、completeness 反例或未决 query 决定下一项有界修复。
View/helper 改变会重新打开全部依赖它的 API 检查。
保持原语义及检查输入，不能换成会通过的替代目标，也不能让合法输入消失。

阻塞项、已尝试的 proof 产物和 issue 引用保持可见。
共享同一限制的 API 关联同一根因 issue。
对具体源码/工具限制调整计划，不要反复执行未改变的命令；
可以继续独立子模块，但不得绕过 issue/review 要求。
调查、仅 view 的结果或单轴通过，都不等于 API 完成。
最后安排覆盖核对，以及 Reviewer 对模块两条证明链的独立验收。

## 规划有界输入快照

交接明确 `storage-policy.json` 和带存储检查的 checker 命令。
列出完整 source/spec 依赖闭包与快照排除项；
`targets.include` 本身不能限制复制量。历史输出、下载源码树和无关实验副本
不得进入输入根。预算考虑 proof attempt 与 witness candidate 的复制倍增，
派工前检查存储条件。可复用 hash 匹配的未变证据，不重复跑无变化的大批次。
超限是明确 blocker，不是删除 implementation 桥接、弱化 comparison
或移除唯一 proof/review 证据的许可。
