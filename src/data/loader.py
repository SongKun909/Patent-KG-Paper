"""Load and split the Lithium-Battery-IE-Dataset from HuggingFace."""
import random
from dataclasses import dataclass, field
from typing import Optional

from datasets import load_dataset as hf_load_dataset


@dataclass
class PatentAwareSplit:
    train: list = field(default_factory=list)
    val: list = field(default_factory=list)
    test: list = field(default_factory=list)


@dataclass
class PatentDataset:
    records: list
    patent_ids: list
    lang_stats: dict


def load_dataset(
    dataset_path: str = "SongKun909/Lithium-Battery-IE-Dataset",
    streaming: bool = False,
) -> PatentDataset:
    """Load dataset, annotate each record with patent_id derived from input."""
    ds = hf_load_dataset(dataset_path, split="train", streaming=streaming)
    records = list(ds)

    # Derive patent_id from input text hash
    patent_id_map = {}
    patent_counter = 0
    for r in records:
        text_prefix = r["input"][:50]
        if text_prefix not in patent_id_map:
            patent_id_map[text_prefix] = f"PAT-{patent_counter:04d}"
            patent_counter += 1
        r["patent_id"] = patent_id_map[text_prefix]
        # Detect language
        r["lang"] = (
            "en"
            if any(c.isascii() and c.isalpha() for c in r["input"][:100])
            and not any("一" <= c <= "鿿" for c in r["input"][:100])
            else "zh"
        )

    patent_ids = list({r["patent_id"] for r in records})
    zh_count = sum(1 for r in records if r["lang"] == "zh")
    en_count = len(records) - zh_count

    return PatentDataset(
        records=records,
        patent_ids=patent_ids,
        lang_stats={"zh": zh_count, "en": en_count, "total": len(records)},
    )


def split_by_patent(
    records: list,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> PatentAwareSplit:
    """Split records by patent_id to prevent context leakage."""
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 0.001

    patent_groups = {}
    for r in records:
        pid = r["patent_id"]
        patent_groups.setdefault(pid, []).append(r)

    patent_ids = list(patent_groups.keys())
    rng = random.Random(seed)
    rng.shuffle(patent_ids)

    n_total = len(patent_ids)
    n_train = max(1, int(n_total * train_ratio))
    n_val = max(1, int(n_total * val_ratio))

    train_ids = set(patent_ids[:n_train])
    val_ids = set(patent_ids[n_train : n_train + n_val])
    test_ids = set(patent_ids[n_train + n_val :])

    return PatentAwareSplit(
        train=[r for pid in train_ids for r in patent_groups[pid]],
        val=[r for pid in val_ids for r in patent_groups[pid]],
        test=[r for pid in test_ids for r in patent_groups[pid]],
    )
