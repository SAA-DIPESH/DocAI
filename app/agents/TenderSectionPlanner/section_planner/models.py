from __future__ import annotations

from typing import Any, Literal, TypeAlias

from pydantic import AliasChoices, BaseModel, ConfigDict, Field as PydanticField


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


JsonScalar: TypeAlias = str | int | float | bool | None
RequirementDisposition: TypeAlias = Literal[
    "RESPONSE_CONTENT",
    "ELIGIBILITY_OR_DECLARATION",
    "SUBMISSION_INSTRUCTION",
    "TENDER_METADATA",
    "CONTRACTUAL_CONTEXT",
    "REVIEW_REQUIRED",
]


class SourceEvidenceItem(StrictModel):
    DocumentId: str | None = None
    ChunkId: str | None = None
    ChunkIndex: int | str | None = None
    EvidenceExcerpt: str | None = None
    PageID: str | None = None
    PageNumber: int | str | None = None
    SupportedFields: list[str] = PydanticField(default_factory=list)


class SourceDocument(StrictModel):
    DocumentId: str | None = None
    DocumentName: str | None = None


class MandatoryCondition(StrictModel):
    ConditionId: str | None = None
    Name: str | None = None
    PrimaryCategory: str | None = None
    Rule: str | None = None
    ImpactIfNotMet: str | None = None
    SourceEvidence: list[SourceEvidenceItem] = PydanticField(default_factory=list)


class EvaluationConflict(StrictModel):
    ConflictId: str | None = None
    Field: str | None = None
    Description: str | None = None
    Status: str | None = None
    Values: list[Any] = PydanticField(default_factory=list)
    SourceEvidence: list[SourceEvidenceItem] = PydanticField(default_factory=list)


class MissingEvaluationInformation(StrictModel):
    Field: str | None = None
    Reason: str | None = None
    RelatedCriterionId: str | None = None
    SourceEvidence: list[SourceEvidenceItem] = PydanticField(default_factory=list)


class EvaluationReviewFlag(StrictModel):
    Type: str | None = None
    Description: str | None = None
    SourceEvidence: list[SourceEvidenceItem] = PydanticField(default_factory=list)


class OverallScoringDetails(StrictModel):
    AwardMethod: str | None = None
    QualityWeightPercent: JsonScalar = None
    PriceWeightPercent: JsonScalar = None
    OtherOverallWeightings: list[Any] = PydanticField(default_factory=list)
    ScoringScale: Any = None
    PriceScoringFormula: str | None = None
    SourceEvidence: list[SourceEvidenceItem] = PydanticField(default_factory=list)


class SectionPlannerRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    company_id: str = PydanticField(alias="CompanyId", min_length=1)
    tender_id: str = PydanticField(alias="TenderId", min_length=1)
    is_regenerate: bool = PydanticField(
        False,
        validation_alias=AliasChoices("IsRegenerate", "IsRegenerated"),
        serialization_alias="IsRegenerate",
    )
    user_id: str = PydanticField(alias="UserId", min_length=1)
    user_name: str = PydanticField(alias="UserName", min_length=1)
    project_id: str = PydanticField("", alias="ProjectId")
    jwt_token: str = PydanticField("", alias="JwtToken", exclude=True, repr=False)


class EvaluationCriterion(StrictModel):

    CriterionId: str
    Name: str = ""
    Description: str = ""
    PrimaryCategory: str = ""
    SecondaryCategories: list[str] = PydanticField(default_factory=list)
    ParentCriterionId: str | None = None
    QuestionReferences: list[str] = PydanticField(default_factory=list)
    WeightPercent: JsonScalar = None
    MaximumScore: JsonScalar = None
    MinimumScore: JsonScalar = None
    MinimumPercent: JsonScalar = None
    PassFail: JsonScalar = None
    Mandatory: JsonScalar = None
    PriceScoringFormula: str | None = None
    SourceEvidence: list[SourceEvidenceItem] = PydanticField(default_factory=list)


class RequirementNodeMapping(StrictModel):
    NodeId: str
    CanonicalRequirementIds: list[str]
    EvaluationCriterionIds: list[str] = PydanticField(default_factory=list)


class SectionPlannerLLMDecision(StrictModel):
    Mappings: list[RequirementNodeMapping]
    UnmappedCanonicalRequirementIds: list[str] = PydanticField(default_factory=list)


class DynamicSubSectionDecision(StrictModel):
    SubSectionName: str = PydanticField(min_length=1, max_length=120)
    SubSectionDescription: str = PydanticField(min_length=1, max_length=500)
    CanonicalRequirementIds: list[str] = PydanticField(min_length=1)
    EvaluationCriterionIds: list[str] = PydanticField(default_factory=list)


class DynamicSectionDecision(StrictModel):
    SectionName: str = PydanticField(min_length=1, max_length=120)
    SectionDescription: str = PydanticField(min_length=1, max_length=500)
    SubSections: list[DynamicSubSectionDecision] = PydanticField(min_length=1)


class DynamicProposalGroupDecision(StrictModel):
    GroupName: str = PydanticField(min_length=1, max_length=100)
    Sections: list[DynamicSectionDecision] = PydanticField(min_length=1)


class DynamicSectionPlannerLLMDecision(StrictModel):
    """Dynamic hierarchy content returned by the LLM; Python assigns all IDs."""

    ProposalGroups: list[DynamicProposalGroupDecision] = PydanticField(min_length=1)
    UnmappedCanonicalRequirementIds: list[str] = PydanticField(default_factory=list)
    UnmappedEvaluationCriterionIds: list[str] = PydanticField(default_factory=list)


