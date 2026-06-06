"""Map UD v2 dependency relations to quintuple element candidates."""
from typing import List


class UDToQuintupleMapper:
    """Maps Universal Dependencies v2 relations to quintuple hints."""

    OBJECT_RELATIONS = {"nsubj", "nsubj:pass", "csubj"}
    NAME_RELATIONS = {"obj", "iobj", "compound", "nmod", "amod"}
    VALUE_RELATIONS = {"nummod", "nmod:num", "quantmod"}
    RELATION_RELATIONS = {"root", "cop", "case", "mark"}
    CONDITION_RELATIONS = {
        "advcl", "obl", "obl:tmod", "advmod", "nmod:temp",
    }

    def map_to_hints(self, dependencies: List[dict]) -> dict:
        """Convert dependency parse to quintuple element hints."""
        hints = {
            "object_candidates": [],
            "name_candidates": [],
            "value_candidates": [],
            "relation_candidates": [],
            "condition_candidates": [],
            "raw_deps": dependencies,
        }

        for dep in dependencies:
            rel = dep["relation"].lower()

            if rel in self.OBJECT_RELATIONS:
                hints["object_candidates"].append(dep["child"])
            if rel in self.NAME_RELATIONS:
                hints["name_candidates"].append(dep["child"])
            if rel in self.VALUE_RELATIONS:
                hints["value_candidates"].append(dep["child"])
            if rel in self.RELATION_RELATIONS:
                hints["relation_candidates"].append(dep["child"])
            if rel in self.CONDITION_RELATIONS:
                hints["condition_candidates"].append(dep["child"])

        return hints
