# Verus API 后置条件直接展开

对应[英文 Skill](../verus-inline-api-postconditions.md)。

Rust std 规格生成应把保证直接写进真实 API 的 `ensures`，
不要只写一个 spec 函数调用，把全部后置条件藏在里面。

避免：

```rust
ensures
    current::as_slice_post(drain, returned@),
```

直接写实际关系：

```rust
ensures
    returned@ == IteratorSpec::remaining(drain),
```

这不是按物理行数检查。单行 `result@ == input@` 可以是完整、明确的内容保证；
把 `whole_post(...)` 分成多行仍只是整份合同转发，不满足本规则。

## 展开保证，不重复定义基础抽象

可保留独立有意义的 view、序列运算、`eq_spec`、`IteratorSpec::remaining`
和已证明的共享 lemma。不要为了避免 spec 函数名而复制另一套模型。
应展开的是包装全部后置的谓词及其别名，直接展示返回、内容、写回和各分支保证。

原调用域和 API 身份不变。需要 TB-PARTIAL-EQ 时，全部展开条款仍在准确的
符合性蕴含之内；不移出 guard、不增加 `requires B`，也不把独立容器条件 C
并入外层 B。正式合同不得依赖仅为证明公开的字段，遵循
[字段可见性 Skill](verus-proof-only-field-visibility.zh-CN.md)。
指针和 ownership 属性不是本任务额外的 spec/completeness 要求。

## 必须接到真实 API

`spec fn next_contract(...) -> bool` 只是模型，不是 `Iterator::next` 的合同；
外部类型登记不是方法规格；返回 `Ghost<Seq<T>>` 的分析函数也不是 API 绑定。

必须给准确的 Rust API 提供有效规格，或者把具体类型和构造关系接入既有协议，
使其适用的继承方法合同真正可用。用未修改公共库上的真实调用展示联系，
不能只为客户端通过而假定缺失的 conformance 条件。
共享引理和投影确定性不能替代这种接入，也不能替代两条 API 证明链。

覆盖表分别记录辅助候选、实际 API 绑定、源码正确性、完整性范围和独立审阅。
缺少绑定时应写 **API 规格生成未完成**，不能写成“规格已生成、只差证明”。
可如实报告局部限制，但不能将它计为 API 规格，也不能用总入口或辅助证明通过掩盖。

展开已有 post 谓词后，源码证明和 completeness 合同须与真实 API 合同等价。
保留旧输入与结果，核对改变的绑定及受影响的客户端/证明；
不能声称旧快照字节与改后的输入相同，无关 API 无需重跑。
不能仅因辅助模型和限制报告已产出，就把整个剩余规格队列宣称完成。
