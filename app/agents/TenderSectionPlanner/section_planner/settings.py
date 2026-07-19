from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .exceptions import ConfigurationError

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    mongo_db_name: str
    requirement_deduplication_collection: str
    evaluation_criteria_collection: str
    tender_section_plan_collection: str
    llm_provider: str
    openai_api_key: str
    openai_model: str
    openai_timeout_seconds: float
    openai_max_retries: int
    openai_reasoning_effort: str
    nvidia_api_key: str
    nvidia_model: str
    nvidia_base_url: str
    nvidia_timeout_seconds: float
    nvidia_max_retries: int
    nvidia_max_tokens: int
    nvidia_temperature: float
    nvidia_top_p: float
    nvidia_enable_thinking: bool
    nvidia_clear_thinking: bool
    mistral_api_key: str
    mistral_model: str
    mistral_base_url: str
    mistral_timeout_seconds: float
    mistral_max_retries: int
    mistral_temperature: float
    constitution_path: Path
    specification_path: Path
    user_prompt_path: Path
    llm_max_input_tokens: int
    llm_max_output_tokens: int
    llm_repair_attempts: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            mongo_uri=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
            mongo_db_name=os.getenv("MONGO_DB_NAME", "DocAI"),
            requirement_deduplication_collection=os.getenv(
                "REQUIREMENT_DEDUPLICATION_COLLECTION", "TenderRequirementDeduplications"
            ),
            evaluation_criteria_collection=os.getenv(
                "EVALUATION_CRITERIA_COLLECTION", "EvaluationCriteria"
            ),
            tender_section_plan_collection=os.getenv(
                "TENDER_SECTION_PLAN_COLLECTION", "TenderSectionPlans"
            ),
            llm_provider=os.getenv("LLM_PROVIDER", "openai").strip().lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.1"),
            openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "180")),
            openai_max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "2")),
            openai_reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "medium"),
            nvidia_api_key=os.getenv("NVIDIA_API_KEY", ""),
            nvidia_model=os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct"),
            nvidia_base_url=os.getenv(
                "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
            ),
            nvidia_timeout_seconds=float(os.getenv("NVIDIA_TIMEOUT_SECONDS", "180")),
            nvidia_max_retries=int(os.getenv("NVIDIA_MAX_RETRIES", "2")),
            nvidia_max_tokens=int(os.getenv("NVIDIA_MAX_TOKENS", "8192")),
            nvidia_temperature=float(os.getenv("NVIDIA_TEMPERATURE", "0.1")),
            nvidia_top_p=float(os.getenv("NVIDIA_TOP_P", "0.7")),
            nvidia_enable_thinking=_env_bool("NVIDIA_ENABLE_THINKING", True),
            nvidia_clear_thinking=_env_bool("NVIDIA_CLEAR_THINKING", False),
            mistral_api_key=os.getenv("MISTRAL_API_KEY", ""),
            mistral_model=os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
            mistral_base_url=os.getenv(
                "MISTRAL_BASE_URL", "https://api.mistral.ai/v1"
            ),
            mistral_timeout_seconds=float(os.getenv("MISTRAL_TIMEOUT_SECONDS", "180")),
            mistral_max_retries=int(os.getenv("MISTRAL_MAX_RETRIES", "2")),
            mistral_temperature=float(os.getenv("MISTRAL_TEMPERATURE", "0.2")),
            constitution_path=Path(
                os.getenv(
                    "SECTION_PLANNER_CONSTITUTION_PATH",
                    str(_PROJECT_ROOT / "Section_Planner_Constitution.md"),
                )
            ),
            specification_path=Path(
                os.getenv(
                    "SECTION_PLANNER_SPECIFICATION_PATH",
                    str(_PROJECT_ROOT / "Section_Planner_Specification.md"),
                )
            ),
            user_prompt_path=Path(
                os.getenv(
                    "SECTION_PLANNER_USER_PROMPT_PATH",
                    str(_PROJECT_ROOT / "Section_Planner_User_Prompt.md"),
                )
            ),
            llm_max_input_tokens=max(1, int(os.getenv("LLM_MAX_INPUT_TOKENS", "12000"))),
            llm_max_output_tokens=max(1, int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "3000"))),
            llm_repair_attempts=min(
                1,
                max(
                    0,
                    int(
                        os.getenv(
                            "LLM_MAX_REPAIR_ATTEMPTS",
                            os.getenv("LLM_REPAIR_ATTEMPTS", "1"),
                        )
                    ),
                ),
            ),
        )

    def validate(self) -> None:
        missing = []
        if self.llm_provider not in {"openai", "nvidia", "mistral"}:
            raise ConfigurationError(
                "LLM_PROVIDER must be openai, nvidia, or mistral"
            )
        if self.llm_provider == "openai":
            if not self.openai_api_key.strip():
                missing.append("OPENAI_API_KEY")
            if not self.openai_model.strip():
                missing.append("OPENAI_MODEL")
        if self.llm_provider == "nvidia":
            if not self.nvidia_api_key.strip():
                missing.append("NVIDIA_API_KEY")
            if not self.nvidia_model.strip():
                missing.append("NVIDIA_MODEL")
            if not self.nvidia_base_url.strip():
                missing.append("NVIDIA_BASE_URL")
        if self.llm_provider == "mistral":
            if not self.mistral_api_key.strip():
                missing.append("MISTRAL_API_KEY")
            if not self.mistral_model.strip():
                missing.append("MISTRAL_MODEL")
            if not self.mistral_base_url.strip():
                missing.append("MISTRAL_BASE_URL")
        if not self.mongo_uri.strip():
            missing.append("MONGO_URI")
        if not self.mongo_db_name.strip():
            missing.append("MONGO_DB_NAME")
        if not self.requirement_deduplication_collection.strip():
            missing.append("REQUIREMENT_DEDUPLICATION_COLLECTION")
        if not self.evaluation_criteria_collection.strip():
            missing.append("EVALUATION_CRITERIA_COLLECTION")
        if not self.tender_section_plan_collection.strip():
            missing.append("TENDER_SECTION_PLAN_COLLECTION")
        if missing:
            raise ConfigurationError("Missing required configuration: " + ", ".join(missing))
        for label, path in (
            ("Constitution", self.constitution_path),
            ("Specification", self.specification_path),
            ("User Prompt", self.user_prompt_path),
        ):
            if not path.is_file():
                raise ConfigurationError(f"{label} markdown file does not exist: {path}")
            if not path.read_text(encoding="utf-8").strip():
                raise ConfigurationError(f"{label} markdown file is empty: {path}")
