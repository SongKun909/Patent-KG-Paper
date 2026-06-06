#!/usr/bin/env python
"""Run all experiments and produce results table + plots."""
import json
import os
import sys
import time
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import PipelineConfig, load_config
from data.loader import load_dataset, split_by_patent
from pipeline import ExtractionPipeline
from models.quintuple import Quintuple
from eval.f1_star import compute_f1_star, F1StarResult
from baselines.rule_baseline import RuleBaseline


class ExperimentRunner:
    """Runs experiments and collects results."""

    def __init__(self, config_path: str = None):
        self.config = load_config(config_path)
        self.pipeline = ExtractionPipeline(self.config)
        self.rule_baseline = RuleBaseline()
        self.results = {}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def load_test_data(self):
        """Load and split the dataset."""
        print("Loading dataset...")
        ds = load_dataset(self.config.dataset_path)
        print(f"  Loaded {ds.lang_stats['total']} records from {len(ds.patent_ids)} patents")
        print(f"  Language distribution: {ds.lang_stats}")

        split = split_by_patent(
            ds.records,
            train_ratio=0.70,
            val_ratio=0.15,
            test_ratio=0.15,
            seed=self.config.seed,
        )
        print(f"  Split: train={len(split.train)}, val={len(split.val)}, test={len(split.test)}")
        return split

    def run_single_llm(
        self, test_records: List[dict], shots: int = 0
    ) -> Dict:
        """Run single LLM baseline (no multi-agent, no syntax)."""
        print(f"\n{'='*60}")
        print(f"Running Single LLM ({shots}-Shot)...")
        print(f"{'='*60}")

        all_preds = []
        all_golds = []
        n_records = len(test_records)

        for i, record in enumerate(test_records):
            text = record["input"]
            gold_output = record["output"]
            lang = record.get("lang", "zh")

            # Parse gold
            try:
                gold = json.loads(gold_output) if isinstance(gold_output, str) else gold_output
                if isinstance(gold, dict):
                    gold = [gold]
            except (json.JSONDecodeError, TypeError):
                continue

            # Single LLM extraction (skip filter + syntax + agents)
            try:
                # Build few-shot prompt if needed
                if shots > 0:
                    examples = self._get_few_shot_examples(shots, lang)
                    text_with_examples = examples + "\n\n" + text
                else:
                    text_with_examples = text

                from prompts.templates import EXTRACT_SYSTEM_PROMPT, build_extract_prompt
                prompt = build_extract_prompt(text_with_examples, None)
                raw = self.pipeline.llm.generate(EXTRACT_SYSTEM_PROMPT, prompt)
                pred_quints = self.pipeline.llm._parse_response(raw, text)
            except Exception as e:
                print(f"  [{i+1}/{n_records}] LLM error: {e}")
                continue

            pred_dicts = [q.to_dict() for q in pred_quints]
            result = compute_f1_star(pred_dicts, gold)
            all_preds.append(pred_dicts)
            all_golds.append(gold)

            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{n_records}] Running F1*: {result.f1_star:.4f}")

        # Aggregate results
        agg = self._aggregate_results(all_preds, all_golds)
        print(f"\n  Final F1*: {agg['f1_star']:.4f}")
        print(f"  Precision: {agg['precision']:.4f}, Recall: {agg['recall']:.4f}")
        return agg

    def run_full_pipeline(
        self,
        test_records: List[dict],
        syntax_enabled: bool = True,
        verify_enabled: bool = True,
    ) -> Dict:
        """Run the full multi-agent pipeline."""
        mode_desc = []
        if syntax_enabled:
            mode_desc.append("+Syntax")
        if verify_enabled:
            mode_desc.append("+Verify")
        mode_str = "+".join(mode_desc) if mode_desc else "ExtractOnly"

        print(f"\n{'='*60}")
        print(f"Running Full Pipeline ({mode_str})...")
        print(f"{'='*60}")

        all_preds = []
        all_golds = []
        n_records = len(test_records)

        for i, record in enumerate(test_records):
            text = record["input"]
            gold_output = record["output"]
            lang = record.get("lang", "zh")
            patent_id = record.get("patent_id", f"PAT-{i}")

            # Parse gold
            try:
                gold = json.loads(gold_output) if isinstance(gold_output, str) else gold_output
                if isinstance(gold, dict):
                    gold = [gold]
            except (json.JSONDecodeError, TypeError):
                continue

            try:
                if not syntax_enabled and not verify_enabled:
                    # Pure extract mode: skip filter + syntax + agents
                    from prompts.templates import EXTRACT_SYSTEM_PROMPT, build_extract_prompt
                    prompt = build_extract_prompt(text, None)
                    raw = self.pipeline.llm.generate(EXTRACT_SYSTEM_PROMPT, prompt)
                    pred_quints = self.pipeline.llm._parse_response(raw, text)
                else:
                    # Run through the pipeline
                    pred_quints = self.pipeline.run(text, lang, patent_id)
            except Exception as e:
                print(f"  [{i+1}/{n_records}] Error: {e}")
                continue

            pred_dicts = [q.to_dict() for q in pred_quints]
            result = compute_f1_star(pred_dicts, gold)
            all_preds.append(pred_dicts)
            all_golds.append(gold)

            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{n_records}] Running F1*: {result.f1_star:.4f}")

        agg = self._aggregate_results(all_preds, all_golds)
        print(f"\n  Final F1*: {agg['f1_star']:.4f}")
        print(f"  Precision: {agg['precision']:.4f}, Recall: {agg['recall']:.4f}")
        print(f"  Element scores: {agg.get('element_scores', {})}")
        return agg

    def run_rule_baseline(self, test_records: List[dict]) -> Dict:
        """Run rule-based baseline extraction."""
        print(f"\n{'='*60}")
        print("Running Rule-Based Baseline...")
        print(f"{'='*60}")

        all_preds = []
        all_golds = []

        for i, record in enumerate(test_records):
            text = record["input"]
            gold_output = record["output"]

            try:
                gold = json.loads(gold_output) if isinstance(gold_output, str) else gold_output
                if isinstance(gold, dict):
                    gold = [gold]
            except (json.JSONDecodeError, TypeError):
                continue

            preds = self.rule_baseline.extract(text)
            result = compute_f1_star(preds, gold)
            all_preds.append(preds)
            all_golds.append(gold)

            if (i + 1) % 20 == 0:
                print(f"  [{i+1}/{len(test_records)}] F1*: {result.f1_star:.4f}")

        agg = self._aggregate_results(all_preds, all_golds)
        print(f"\n  Final F1*: {agg['f1_star']:.4f}")
        return agg

    def _get_few_shot_examples(self, n: int, lang: str = "zh") -> str:
        """Get few-shot examples for in-context learning."""
        zh_examples = [
            """输入: "电池的能量密度达到300Wh/kg，循环寿命超过2000次。"
输出: [{"指标名称":"能量密度","指标数值":"300Wh/kg","指标关系":"等于","指标对象":"电池","实验条件":"无"}]""",
            """输入: "在0.5C倍率下，正极材料的首次放电比容量为150mAh/g。"
输出: [{"指标名称":"首次放电比容量","指标数值":"150mAh/g","指标关系":"等于","指标对象":"正极","实验条件":"0.5C"}]""",
            """输入: "烧结温度控制在700~800℃，保温时间为4小时。"
输出: [{"指标名称":"烧结温度","指标数值":"700~800℃","指标关系":"范围为","指标对象":"材料","实验条件":"保温4小时"}]""",
        ]
        en_examples = [
            """Input: "The energy density reached 300 Wh/kg at 0.5C rate."
Output: [{"指标名称":"energy density","指标数值":"300 Wh/kg","指标关系":"等于","指标对象":"battery","实验条件":"0.5C"}]""",
            """Input: "The cathode had a specific capacity of 170 mAh/g."
Output: [{"指标名称":"specific capacity","指标数值":"170 mAh/g","指标关系":"等于","指标对象":"cathode","实验条件":"无"}]""",
        ]
        examples = zh_examples if lang.startswith("zh") else en_examples
        return "\n\n".join(examples[:n])

    def _aggregate_results(
        self, all_preds: List, all_golds: List
    ) -> Dict:
        """Aggregate F1* results across all test records."""
        if not all_preds:
            return {"f1_star": 0.0, "precision": 0.0, "recall": 0.0}

        total_result = compute_f1_star(
            [p for preds in all_preds for p in preds],
            [g for golds in all_golds for g in golds],
        )
        return {
            "f1_star": total_result.f1_star,
            "precision": total_result.precision,
            "recall": total_result.recall,
            "completeness": total_result.completeness,
            "element_scores": total_result.element_scores,
            "n_records": len(all_preds),
        }

    def save_results(self, results: Dict, exp_name: str):
        """Save experiment results to JSON."""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{exp_name}_{self.timestamp}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\nResults saved to {output_path}")

    def print_summary_table(self, all_results: Dict):
        """Print a summary table of all experiments."""
        print(f"\n{'='*80}")
        print("EXPERIMENT RESULTS SUMMARY")
        print(f"{'='*80}")
        print(f"{'Group':<40} {'F1*':>8} {'Precision':>10} {'Recall':>10}")
        print(f"{'-'*68}")

        for exp_name, result in all_results.items():
            print(
                f"{exp_name:<40} "
                f"{result.get('f1_star', 0):>8.4f} "
                f"{result.get('precision', 0):>10.4f} "
                f"{result.get('recall', 0):>10.4f}"
            )
        print(f"{'='*80}")


