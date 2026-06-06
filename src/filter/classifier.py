"""Layer 2: fastText binary classifier for indicator sentence filtering."""
import os
import json
import tempfile
from pathlib import Path
from typing import List

import fasttext


class IndicatorClassifier:
    """Binary classifier to distinguish indicator sentences from noise."""

    def __init__(self, model_path: str = None):
        self.model = None
        if model_path and Path(model_path).exists():
            self.model = fasttext.load_model(model_path)

    def _prepare_training_data(
        self,
        records: List[dict],
        output_path: str,
    ) -> int:
        """Convert labeled records to fastText training format.

        Each record has 'input' (patent text) and 'output' (quintuple JSON).
        We label sentences containing extracted quintuple values as '__label__indicator'.
        """
        import re

        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for record in records:
                text = record.get("input", "")
                output = record.get("output", "")

                # Determine which sentences have indicators
                indicator_sentences = set()
                if output:
                    try:
                        quints = json.loads(output) if isinstance(output, str) else output
                        if isinstance(quints, dict):
                            quints = [quints]
                        for q in quints:
                            val = q.get("指标数值", "")
                            name = q.get("指标名称", "")
                            if val or name:
                                # Find sentences containing this value
                                sentences = re.split(r"[。.；;\n]", text)
                                for sent in sentences:
                                    if val in sent or name in sent:
                                        indicator_sentences.add(sent.strip())
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Write all sentences with labels
                sentences = re.split(r"[。.；;\n]", text)
                for sent in sentences:
                    sent = sent.strip()
                    if len(sent) < 5:
                        continue
                    label = (
                        "__label__indicator"
                        if sent in indicator_sentences
                        else "__label__noise"
                    )
                    # Escape newlines and tabs
                    sent_clean = sent.replace("\n", " ").replace("\t", " ")
                    f.write(f"{label} {sent_clean}\n")
                    count += 1

        return count

    def train(
        self,
        records: List[dict],
        model_output_path: str = "models/fasttext_indicator.bin",
    ) -> None:
        """Train a fastText binary classifier."""
        os.makedirs(os.path.dirname(model_output_path) or ".", exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp:
            train_file = tmp.name

        try:
            n_examples = self._prepare_training_data(records, train_file)
            print(f"Prepared {n_examples} training examples")

            self.model = fasttext.train_supervised(
                input=train_file,
                lr=0.5,
                epoch=25,
                wordNgrams=2,
                dim=100,
                loss="softmax",
                verbose=2,
            )

            self.model.save_model(model_output_path)
            print(f"Model saved to {model_output_path}")

            # Quick eval
            result = self.model.test(train_file)
            print(f"Training precision: {result[1]:.4f}, recall: {result[2]:.4f}")

        finally:
            if os.path.exists(train_file):
                os.unlink(train_file)

    def predict(self, sentence: str) -> float:
        """Predict probability that a sentence contains an indicator.

        Returns:
            float: 0.0 (noise) to 1.0 (indicator)
        """
        if self.model is None:
            return 1.0  # If no model, pass through

        sent_clean = sentence.replace("\n", " ").replace("\t", " ")
        labels, probs = self.model.predict(sent_clean, k=2)
        for label, prob in zip(labels, probs):
            if label == "__label__indicator":
                return prob
        return 0.0

    def filter(
        self, sentences: List[str], threshold: float = 0.5
    ) -> List[str]:
        """Filter sentences to only those classified as indicators."""
        return [s for s in sentences if self.predict(s) >= threshold]
