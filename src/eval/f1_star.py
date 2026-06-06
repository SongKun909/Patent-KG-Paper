"""F1* weighted metric — dynamic weighted evaluation for quintuples.

From the data paper:
- Core elements (name, value, relation): weight 0.7
- Auxiliary elements (object, condition): weight 0.15 each
- One-vote veto: core element mismatch = total score 0
- String similarity for partial matching
"""
import re
from dataclasses import dataclass
from typing import List


@dataclass
class F1StarResult:
    precision: float
    recall: float
    f1_star: float
    element_scores: dict
    completeness: float  # 五元组完备度


def _normalize_value(v: str) -> str:
    """Normalize numeric values for comparison."""
    v = v.strip().lower()
    v = re.sub(r"\s+", "", v)
    v = v.replace("mAh·g⁻¹", "mAh/g").replace("mAh.g", "mAh/g")
    v = v.replace("Wh·kg⁻¹", "Wh/kg").replace("Wh·kg", "Wh/kg")
    return v


def _element_similarity(pred: str, gold: str) -> float:
    """Compute similarity between predicted and gold element values."""
    if not pred or not gold:
        return 0.0
    pn = _normalize_value(pred)
    gn = _normalize_value(gold)
    if pn == gn:
        return 1.0
    if pn in gn or gn in pn:
        return 0.7
    pnums = re.findall(r"\d+\.?\d*", pn)
    gnums = re.findall(r"\d+\.?\d*", gn)
    if pnums and gnums and pnums == gnums:
        return 0.6
    return 0.0


def _match_quintuples(
    preds: List[dict], golds: List[dict]
) -> List[tuple]:
    """Greedy matching between predicted and gold quintuples."""
    matched = []
    used_pred = set()
    used_gold = set()

    for gi, gold in enumerate(golds):
        best_score = 0.0
        best_pi = -1
        for pi, pred in enumerate(preds):
            if pi in used_pred:
                continue
            name_sim = _element_similarity(
                pred.get("指标名称", ""), gold.get("指标名称", "")
            )
            val_sim = _element_similarity(
                pred.get("指标数值", ""), gold.get("指标数值", "")
            )
            core_score = (name_sim + val_sim) / 2
            if core_score > best_score:
                best_score = core_score
                best_pi = pi

        if best_pi >= 0 and best_score >= 0.3:
            matched.append((best_pi, gi, best_score))
            used_pred.add(best_pi)
            used_gold.add(gi)

    return matched


def compute_f1_star(
    pred_quintuples: List[dict],
    gold_quintuples: List[dict],
) -> F1StarResult:
    """Compute F1* for a single patent's extraction."""
    CORE_WEIGHT = 0.7
    AUX_WEIGHT = 0.15

    if not gold_quintuples:
        return F1StarResult(
            precision=0.0, recall=0.0, f1_star=0.0,
            element_scores={}, completeness=0.0,
        )

    matches = _match_quintuples(pred_quintuples, gold_quintuples)

    total_score = 0.0
    element_totals = {"name": 0.0, "value": 0.0, "relation": 0.0,
                      "object": 0.0, "condition": 0.0}
    n_matched = len(matches)

    for pi, gi, _ in matches:
        pred = pred_quintuples[pi]
        gold = gold_quintuples[gi]

        name_sim = _element_similarity(
            pred.get("指标名称", ""), gold.get("指标名称", ""))
        val_sim = _element_similarity(
            pred.get("指标数值", ""), gold.get("指标数值", ""))
        rel_sim = _element_similarity(
            pred.get("指标关系", ""), gold.get("指标关系", ""))

        core_ok = name_sim > 0.5 and val_sim > 0.5
        if not core_ok:
            continue

        core_score = CORE_WEIGHT * (name_sim + val_sim + rel_sim) / 3
        obj_score = AUX_WEIGHT * _element_similarity(
            pred.get("指标对象", ""), gold.get("指标对象", ""))
        cond_score = AUX_WEIGHT * _element_similarity(
            pred.get("实验条件", ""), gold.get("实验条件", ""))

        total_score += core_score + obj_score + cond_score
        element_totals["name"] += name_sim
        element_totals["value"] += val_sim
        element_totals["relation"] += rel_sim
        element_totals["object"] += _element_similarity(
            pred.get("指标对象", ""), gold.get("指标对象", ""))
        element_totals["condition"] += _element_similarity(
            pred.get("实验条件", ""), gold.get("实验条件", ""))

    n_gold = len(gold_quintuples)
    n_pred = len(pred_quintuples)

    recall_sum = total_score / n_gold if n_gold > 0 else 0.0
    precision_sum = total_score / n_pred if n_pred > 0 else 0.0
    f1 = (
        2 * precision_sum * recall_sum / (precision_sum + recall_sum)
        if (precision_sum + recall_sum) > 0
        else 0.0
    )

    elem_scores = {
        k: v / n_matched if n_matched > 0 else 0.0
        for k, v in element_totals.items()
    }

    def _is_complete(q):
        return all(q.get(k, "") for k in
                   ["指标名称","指标数值","指标关系","指标对象","实验条件"])

    completeness = (
        sum(1 for q in pred_quintuples if _is_complete(q))
        / len(pred_quintuples)
        if pred_quintuples
        else 0.0
    )

    return F1StarResult(
        precision=precision_sum,
        recall=recall_sum,
        f1_star=f1,
        element_scores=elem_scores,
        completeness=completeness,
    )
