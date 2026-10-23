# 回调 API 的生成与跳过策略

对应[英文 Skill](../verus-callback-api-triage.md)。

规则版本：**callback-triage-v1**，2026-10-16 获得操作者授权。
适用于依赖 `Fn`、`FnMut`、`FnOnce`、函数项、闭包、可变捕获、
回调参数写回或多次回调状态的 API。

回调 API 仍保留在 canonical inventory 中。当前 Verus/vstd 或任务本地 Verus
能够表达 sound 且有用的合同时，就生成规格；如果在有界、实质不同的尝试后，
回调支持仍不足，则保留部分结果，标记为 callback-support 的 local skip／延后，
继续其他独立 API。回调限制不能阻塞整个模块。

## 能生成时生成

复用已有 callable 协议，描述真实调用顺序、返回值、可变实参写回及有关回调状态。
保持原始回调类型和调用域。多次调用要区分每次当前 callable 状态，
不能把全部调用冻结在初始状态，也不能把 `mut_ref_current` 等同于任意未来值。

即使源码证明或 completeness 仍是部分结果，也可以保留有用的 API 候选，
但要分别报告这两条证明链。只有实际绑定且两条证明在声明范围内通过，
才能把回调 API 计为完成。

具体客户端、原生测试和局部 call-scope lemma 可用于检查语义，
但不证明任意回调行为，也不能替代原 API 的 correctness/completeness。

## 不能通过缩小回调域换取成功

除非原 Rust API 已有相同要求，否则不能增加：

- 回调纯度或恒等性；
- 返回值确定性；
- `Copy`、`Clone`、`View`、`'static`；
- 不捕获状态、无内部可变性或固定回调结果。

不能用纯 spec function 替代有状态回调，也不能把期望输出写入分析前提。
若 panic、短路和写回属于选定功能观察，就必须保留。

## 有界尝试与 local skip

先尝试已有 vstd callable 规则；存在实质不同且忠实于源码的 proof/encoding 路线时，
至少再尝试一种。可以用任务本地 Verus 修补范围明确的回调语言 feature，
但不要求为了一个 API 实现整套新的回调语义。

以下情况可以延后／跳过：

- 当前规则缺少可变捕获或函数项对应；
- 无法比较／枚举泛型可变回调 post-state；
- 复杂循环中需要传递多次 `FnMut` 当前／未来状态；
- 回调、元素和 Drop/panic 效果尚无不缩小调用域的有用状态接口。

记录准确 API、候选（若有）、尝试、诊断、缺失的 Verus 能力及重开条件。
使用 `partial_callback_spec` 或 `local_skip_callback_support` 等状态，
不能写成 `passed`。保留失败 query 和源码尝试。
跳过不等于完成，不能删除身份，也不能用 signature-only／普通长度合同替代。

Manager/Planner 登记延后后继续其他 ready API。
Reviewer 核对跳过有真实证据、候选没有过度声称，且没有忽略简单的已有机制。
最终报告将回调延后项与其他剩余工作分开统计。
