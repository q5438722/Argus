# Manager：Verus 任务范围与交付（中文审阅稿）

对应[英文角色 Skill](../verus-spec-generation-and-repair.md)。
处理 Verus 模块规格任务时，先读[共享规范](../../../references/verus-spec-generation-and-repair.zh-CN.md)。
前门/SELF 做范围确认时也使用本角色要求；不要求额外开启通用 Manager grounding。

## 范围与交接

将[任务本地 Verus 授权](../../../references/verus-campaign-local-toolchain.zh-CN.md)
和[回调 API 策略](../../../references/verus-callback-api-triage.zh-CN.md)带入任务。
官方基线保持只读；需要补语言 feature 时使用独立可修改工具链。
回调支持不足的跳过项保留在清单中，但不阻塞其他 ready API。

要求[直接展开且实际绑定的 API 后置](../../../references/verus-inline-api-postconditions.zh-CN.md)，
并指定[统一产物根](../../../references/spec-artifact-workspace.zh-CN.md)。
不能把辅助函数交付当作剩余 API 规格队列完成。
获准搬迁时使用受支持的生命周期/workdir 接口，保留历史证据和原任务身份。

1. 确认目标模块、Rust 源码与 docstrings、已有 vstd 合同、输出位置和固定 Verus 基线。
   保留用户要求的 API 范围；有歧义就说明，不能悄悄排除困难 API 或修改签名。
2. 要求先分析子模块与依赖，再生成 API spec。
   详细结构分析交给 Planner，不重复其完整探索。
   每个子模块都要说明复用哪个 view，或在写 API spec 前新增什么 view。
3. 要求 bottom-up 的依赖顺序，或有明确理由的其他顺序。
   View 及其对应义务必须先于依赖它的合同；
   整个修复过程始终同时依据源代码和 docstrings。
4. 明确两个验收维度：源代码实现的 correctness 由 Verus 验证，
   completeness 由 `spec-determin-tool` 检查。
   让 Planner 确认项目真实命令；不能以客户端证明、类型检查、源码审阅或其他工具替代。
5. 将四类产物写入交接：按子模块组织的 specs、逐 API correctness proof 目录、
   独立的 completeness proof 目录，以及包含问题/提案索引和状态的 `issues/`。
   要求简明索引，将每个 API、产物、两轴结果和相关 issue 连接起来。
6. 明确 issue 报告的存放位置及外部提交授权。
   任何 implementation 改动先提出 issue，再经严格独立 review；
   review 本身不授权修改原始 Rust/std 或 Verus。
   获得明确批准前保留目标源码。

## 要求可用的库接入

私有字段阻碍源码证明时，将[仅用于证明的字段可见性授权](../../../references/verus-proof-only-field-visibility.zh-CN.md)
带入任务。只允许适配隔离的 correctness 副本，不修改真实 std/vstd 或扩展公开接口。
要求对应性审阅及原库下的 spec/completeness；不只为字段可见性再次等待批准，
也不自动改写旧失败的分类。

依据[抽象接入参考](../../../references/spec-abstraction-integration.zh-CN.md)，
要求复用足够的既有规格协议；不足时提供有依据的桥接。
对范围内有状态 family，交付要求包含 constructor/consumer 互通与代表性仓库客户端。
不预设必须新增 view 或指定具体表示，详细分析交给 Planner。
孤立模型输出唯一，不证明调用者能通过已有库合同使用 API。
接入客户端只补充检查，不能替代任一证明维度。

## 声明验证的信任边界

采用 [TB-PARTIAL-EQ](../../../references/trust-boundaries/partial-eq.zh-CN.md)
的 **conditional-posts-v2** 更正。**如果有需要**，要求该函数全部后置位于
`T::obeys_eq_spec() ==>` 右侧，不统一假定标志成立，也不增加 API `requires`。
无关函数与原 Rust 调用域不变。专门的 `trust_boundaries/TB-PARTIAL-EQ.md`
记录理由、准确配对、完整受保护保证及条件分析范围。
通过正常规划修正冲突的项目指导，旧前提式证据保留为历史，
安排迁移检查而非把旧成功静默改名。区分条件完整性与无条件确定性；
本次更正不授权其他 trust boundary。

## 完成与升级

未通过的 API 带着明确失败或 blocker 继续 repair。
不能仅凭生成数量、某个子任务 `done` 或单轴通过就宣称模块完成。
独立 Reviewer 必须核对全部范围、两条证明链及 issues。

已经复现的 Verus 限制（包括不支持 Rust 语法），
以及经独立 review 确认的 std 实现/docstring 错误，必须提出 issue。
证明失败本身不等于这些诊断成立。
未确认问题标记为需要 review，区分本地草稿和已发布的外部 issue；
缺少提交权限时进行处理，不能声称已经发布。

规划/view 子任务完成，与 API 已通过验收分开。
工具限制不授权修改 verifier 或 lifecycle 引擎；确有需要时应另行取得批准。
版本、路径、范围决策和进度保留在项目里。

## 存储开工条件与保留规则

派工前设置 `storage-policy.json`、有界输入根和带存储检查的 checker 入口。
Engineer 与 Reviewer 都检查真实输出文件系统的空闲空间与输入大小；
超限不得派工，用户暂停后不能因清理释放空间就自动恢复。
存储阻塞期间保留完整 API 目标。明确批准归档范围，保留唯一
spec/proof/query/review 证据以及重复输入的已验证恢复路径。
清理不改变接受数量，也不授权修改 checker 或源码 implementation。