def main():
    """Run experiments based on config files."""
    import argparse

    parser = argparse.ArgumentParser(description="Run extraction experiments")
    parser.add_argument(
        "--exp",
        type=str,
        default="all",
        choices=["all", "exp1", "exp2", "exp3", "quick"],
        help="Which experiment to run",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit test records (0 = all)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to custom config YAML",
    )
    args = parser.parse_args()

    runner = ExperimentRunner(args.config)
    split = runner.load_test_data()

    test_records = split.test[:args.limit] if args.limit > 0 else split.test
    print(f"Using {len(test_records)} test records")

    all_results = {}

    # Quick smoke test
    if args.exp in ("all", "quick"):
        print("\n>>> Running quick smoke test on first 3 records...")
        smoke = runner.run_full_pipeline(test_records[:3])
        all_results["quick_smoke"] = smoke

    # Experiment 1: LLM comparison
    if args.exp in ("all", "exp1"):
        # Only run on a limited subset unless explicitly full run
        n = min(len(test_records), 5) if args.limit == 0 else len(test_records)
        exp1_records = test_records[:n]

        # 1a: Zero-shot
        result_1a = runner.run_single_llm(exp1_records, shots=0)
        all_results["1a_zero_shot"] = result_1a

        # 1b: 3-Shot
        result_1b = runner.run_single_llm(exp1_records, shots=3)
        all_results["1b_3_shot"] = result_1b

        # 1d: Full pipeline
        result_1d = runner.run_full_pipeline(exp1_records)
        all_results["1d_ours"] = result_1d

    # Experiment 2: Traditional baselines
    if args.exp in ("all", "exp2"):
        n = min(len(test_records), 10) if args.limit == 0 else len(test_records)
        exp2_records = test_records[:n]

        result_2a = runner.run_rule_baseline(exp2_records)
        all_results["2a_rule"] = result_2a

        result_2c = runner.run_full_pipeline(exp2_records)
        all_results["2c_ours"] = result_2c

    # Run ablation study
    if args.exp in ("all", "exp3"):
        n = min(len(test_records), 5) if args.limit == 0 else len(test_records)
        exp3_records = test_records[:n]

        # 3a: Full
        r_full = runner.run_full_pipeline(exp3_records, syntax_enabled=True, verify_enabled=True)
        all_results["3a_full"] = r_full

        # 3b: No verify
        r_no_v = runner.run_full_pipeline(exp3_records, syntax_enabled=True, verify_enabled=False)
        all_results["3b_no_verify"] = r_no_v

        # 3c: No syntax
        r_no_s = runner.run_full_pipeline(exp3_records, syntax_enabled=False, verify_enabled=True)
        all_results["3c_no_syntax"] = r_no_s

        # 3d: No both
        r_no_both = runner.run_full_pipeline(exp3_records, syntax_enabled=False, verify_enabled=False)
        all_results["3d_no_both"] = r_no_both

    # Print summary and save
    runner.print_summary_table(all_results)
    runner.save_results(all_results, args.exp)

    print("\nDone!")


if __name__ == "__main__":
    main()
