"""Prompt templates with syntactic augmentation."""
from typing import Optional

EXTRACT_SYSTEM_PROMPT = """你是一个深耕电化学与锂离子电池领域的专利情报提取专家。
你的任务是从高度专业、句式复杂的专利文本中，精准解构并抽取【技术指标语义五元组】。

请严格遵循以下本体约束与归一化准则进行抽取：

1. 【指标名称】: 提取物理属性或电化学性能名词，需剥离无关修饰词。
2. 【指标对象】: 提取指标所依附的材料或部件实体，映射至宏观顶层类别。
3. 【指标数值】: 提取准确的量值，必须严格保留对应的法定度量衡单位。
4. 【指标关系】: 提取数值与对象之间的逻辑关系（等于/大于/小于/范围为/约等）。
5. 【实验条件】: 提取指标测量或适用的实验参数环境（倍率、温度、压力等）。

输出格式为 JSON 数组: [{"指标名称":"...", "指标数值":"...", "指标关系":"...",
"指标对象":"...", "实验条件":"..."}]。如无技术指标则输出 []。"""


def _describe_syntax(syntactic_hints: dict) -> str:
    """Convert Stanza parse results to natural language syntactic hints."""
    if not syntactic_hints:
        return ""

    lines = ["\n## 句法结构分析（辅助参考）："]
    tokens = syntactic_hints.get("tokens", [])
    deps = syntactic_hints.get("dependencies", [])

    if tokens:
        lines.append(f"- 词序列: {' / '.join(tokens)}")

    for dep in deps:
        head = dep.get("head", "")
        rel = dep.get("relation", "")
        child = dep.get("child", "")
        lines.append(f"- 依存弧: [{rel}] {head} → {child}")

    return "\n".join(lines)


def build_extract_prompt(
    text: str,
    syntactic_hints: Optional[dict] = None,
) -> str:
    """Build the extract agent prompt with optional syntactic hints."""
    base = f"请从以下专利文本中抽取技术指标五元组：\n\n{text}"
    if syntactic_hints:
        base += _describe_syntax(syntactic_hints)
    return base


VERIFY_SYSTEM_PROMPT = """你是一个专利技术指标验证专家。请对以下抽取结果进行多维度校验：

1. **物理边界检查**: 指标数值是否在合理范围内？
2. **逻辑一致性**: 材料-性能对应关系是否成立？
3. **句法完整性**: 五元组各要素是否有缺失或错位？

对每个五元组给出 verdict (pass/fail), reason (简短理由)。
输出格式: [{"verdict":"pass/fail","reason":"...","index": 索引号}]"""


INTEGRATE_SYSTEM_PROMPT = """你是一个专利技术指标整合专家。请对多个抽取结果进行：

1. **术语归一化**: 同义异形映射到标准术语
2. **冲突消解**: 句法一致性 > LLM置信度
3. **去重合并**: 相同指标合并为一条

输出最终的五元组列表。"""
