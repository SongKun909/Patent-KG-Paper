"""Stanza wrapper for bilingual dependency parsing."""
from typing import Optional

import stanza


class StanzaParser:
    """Bilingual dependency parser using Stanza (UD v2)."""

    _pipelines = {}  # Class-level cache

    def __init__(self, lang: str = "zh"):
        if lang not in self._pipelines:
            lang_code = "zh" if lang.startswith("zh") else "en"
            try:
                self._pipelines[lang] = stanza.Pipeline(
                    lang=lang_code,
                    processors="tokenize,pos,lemma,depparse",
                    verbose=False,
                    use_gpu=False,
                )
            except Exception:
                stanza.download(lang_code)
                self._pipelines[lang] = stanza.Pipeline(
                    lang=lang_code,
                    processors="tokenize,pos,lemma,depparse",
                    verbose=False,
                    use_gpu=False,
                )
        self.pipeline = self._pipelines[lang]
        self.lang = lang[:2]

    def parse(self, text: str) -> dict:
        """Parse text and return simplified dependency structure."""
        if not text.strip():
            return {"tokens": [], "dependencies": []}

        doc = self.pipeline(text)
        tokens = []
        dependencies = []

        for sentence in doc.sentences:
            for word in sentence.words:
                tokens.append(word.text)
                if word.head > 0 and word.deprel != "punct":
                    head_text = sentence.words[word.head - 1].text
                    dependencies.append({
                        "head": head_text,
                        "child": word.text,
                        "relation": word.deprel,
                        "head_id": word.head,
                        "child_id": word.id,
                    })

        return {"tokens": tokens, "dependencies": dependencies}
