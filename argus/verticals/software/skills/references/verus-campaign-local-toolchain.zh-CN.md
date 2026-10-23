# 每个任务独立维护 Verus 工具链

对应[英文 Skill](../verus-campaign-local-toolchain.md)，同时遵循
[共享规格流程](verus-spec-generation-and-repair.zh-CN.md)及
[统一产物目录](spec-artifact-workspace.zh-CN.md)。

规则版本：**campaign-local-verus-v1**，2026-10-16 获得操作者授权。

每个 Argus 规格任务都可以维护、修改并编译自己的 Verus 源码和与之匹配的
vstd，用于解决固定验证器明确不支持的 Rust language feature，
或验证器翻译／建模缺口。对有界的本地 patch，不需要逐项再次等待操作者授权。
但这不授权修改共享官方工具链、静默改变证明基线、削弱验证义务或直接对外发布。

## 目录与基线身份

共享产物根中的官方基线保持只读。本地可修改工具链放在任务工作目录内，例如：

```text
<campaign>/toolchains/local-verus/
    source/
    patches/
    build/
    manifest.json
```

从任务固定的官方 commit 派生，并记录：

- 上游仓库、commit 和原始源码树 digest；
- 每份本地 patch/diff、用途、影响的验证阶段和 review；
- Rust toolchain、solver、构建命令及匹配的 vstd 源码／构建；
- Verus、vstd、二进制 hash 和回归命令；
- 哪些 API／proof 使用官方工具链，哪些使用本地工具链。

不能把修改后的 Verus 与无关的预编译 vstd 混用；Verus 和 vstd 要一起匹配构建。
本地源码、target 和编译日志不得进入 specdet 输入快照。

## 何时允许修改本地 Verus

先在只读官方基线上用最小复现确认真实限制和诊断，并排除：

- API 合同或源码翻译错误；
- 已有规格未接入；
- proof/checker 编码不正确；
- 资源限制；
- 普通 Rust 版本不匹配。

本地 patch 应处理范围明确的问题，例如 parser/lowering 支持、
方法或函数项对应、真实 Rust 构造的安全翻译，或源码证明需要的其他有界能力。
不能为了回避 language support 去改写 Rust/std 的执行语义。

采用尽可能小的语义改动，禁止：

- 把失败义务改成假设或删除义务；
- 新增带答案的公理、`admit`、大范围 `external_body` 或目标专用捷径；
- 削弱 soundness、跳过方法体、屏蔽诊断或静默缩小原 API 调用域；
- 修改共享官方 Verus/vstd。

patch 必须同时有正例和负例／回归控制，避免规则过宽。
先构建并验证匹配的 vstd，再运行最小复现及受影响的项目检查。
仅构建成功不证明 soundness 或源码对应。

## 结果标注

本地验证器得到的结果必须引用其 manifest 和二进制 digest，并明确标注为：

```text
verified with campaign-local Verus
```

不能写成官方基线通过。历史官方结果保持不变。

当同一份经审阅的本地工具链下，两条证明链均通过，且 API 合同和源码对应
已独立接受时，任务可以在自己的范围内接受该 API。最终报告必须分别列出：

- 官方基线结果；
- 本地工具链结果及准确 patch 依赖；
- 尚待上游移植或独立审阅的义务。

不能把本地结果直接提升为共享 vstd 或上游结论。
未来官方版本替代本地 patch 前，要核对准确合同和行为兼容性。

## 独立审阅与失败处理

计入本地工具链结果前，Reviewer 核对 patch、原诊断、生成义务／query、
回归控制、匹配 vstd 构建及工具链 manifest。
本规则只授权任务本地目录中的 Verus 修改；更广泛的工具修改仍需单独授权。

如果 patch 范围扩大、可信基础影响不清楚、回归失败，或需要大量新的语言／回调语义，
保留本地问题记录，并按相关 API family 的规则重新规划或跳过。
不能让本地 Verus 开发无限阻塞其他独立 API。
