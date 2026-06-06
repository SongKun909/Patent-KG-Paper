"""Configuration management via YAML files."""
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class LLMConfig:
    provider: str = "deepseek"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/anthropic"
    model: str = "deepseek-v4-pro[1m]"
    temperature: float = 0.1
    max_tokens: int = 4096


@dataclass
class FilterConfig:
    regex_enabled: bool = True
    classifier_model_path: str = "models/fasttext_indicator.bin"
    confidence_threshold: float = 0.5


@dataclass
class AgentConfig:
    max_retries: int = 2
    chunk_size: int = 1000
    parallel_chunks: bool = True
    verify_dimensions: list = field(
        default_factory=lambda: [
            "physical_boundary",
            "logical_consistency",
            "syntactic_completeness",
        ]
    )


@dataclass
class PipelineConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    filter: FilterConfig = field(default_factory=FilterConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    dataset_path: str = "SongKun909/Lithium-Battery-IE-Dataset"
    output_dir: str = "output"
    seed: int = 42

    @classmethod
    def from_yaml(cls, path: str) -> "PipelineConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        llm = LLMConfig(**data.get("llm", {}))
        filt = FilterConfig(**data.get("filter", {}))
        agent = AgentConfig(**data.get("agent", {}))
        return cls(
            llm=llm,
            filter=filt,
            agent=agent,
            dataset_path=data.get("dataset_path", cls.dataset_path),
            output_dir=data.get("output_dir", cls.output_dir),
            seed=data.get("seed", cls.seed),
        )


def load_config(config_path: Optional[str] = None) -> PipelineConfig:
    if config_path and Path(config_path).exists():
        return PipelineConfig.from_yaml(config_path)

    import os

    return PipelineConfig(
        llm=LLMConfig(
            api_key=os.environ.get(
                "ANTHROPIC_AUTH_TOKEN",
                "REDACTED_API_KEY",
            ),
            base_url=os.environ.get(
                "ANTHROPIC_BASE_URL",
                "https://api.deepseek.com/anthropic",
            ),
        )
    )