class SectionNode(StrictModel):
    SectionId: str
    SectionName: str
    SectionDescription: str
    Required: bool = True
    Priority: Literal["High", "Medium", "Low", "Unknown"] = "Unknown"
    RequirementIds: list[str]
    EvaluationCriteria: list[EvaluationCriterion] = PydanticField(default_factory=list)
    SubSections: list[SectionNode] = PydanticField(default_factory=list)
    EvidenceRequired: bool = False
    CaseStudyRequired: bool = False
    Dependencies: list[str] = PydanticField(default_factory=list)
    AutoCreated: bool = False
    AutoCreatedReason: str | None = None


class ProposalGroup(StrictModel):
    GroupId: str
    GroupName: str
    Order: int = 0
    Sections: list[SectionNode]


class EvaluationSummary(StrictModel):
    EvaluationModelDetected: bool = False
    ExtractionStatus: str = ""
    Criteria: list[EvaluationCriterion] = PydanticField(default_factory=list)
    OverallScoring: OverallScoringDetails = PydanticField(default_factory=OverallScoringDetails)
    MandatoryConditions: list[MandatoryCondition] = PydanticField(default_factory=list)
    Conflicts: list[EvaluationConflict] = PydanticField(default_factory=list)
    MissingInformation: list[MissingEvaluationInformation] = PydanticField(default_factory=list)
    ReviewFlags: list[EvaluationReviewFlag] = PydanticField(default_factory=list)
    RequiresHumanReview: bool = False
    SourceDocuments: list[SourceDocument] = PydanticField(default_factory=list)


class ValidationResult(StrictModel):
    RequirementCoverageValid: bool
    EvaluationCriteriaCoverageValid: bool
    HierarchyValid: bool
    DependencyValid: bool
    NoEmptySections: bool
    NoUnsupportedWeights: bool
    Issues: list[str] = PydanticField(default_factory=list)
    SourceRequirementCoverageValid: bool = True
    ProposalRequirementCoverageValid: bool = True
    BlockingIssues: list[str] = PydanticField(default_factory=list)
    Warnings: list[str] = PydanticField(default_factory=list)
    Information: list[str] = PydanticField(default_factory=list)


class RequirementMapping(StrictModel):
    CanonicalRequirementId: str
    CanonicalRequirement: str
    SourceRequirementIds: list[str] = PydanticField(default_factory=list)
    SourceDocumentIds: list[str] = PydanticField(default_factory=list)
    SourceChunkIds: list[str] = PydanticField(default_factory=list)
    SectionId: str
    SubSectionId: str | None = None


class EvaluationCriterionMapping(StrictModel):
    CriterionId: str
    SectionId: str
    SubSectionId: str | None = None
    SourceEvidence: list[SourceEvidenceItem] = PydanticField(default_factory=list)


class EvidenceRequirementTrigger(StrictModel):
    SectionId: str
    SubSectionId: str | None = None
    SourceType: Literal["Requirement", "EvaluationCriterion"]
    SourceId: str
    Trigger: str
    SourceText: str


class RequirementPlanningDisposition(StrictModel):
    CanonicalRequirementId: str
    Disposition: RequirementDisposition
    ResponseApplicability: bool
    Reason: str
    Confidence: float
    SourceRequirementIds: list[str] = PydanticField(default_factory=list)
    SourceDocumentIds: list[str] = PydanticField(default_factory=list)


class Traceability(StrictModel):
    RequirementMappings: list[RequirementMapping] = PydanticField(default_factory=list)
    EvaluationCriterionMappings: list[EvaluationCriterionMapping] = PydanticField(default_factory=list)
    EvidenceRequirementTriggers: list[EvidenceRequirementTrigger] = PydanticField(
        default_factory=list
    )
    CaseStudyTriggers: list[EvidenceRequirementTrigger] = PydanticField(default_factory=list)


class ProposalPlan(StrictModel):
    ProposalPlanId: str
    CompanyId: str
    TenderId: str
    ProjectId: str
    Sector: str = ""
    PlanStatus: Literal["Generated", "Partial", "ValidationRequired"]
    ProposalGroups: list[ProposalGroup]
    MappedRequirementIds: list[str]
    UnmappedRequirementIds: list[str]
    MappedEvaluationCriterionIds: list[str]
    UnmappedEvaluationCriterionIds: list[str]
    RequirementDispositions: list[RequirementPlanningDisposition] = PydanticField(
        default_factory=list
    )
    NonResponseRequirements: list[RequirementPlanningDisposition] = PydanticField(
        default_factory=list
    )
    ReviewRequiredRequirements: list[RequirementPlanningDisposition] = PydanticField(
        default_factory=list
    )
    EvaluationSummary: EvaluationSummary
    Traceability: Traceability
    Validation: ValidationResult


class PublicValidationResult(BaseModel):
    """Validation fields safe and useful for public API consumers."""

    model_config = ConfigDict(extra="ignore")

    RequirementCoverageValid: bool
    EvaluationCriteriaCoverageValid: bool
    HierarchyValid: bool
    DependencyValid: bool
    NoEmptySections: bool
    NoUnsupportedWeights: bool
    Issues: list[str] = PydanticField(default_factory=list)
    SourceRequirementCoverageValid: bool = True
    ProposalRequirementCoverageValid: bool = True
    BlockingIssues: list[str] = PydanticField(default_factory=list)


class ProposalPlanResponse(ProposalPlan):
    """Public ProposalPlan DTO that ignores persistence-only audit metadata."""

    model_config = ConfigDict(extra="ignore")
    Validation: PublicValidationResult


SectionNode.model_rebuild()
