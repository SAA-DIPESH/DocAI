class SectionPlannerError(Exception):
    """Base controlled planner error."""


class SourceNotFoundError(SectionPlannerError):
    pass


class InvalidSourceError(SectionPlannerError):
    pass


class PersistenceError(SectionPlannerError):
    pass


class ConfigurationError(SectionPlannerError):
    pass


class LLMServiceError(SectionPlannerError):
    pass


class LLMTimeoutError(LLMServiceError):
    pass


class LLMRateLimitError(LLMServiceError):
    pass


class StructuredOutputError(LLMServiceError):
    pass


class PlanValidationError(SectionPlannerError):
    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("Generated plan failed validation: " + "; ".join(issues))
