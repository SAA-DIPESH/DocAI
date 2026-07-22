from __future__ import annotations

import json
import hashlib
import logging
import re
import time
import uuid
from collections import Counter
from typing import Any

from .exceptions import (
    InvalidSourceError,
    PersistenceError,
    PlanValidationError,
    SourceNotFoundError,
)
from .assembly import ProposalPlanAssembler
from .disposition import classify_requirement
from .llm import (
    LLMResult,
    SectionPlannerLLMProvider,
    create_llm_provider,
    estimate_input_tokens,
)
from .models import (
    DynamicSectionPlannerLLMDecision,
    ProposalPlan,
    RequirementNodeMapping,
    SectionPlannerLLMDecision,
    SectionPlannerRequest,
)
from .prompts import PlannerPrompts, PromptLoader
from .repository import PlannerRepository
from .settings import Settings
from .state import SectionPlannerState
from .validation import PlanValidator

logger = logging.getLogger("uvicorn.error")


def _payload(record: dict[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {}
    output = record.get("Output")
    if isinstance(output, dict):
        return output
    json_output = record.get("JsonOutput")
    if isinstance(json_output, dict):
        return json_output
    final_json = record.get("FinalJson")
    return final_json if isinstance(final_json, dict) else record


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items() if key != "_id"}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _nested(document: dict[str, Any], *path: str) -> Any:
    value: Any = document
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def extract_deduplicated_requirements(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract only established Requirement Agent persistence shapes."""
    candidates = (
        _nested(document, "JsonOutput", "DeduplicatedRequirements"),
        _nested(document, "Output", "DeduplicatedRequirements"),
        _nested(document, "JsonOutput", "Output", "DeduplicatedRequirements"),
        _nested(document, "FinalJson", "Output", "DeduplicatedRequirements"),
        document.get("DeduplicatedRequirements"),
        _nested(document, "JsonOutput", "CanonicalRequirements"),
        _nested(document, "FinalJson", "CanonicalRequirements"),
    )
    for candidate in candidates:
        if isinstance(candidate, list) and candidate:
            return candidate
    raise InvalidSourceError(
        "Requirement Deduplication record does not contain a non-empty canonical requirement collection"
    )


class SectionPlannerService:
    """LLM semantic decisions with deterministic Python-owned plan assembly."""

    def __init__(
        self,
        repository: PlannerRepository,
        settings: Settings | None = None,
        llm: SectionPlannerLLMProvider | None = None,
        prompt_loader: PromptLoader | None = None,
        validator: PlanValidator | None = None,
        assembler: ProposalPlanAssembler | None = None,
    ) -> None:
        self.repository = repository
        self.settings = settings or Settings.from_env()
        self.prompt_loader = prompt_loader or PromptLoader(self.settings)
        self.validator = validator or PlanValidator()
        self.assembler = assembler or ProposalPlanAssembler()
        self.llm = llm

    async def execute(self, request: SectionPlannerRequest) -> dict[str, Any]:
        started = time.monotonic()
        run_id = str(uuid.uuid4())
        # Selected LLM provider and prompt configuration are mandatory before source loading;
        # an unconfigured agent must never degrade into a non-AI execution path.
        self.settings.validate()
        state = self.validate_request(request)
        self.initialise_operational_state(state)
        self.load_sources(state)
        requirements = self.normalize_canonical_requirements(state)
        evaluation = self.normalize_evaluation_criteria(state)
        self._log_source_summary(state, requirements, evaluation)
        prompts = self.prompt_loader.load()
        llm = self.llm or create_llm_provider(self.settings)
        instructions, runtime_prompt, estimated_input_tokens = self.build_llm_context(
            prompts, requirements, evaluation
        )

        result = await llm.generate_plan(
            instructions=instructions,
            runtime_prompt=runtime_prompt,
            output_model=DynamicSectionPlannerLLMDecision,
        )
        repair_attempts = 0
        usage = dict(result.usage)
        decision = self._normalize_dynamic_decision(
            DynamicSectionPlannerLLMDecision.model_validate(result.plan),
            requirements,
            evaluation,
        )
        plan, issues = self._assemble_and_validate(
            decision, state, requirements, evaluation
        )
        max_repair_attempts = min(1, self.settings.llm_repair_attempts)
        while issues and repair_attempts < max_repair_attempts:
            repair_attempts += 1
            result = await llm.repair_plan(
                instructions=instructions,
                runtime_prompt=runtime_prompt,
                previous_output=decision.model_dump(),
                validation_errors=issues,
                output_model=DynamicSectionPlannerLLMDecision,
            )
            self._add_usage(usage, result.usage)
            decision = self._normalize_dynamic_decision(
                DynamicSectionPlannerLLMDecision.model_validate(
                    result.plan
                ),
                requirements,
                evaluation,
            )
            plan, issues = self._assemble_and_validate(
                decision, state, requirements, evaluation
            )
        if issues:
            raise PlanValidationError(issues)
        if plan is None:
            raise PlanValidationError(["Python could not assemble ProposalPlan"])

        document = self.prepare_persistence(
            state,
            plan,
            result,
            prompts,
            usage,
            repair_attempts,
            len(requirements),
            len(evaluation["Criteria"]),
            estimated_input_tokens,
            sum(
                requirement.get("ResponseApplicability") is True
                for requirement in requirements
            ),
        )
        stored = self.persist_plan(document, state["IsRegenerate"])
        section_count, subsection_count = self._node_counts(plan)
        logger.info(
            "Section planning completed | run_id=%s company_id=%s tender_id=%s project_id=%s "
            "model=%s response_id=%s duration_ms=%s repairs=%s requirements=%s criteria=%s "
            "sections=%s subsections=%s mapped_requirements=%s unmapped_requirements=%s "
            "request_count=%s estimated_input_tokens=%s actual_input_tokens=%s "
            "actual_output_tokens=%s valid=true",
            run_id,
            state["CompanyId"],
            state["TenderId"],
            state["ProjectId"],
            result.model,
            result.response_id,
            round((time.monotonic() - started) * 1000),
            repair_attempts,
            len(requirements),
            len(evaluation["Criteria"]),
            section_count,
            subsection_count,
            len(plan.MappedRequirementIds),
            len(plan.UnmappedRequirementIds),
            1 + repair_attempts,
            estimated_input_tokens,
            usage.get("InputTokens", 0),
            usage.get("OutputTokens", 0),
        )
        return stored

    @staticmethod
    def _normalize_llm_decision(
        decision: SectionPlannerLLMDecision,
        requirements: list[dict[str, Any]],
    ) -> SectionPlannerLLMDecision:
        """Normalize the retired configured-node contract for adapter compatibility."""

        merged_by_node: dict[str, dict[str, Any]] = {}
        node_order: list[str] = []
        for mapping in decision.Mappings:
            node_id = str(mapping.NodeId)
            if node_id not in merged_by_node:
                merged_by_node[node_id] = {
                    "NodeId": node_id,
                    "CanonicalRequirementIds": [],
                    "EvaluationCriterionIds": [],
                }
                node_order.append(node_id)
            target = merged_by_node[node_id]
            for requirement_id in mapping.CanonicalRequirementIds:
                if requirement_id not in target["CanonicalRequirementIds"]:
                    target["CanonicalRequirementIds"].append(requirement_id)
            for criterion_id in mapping.EvaluationCriterionIds:
                if criterion_id not in target["EvaluationCriterionIds"]:
                    target["EvaluationCriterionIds"].append(criterion_id)

        merged_mappings = [merged_by_node[node_id] for node_id in node_order]
        mapped_requirement_ids = {
            requirement_id
            for mapping in merged_mappings
            for requirement_id in mapping["CanonicalRequirementIds"]
        }
        response_requirement_ids = [
            str(requirement["CanonicalRequirementId"])
            for requirement in requirements
            if requirement.get("ResponseApplicability") is True
        ]
        response_requirement_id_set = set(response_requirement_ids)
        unmapped_requirement_ids = [
            requirement_id
            for requirement_id in response_requirement_ids
            if requirement_id not in mapped_requirement_ids
        ]
        for requirement_id in decision.UnmappedCanonicalRequirementIds:
            if (
                requirement_id not in response_requirement_id_set
                and requirement_id not in unmapped_requirement_ids
            ):
                unmapped_requirement_ids.append(requirement_id)
        return SectionPlannerLLMDecision.model_validate(
            {
                "Mappings": merged_mappings,
                "UnmappedCanonicalRequirementIds": unmapped_requirement_ids,
            }
        )

    @staticmethod
    def _normalize_dynamic_decision(
        decision: DynamicSectionPlannerLLMDecision,
        requirements: list[dict[str, Any]],
        evaluation: dict[str, Any],
    ) -> DynamicSectionPlannerLLMDecision:
        """Reconcile unmapped requirements and assign each known criterion one owner."""

        payload = decision.model_dump()
        criteria_by_id = {
            str(item["CriterionId"]): item
            for item in _list(evaluation.get("Criteria"))
            if item.get("CriterionId")
        }
        known_criterion_ids = set(criteria_by_id)
        requirements_by_id = {
            str(item["CanonicalRequirementId"]): item
            for item in requirements
            if item.get("CanonicalRequirementId")
        }
        nodes: list[tuple[tuple[int, int, int], dict[str, Any], str]] = []
        for group_index, group in enumerate(payload["ProposalGroups"]):
            for section_index, section in enumerate(group["Sections"]):
                for subsection_index, subsection in enumerate(section["SubSections"]):
                    requirement_text = " ".join(
                        str(
                            requirements_by_id.get(requirement_id, {}).get(
                                "CanonicalRequirement", ""
                            )
                        )
                        for requirement_id in subsection["CanonicalRequirementIds"]
                    )
                    node_text = " ".join(
                        (
                            group["GroupName"],
                            section["SectionName"],
                            section["SectionDescription"],
                            subsection["SubSectionName"],
                            subsection["SubSectionDescription"],
                            requirement_text,
                        )
                    ).casefold()
                    nodes.append(
                        (
                            (group_index, section_index, subsection_index),
                            subsection,
                            node_text,
                        )
                    )

        winner_by_criterion: dict[str, tuple[int, int, int]] = {}
        for criterion_id, criterion in criteria_by_id.items():
            candidates = [node for node in nodes if criterion_id in node[1]["EvaluationCriterionIds"]]
            if not candidates:
                continue
            criterion_text = " ".join(
                str(criterion.get(key) or "")
                for key in ("Name", "Description", "PrimaryCategory")
            ).casefold()
            if "social value" in criterion_text:
                # The existing semantic validator requires an explicit Social Value owner.
                candidates = [node for node in candidates if "social value" in node[2]]
                if not candidates:
                    continue
            criterion_terms = set(re.findall(r"[a-z0-9]+", criterion_text))
            winner = max(
                candidates,
                key=lambda node: len(
                    criterion_terms & set(re.findall(r"[a-z0-9]+", node[2]))
                ),
            )
            winner_by_criterion[criterion_id] = winner[0]

        for path, subsection, _ in nodes:
            normalized_criterion_ids: list[str] = []
            for criterion_id in subsection["EvaluationCriterionIds"]:
                # Unknown IDs remain present for deterministic rejection.
                if criterion_id not in known_criterion_ids:
                    normalized_criterion_ids.append(criterion_id)
                    continue
                if winner_by_criterion.get(criterion_id) != path:
                    continue
                if criterion_id not in normalized_criterion_ids:
                    normalized_criterion_ids.append(criterion_id)
            subsection["EvaluationCriterionIds"] = normalized_criterion_ids

        mapped_criterion_ids = {
            criterion_id
            for _, subsection, _ in nodes
            for criterion_id in subsection["EvaluationCriterionIds"]
            if criterion_id in known_criterion_ids
        }
        unmapped_criterion_ids = [
            criterion_id
            for criterion_id in criteria_by_id
            if criterion_id not in mapped_criterion_ids
        ]
        for criterion_id in decision.UnmappedEvaluationCriterionIds:
            if (
                criterion_id not in known_criterion_ids
                and criterion_id not in unmapped_criterion_ids
            ):
                unmapped_criterion_ids.append(criterion_id)
        payload["UnmappedEvaluationCriterionIds"] = unmapped_criterion_ids

        mapped_requirement_ids = {
            requirement_id
            for group in decision.ProposalGroups
            for section in group.Sections
            for subsection in section.SubSections
            for requirement_id in subsection.CanonicalRequirementIds
        }
        response_requirement_ids = [
            str(requirement["CanonicalRequirementId"])
            for requirement in requirements
            if requirement.get("ResponseApplicability") is True
        ]
        response_requirement_id_set = set(response_requirement_ids)

        unmapped_requirement_ids = [
            requirement_id
            for requirement_id in response_requirement_ids
            if requirement_id not in mapped_requirement_ids
        ]
        for requirement_id in decision.UnmappedCanonicalRequirementIds:
            if (
                requirement_id
                not in response_requirement_id_set
                and requirement_id
                not in unmapped_requirement_ids
            ):
                unmapped_requirement_ids.append(requirement_id)
        payload["UnmappedCanonicalRequirementIds"] = unmapped_requirement_ids
        return DynamicSectionPlannerLLMDecision.model_validate(payload)

    @staticmethod
    def _dynamic_id(prefix: str, *parts: Any) -> str:
        identity = "|".join(
            re.sub(r"\s+", " ", str(part).strip()).casefold() for part in parts
        )
        return f"{prefix}-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]}"

    def _materialize_dynamic_hierarchy(
        self,
        decision: DynamicSectionPlannerLLMDecision,
        state: SectionPlannerState,
    ) -> tuple[dict[str, Any], SectionPlannerLLMDecision, list[str]]:
        """Assign stable Python-owned IDs to the LLM-selected dynamic hierarchy."""

        issues: list[str] = []
        groups: list[dict[str, Any]] = []
        mappings: list[RequirementNodeMapping] = []
        seen_group_names: set[str] = set()

        for group_index, group in enumerate(decision.ProposalGroups):
            group_name = group.GroupName.strip()
            group_key = group_name.casefold()
            if not group_name:
                issues.append("Dynamic GroupName must not be blank")
            if group_key in seen_group_names:
                issues.append(f"Duplicate dynamic GroupName: {group_name}")
            seen_group_names.add(group_key)
            group_id = self._dynamic_id(
                "grp-dyn",
                state["CompanyId"],
                state["TenderId"],
                group_index,
                group_name,
            )
            sections: list[dict[str, Any]] = []
            seen_section_names: set[str] = set()

            for section_index, section in enumerate(group.Sections):
                section_name = section.SectionName.strip()
                section_key = section_name.casefold()
                if not section_name:
                    issues.append(f"Blank SectionName in group {group_name}")
                if section_key in seen_section_names:
                    issues.append(
                        f"Duplicate dynamic SectionName in {group_name}: {section_name}"
                    )
                seen_section_names.add(section_key)
                section_id = self._dynamic_id(
                    "sec-dyn",
                    state["CompanyId"],
                    state["TenderId"],
                    group_index,
                    group_name,
                    section_index,
                    section_name,
                )
                subsections: list[dict[str, Any]] = []
                seen_subsection_names: set[str] = set()

                for subsection_index, subsection in enumerate(section.SubSections):
                    subsection_name = subsection.SubSectionName.strip()
                    subsection_key = subsection_name.casefold()
                    if not subsection_name:
                        issues.append(f"Blank SubSectionName in section {section_name}")
                    if subsection_key in seen_subsection_names:
                        issues.append(
                            "Duplicate dynamic SubSectionName in "
                            f"{section_name}: {subsection_name}"
                        )
                    seen_subsection_names.add(subsection_key)
                    subsection_id = self._dynamic_id(
                        "sub-dyn",
                        state["CompanyId"],
                        state["TenderId"],
                        group_index,
                        group_name,
                        section_index,
                        section_name,
                        subsection_index,
                        subsection_name,
                    )
                    subsections.append(
                        {
                            "SubSectionId": subsection_id,
                            "SubSectionName": subsection_name,
                            "SectionDescription": subsection.SubSectionDescription.strip(),
                            "Order": subsection_index,
                            "RequirementTypes": [],
                            "Dependencies": [],
                        }
                    )
                    mappings.append(
                        RequirementNodeMapping(
                            NodeId=subsection_id,
                            CanonicalRequirementIds=subsection.CanonicalRequirementIds,
                            EvaluationCriterionIds=subsection.EvaluationCriterionIds,
                        )
                    )

                sections.append(
                    {
                        "SectionId": section_id,
                        "SectionName": section_name,
                        "SectionDescription": section.SectionDescription.strip(),
                        "Order": section_index,
                        "RequirementTypes": [],
                        "Dependencies": [],
                        "SubSections": subsections,
                    }
                )

            groups.append(
                {
                    "GroupId": group_id,
                    "GroupName": group_name,
                    "Order": group_index,
                    "Sections": sections,
                }
            )

        hierarchy = {"Sector": "", "Groups": groups}
        mapping_decision = SectionPlannerLLMDecision(
            Mappings=mappings,
            UnmappedCanonicalRequirementIds=decision.UnmappedCanonicalRequirementIds,
        )
        return hierarchy, mapping_decision, issues

    def _assemble_and_validate(
        self,
        decision: DynamicSectionPlannerLLMDecision,
        state: SectionPlannerState,
        requirements: list[dict[str, Any]],
        evaluation: dict[str, Any],
    ) -> tuple[ProposalPlan | None, list[str]]:
        hierarchy, mapping_decision, issues = self._materialize_dynamic_hierarchy(
            decision, state
        )
        known_criterion_ids = {
            str(item["CriterionId"])
            for item in _list(evaluation.get("Criteria"))
            if item.get("CriterionId")
        }
        unknown_unmapped_criteria = (
            set(decision.UnmappedEvaluationCriterionIds) - known_criterion_ids
        )
        if unknown_unmapped_criteria:
            issues.append(
                "Invented unmapped EvaluationCriterionIds: "
                f"{sorted(unknown_unmapped_criteria)}"
            )
        if issues:
            return None, issues
        issues = self.assembler.validate_decisions(
            mapping_decision, hierarchy, requirements, evaluation
        )
        if issues:
            return None, issues
        plan = self.assembler.assemble(
            mapping_decision,
            hierarchy,
            requirements,
            evaluation,
            company_id=state["CompanyId"],
            tender_id=state["TenderId"],
            project_id=state["ProjectId"],
        )
        return plan, self.validator.validate(
            plan,
            hierarchy,
            requirements,
            evaluation,
            state["CompanyId"],
            state["TenderId"],
        )

    @staticmethod
    def validate_request(request: SectionPlannerRequest) -> SectionPlannerState:
        # JwtToken is excluded by the request model and never enters state or prompts.
        return SectionPlannerState(**request.model_dump(by_alias=True))

    @staticmethod
    def initialise_operational_state(state: SectionPlannerState) -> None:
        state["Status"] = "Regenerating" if state["IsRegenerate"] else "Active"

    def load_sources(self, state: SectionPlannerState) -> None:
        company_id, tender_id = state["CompanyId"], state["TenderId"]
        operational_status = state["Status"]
        requirements = self.repository.load_requirements(
            company_id, tender_id, operational_status
        )
        evaluation = self.repository.load_evaluation(
            company_id, tender_id, operational_status
        )
        if not requirements:
            raise SourceNotFoundError(
                f"{operational_status} Requirement Deduplication output was not found"
            )
        # Evaluation Criteria is optional: a null/NOT_FOUND result is a legitimate
        # extraction outcome (no evaluation model in the tender), not a blocker.
        # The plan is still built from requirements alone in that case.
        sources = [("Requirement Deduplication output", requirements)]
        if evaluation:
            sources.append(("Evaluation Criteria output", evaluation))
        for label, record in sources:
            self._validate_source_scope(label, record, company_id, tender_id)
        state["requirement_record"] = requirements
        state["evaluation_record"] = evaluation

    @staticmethod
    def _validate_source_scope(
        label: str, record: dict[str, Any], company_id: str, tender_id: str
    ) -> None:
        if (
            str(record.get("CompanyId", company_id)) != company_id
            or str(record.get("TenderId", tender_id)) != tender_id
        ):
            raise InvalidSourceError(
                f"{label} does not match the requested CompanyId and TenderId"
            )

    @staticmethod
    def normalize_canonical_requirements(
        state: SectionPlannerState,
    ) -> list[dict[str, Any]]:
        raw = extract_deduplicated_requirements(state["requirement_record"])
        normalized: list[dict[str, Any]] = []
        for item in raw:
            canonical_id = item.get("CanonicalRequirementId")
            canonical_text = item.get("CanonicalRequirement") or item.get(
                "CanonicalRequirementText"
            )
            if not canonical_id or not canonical_text:
                raise InvalidSourceError(
                    "Every canonical requirement requires CanonicalRequirementId and canonical text"
                )
            raw_intent = item.get("IntentResult")
            if isinstance(raw_intent, dict):
                intent_result = _json_safe(raw_intent)
            else:
                intent_result = {
                    "CapabilityIntent": _json_safe(
                        _list(item.get("CapabilityIntents"))
                    ),
                    "EvidenceSections": _json_safe(
                        _list(item.get("EvidenceSections"))
                    ),
                    "SemanticAnchors": _json_safe(
                        _list(item.get("SemanticAnchors"))
                    ),
                }
            aggregate_types = _list(item.get("RequirementTypes"))
            requirement_type = item.get("RequirementType") or next(
                (value for value in aggregate_types if value), None
            )
            raw_requirement_ids = list(
                dict.fromkeys(
                    str(value)
                    for value in _list(item.get("RequirementIds"))
                    if value is not None and str(value).strip()
                )
            )
            source_values = _list(item.get("SourceRequirements"))
            source_documents = _list(item.get("SourceDocuments"))
            sources: list[dict[str, Any]] = []
            for index, source in enumerate(source_values):
                if isinstance(source, dict):
                    normalized_source = dict(source)
                else:
                    normalized_source = {"RequirementId": str(source)}
                    if index < len(source_documents) and source_documents[index] is not None:
                        normalized_source["DocumentId"] = source_documents[index]
                if requirement_type and not normalized_source.get("RequirementType"):
                    normalized_source["RequirementType"] = requirement_type
                if (
                    item.get("MandatoryFlag") is not None
                    and normalized_source.get("MandatoryFlag") is None
                ):
                    normalized_source["MandatoryFlag"] = item["MandatoryFlag"]
                if intent_result and not isinstance(
                    normalized_source.get("IntentResult"), dict
                ):
                    normalized_source["IntentResult"] = intent_result
                sources.append(normalized_source)

            source_requirement_ids = {
                str(source.get("RequirementId"))
                for source in sources
                if source.get("RequirementId")
            }
            for requirement_id in raw_requirement_ids:
                if requirement_id in source_requirement_ids:
                    continue
                lineage = {
                    "RequirementId": requirement_id,
                    "RequirementType": requirement_type,
                    "IntentResult": intent_result,
                }
                sources.append(
                    {key: value for key, value in lineage.items() if value not in (None, {})}
                )
                source_requirement_ids.add(requirement_id)

            requirement_ids = raw_requirement_ids or list(
                dict.fromkeys(
                    str(source["RequirementId"])
                    for source in sources
                    if source.get("RequirementId")
                )
            )
            normalized_source_ids = [
                str(source["RequirementId"])
                for source in sources
                if source.get("RequirementId")
            ]
            if raw_requirement_ids and not set(raw_requirement_ids).issubset(
                normalized_source_ids
            ):
                raise InvalidSourceError(
                    "RequirementIds must produce complete SourceRequirements lineage for "
                    f"{canonical_id}"
                )

            intents = [source.get("IntentResult") or {} for source in sources]
            if intent_result:
                intents.insert(0, intent_result)

            requirement_types = list(
                dict.fromkeys(
                    str(value)
                    for value in [
                        requirement_type,
                        *aggregate_types,
                        *SectionPlannerService._values(sources, "RequirementType"),
                    ]
                    if value is not None and str(value).strip()
                )
            )
            capability_intents = list(
                dict.fromkeys(
                    [
                        *[
                            str(value)
                            for value in _list(item.get("CapabilityIntents"))
                        ],
                        *SectionPlannerService._intent_values(
                            intents, "CapabilityIntent", "CapabilityIntents"
                        ),
                    ]
                )
            )
            evidence_sections = list(
                dict.fromkeys(
                    [
                        *[
                            str(value)
                            for value in _list(item.get("EvidenceSections"))
                        ],
                        *SectionPlannerService._intent_values(
                            intents, "EvidenceSections"
                        ),
                    ]
                )
            )
            semantic_anchors = list(
                dict.fromkeys(
                    [
                        *[
                            str(value)
                            for value in _list(item.get("SemanticAnchors"))
                        ],
                        *SectionPlannerService._intent_values(
                            intents, "SemanticAnchors"
                        ),
                    ]
                )
            )
            normalized_requirement = {
                "CanonicalRequirementId": str(canonical_id),
                "CanonicalRequirement": str(canonical_text),
                "RequirementIds": requirement_ids,
                "RequirementType": str(requirement_type) if requirement_type else "",
                "IntentResult": intent_result,
                "RequirementTypes": requirement_types,
                "MandatoryFlags": SectionPlannerService._values(
                    sources, "MandatoryFlag"
                ),
                "Priorities": SectionPlannerService._values(sources, "Priority"),
                "RequirementStrengths": SectionPlannerService._values(
                    sources, "RequirementStrength"
                ),
                "Headings": SectionPlannerService._values(sources, "Heading"),
                "CapabilityIntents": capability_intents,
                "EvidenceSections": evidence_sections,
                "SemanticAnchors": semantic_anchors,
                "SourceDocuments": _json_safe(source_documents),
                "SourceRequirements": [
                    {
                        key: _json_safe(source.get(key))
                        for key in (
                            "RequirementId",
                            "DocumentId",
                            "ChunkId",
                            "SourceMongoId",
                            "RequirementText",
                            "RequirementType",
                            "MandatoryFlag",
                            "Priority",
                            "RequirementStrength",
                            "Heading",
                            "PageNumber",
                            "Confidence",
                            "IntentResult",
                        )
                        if source.get(key) is not None
                    }
                    for source in sources
                ],
            }
            normalized_requirement.update(classify_requirement(normalized_requirement))
            normalized.append(normalized_requirement)
        return normalized

    @staticmethod
    def _log_source_summary(
        state: SectionPlannerState,
        requirements: list[dict[str, Any]],
        evaluation: dict[str, Any],
    ) -> None:
        dispositions = Counter(item["Disposition"] for item in requirements)
        response_ids = [
            item["CanonicalRequirementId"]
            for item in requirements
            if item["ResponseApplicability"] is True
        ]
        lineage_count = sum(
            bool(
                [
                    source.get("RequirementId")
                    for source in _list(item.get("SourceRequirements"))
                    if isinstance(source, dict) and source.get("RequirementId")
                ]
            )
            for item in requirements
        )
        logger.info(
            "Section Planner sources normalized | requirement_id=%s evaluation_id=%s "
            "requirements=%s response=%s non_response=%s review_required=%s "
            "submission_instructions=%s lineage=%s criteria=%s response_ids=%s",
            SectionPlannerService._record_id(state["requirement_record"]),
            SectionPlannerService._record_id(state["evaluation_record"]),
            len(requirements),
            len(response_ids),
            sum(not item["ResponseApplicability"] for item in requirements)
            - dispositions["REVIEW_REQUIRED"],
            dispositions["REVIEW_REQUIRED"],
            dispositions["SUBMISSION_INSTRUCTION"],
            lineage_count,
            len(_list(evaluation.get("Criteria"))),
            response_ids,
        )

    @staticmethod
    def _record_id(record: dict[str, Any] | None) -> str | None:
        if not record:
            return None
        raw = record.get("_id") or record.get("Id")
        return str(raw) if raw is not None else None

    @staticmethod
    def _values(items: list[dict[str, Any]], key: str) -> list[Any]:
        return list(
            dict.fromkeys(item.get(key) for item in items if item.get(key) is not None)
        )

    @staticmethod
    def _intent_values(items: list[dict[str, Any]], *keys: str) -> list[Any]:
        values = []
        for item in items:
            for key in keys:
                raw = item.get(key)
                values.extend(
                    raw if isinstance(raw, list) else ([raw] if raw is not None else [])
                )
        return list(dict.fromkeys(str(value) for value in values))

    @staticmethod
    def normalize_evaluation_criteria(state: SectionPlannerState) -> dict[str, Any]:
        output = _payload(state["evaluation_record"])
        criteria = output.get("Criteria")
        if criteria is None:
            criteria = []
        if not isinstance(criteria, list):
            raise InvalidSourceError("Evaluation Criteria.Criteria must be an array")
        normalized_criteria = []
        for item in criteria:
            if not item.get("CriterionId"):
                raise InvalidSourceError(
                    "Every evaluation criterion requires CriterionId"
                )
            normalized_item = {
                key: _json_safe(item.get(key))
                for key in (
                    "CriterionId",
                    "Name",
                    "Description",
                    "PrimaryCategory",
                    "SecondaryCategories",
                    "ParentCriterionId",
                    "QuestionReferences",
                    "WeightPercent",
                    "MaximumScore",
                    "MinimumScore",
                    "MinimumPercent",
                    "PassFail",
                    "Mandatory",
                    "PriceScoringFormula",
                    "SourceEvidence",
                )
            }
            for key in ("Name", "Description", "PrimaryCategory"):
                normalized_item[key] = str(normalized_item.get(key) or "")
            for key in (
                "SecondaryCategories",
                "QuestionReferences",
                "SourceEvidence",
            ):
                normalized_item[key] = _json_safe(_list(item.get(key)))
            normalized_criteria.append(normalized_item)
        return {
            "EvaluationModelDetected": bool(
                output.get("EvaluationModelDetected", False)
            ),
            "ExtractionStatus": str(output.get("ExtractionStatus", "")),
            "Criteria": normalized_criteria,
            "MandatoryConditions": _json_safe(_list(output.get("MandatoryConditions"))),
            "OverallScoring": _json_safe(output.get("OverallScoring") or {}),
            "Conflicts": _json_safe(_list(output.get("Conflicts"))),
            "MissingInformation": _json_safe(_list(output.get("MissingInformation"))),
            "ReviewFlags": _json_safe(_list(output.get("ReviewFlags"))),
            "RequiresHumanReview": bool(output.get("RequiresHumanReview", False)),
            "Validation": _json_safe(output.get("Validation") or {}),
            "SourceDocuments": _json_safe(_list(output.get("SourceDocuments"))),
        }

    def build_llm_context(
        self,
        prompts: PlannerPrompts,
        requirements: list[dict[str, Any]],
        evaluation: dict[str, Any],
    ) -> tuple[str, str, int]:
        instructions = (
            "[SECTION PLANNER CONSTITUTION]\n"
            f"{prompts.constitution.content}\n\n"
            "[SECTION PLANNER SPECIFICATION]\n"
            f"{prompts.specification.content}"
        )
        compact_requirements = self._compact_requirements(requirements)
        compact_evaluation = self._compact_evaluation(evaluation)

        def render() -> str:
            return (
                "[TASK]\n"
                f"{prompts.user_prompt.content}\n"
                "[REQUIREMENTS]\n"
                f"{json.dumps(compact_requirements, ensure_ascii=False, separators=(',', ':'))}\n"
                "[CRITERIA]\n"
                f"{json.dumps(compact_evaluation, ensure_ascii=False, separators=(',', ':'))}\n"
                "[RETURN]\nReturn only DynamicSectionPlannerLLMDecision."
            )

        runtime_prompt = render()
        estimated = estimate_input_tokens(
            instructions, runtime_prompt, DynamicSectionPlannerLLMDecision
        )
        optional_fields = (
            (compact_evaluation, "Description"),
            (compact_requirements, "SemanticAnchors"),
            (compact_requirements, "EvidenceSections"),
            (compact_requirements, "CapabilityIntent"),
        )
        for items, field in optional_fields:
            if estimated <= self.settings.llm_max_input_tokens:
                break
            for item in items:
                item.pop(field, None)
            runtime_prompt = render()
            estimated = estimate_input_tokens(
                instructions, runtime_prompt, DynamicSectionPlannerLLMDecision
            )
        if estimated > self.settings.llm_max_input_tokens:
            raise InvalidSourceError(
                "Compact LLM input exceeds configured token budget: "
                f"estimated={estimated}, maximum={self.settings.llm_max_input_tokens}"
            )
        logger.info(
            "Section Planner compact LLM input | response_requirements=%s criteria=%s "
            "estimated_input_tokens=%s max_input_tokens=%s",
            len(compact_requirements),
            len(compact_evaluation),
            estimated,
            self.settings.llm_max_input_tokens,
        )
        return instructions, runtime_prompt, estimated

    @staticmethod
    def _compact_text(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    @classmethod
    def _compact_values(cls, values: Any) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in _list(values):
            text = cls._compact_text(value)
            key = text.casefold()
            if text and key not in seen:
                seen.add(key)
                result.append(text)
        return result

    @classmethod
    def _compact_requirements(
        cls, requirements: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        compact: list[dict[str, Any]] = []
        for requirement in requirements:
            if requirement.get("ResponseApplicability") is not True:
                continue
            priorities = cls._compact_values(requirement.get("Priorities"))
            mandatory_values = _list(requirement.get("MandatoryFlags"))
            item: dict[str, Any] = {
                "CanonicalRequirementId": str(requirement["CanonicalRequirementId"]),
                "CanonicalRequirement": cls._compact_text(
                    requirement.get("CanonicalRequirement")
                ),
                "RequirementType": cls._compact_text(
                    requirement.get("RequirementType")
                ),
                "CapabilityIntent": cls._compact_values(
                    requirement.get("CapabilityIntents")
                ),
                "EvidenceSections": cls._compact_values(
                    requirement.get("EvidenceSections")
                ),
                "SemanticAnchors": cls._compact_values(
                    requirement.get("SemanticAnchors")
                ),
                "Mandatory": any(
                    value is True or str(value).strip().casefold() == "true"
                    for value in mandatory_values
                ),
            }
            if priorities:
                item["Priority"] = priorities[0]
            compact.append(
                {key: value for key, value in item.items() if value not in ("", [], None)}
            )
        return compact

    @classmethod
    def _compact_evaluation(cls, evaluation: dict[str, Any]) -> list[dict[str, Any]]:
        compact: list[dict[str, Any]] = []
        for criterion in _list(evaluation.get("Criteria")):
            item = {
                "CriterionId": str(criterion["CriterionId"]),
                "Name": cls._compact_text(criterion.get("Name")),
                "Description": cls._compact_text(criterion.get("Description")),
                "PrimaryCategory": cls._compact_text(
                    criterion.get("PrimaryCategory")
                ),
                "WeightPercent": criterion.get("WeightPercent"),
                "Mandatory": criterion.get("Mandatory"),
            }
            compact.append(
                {key: value for key, value in item.items() if value != ""}
            )
        return compact

    def prepare_persistence(
        self,
        state: SectionPlannerState,
        final_plan: ProposalPlan,
        result: LLMResult,
        prompts: PlannerPrompts,
        usage: dict[str, int],
        repair_attempts: int,
        requirement_count: int,
        criterion_count: int,
        estimated_input_tokens: int,
        llm_requirement_count: int,
    ) -> dict[str, Any]:
        plan = final_plan.model_dump()
        plan.update(
            {
                "Status": state["Status"],
                "IsRegenerate": state["IsRegenerate"],
                "UserId": state["UserId"],
                "UserName": state["UserName"],
                "RequirementCount": requirement_count,
                "EvaluationCriterionCount": criterion_count,
                **self._source_record_ids(state),
                "LLMMetadata": {
                    "Provider": result.provider,
                    "Model": result.model,
                    "ResponseId": result.response_id,
                    "PromptHashes": prompts.hashes,
                    "PromptFiles": {
                        "Constitution": self._prompt_audit(prompts.constitution),
                        "Specification": self._prompt_audit(prompts.specification),
                        "UserPrompt": self._prompt_audit(prompts.user_prompt),
                    },
                    "InputRequirementCount": llm_requirement_count,
                    "InputCriterionCount": criterion_count,
                    "EstimatedInputTokens": estimated_input_tokens,
                    "RequestCount": 1 + repair_attempts,
                    "RepairCallCount": repair_attempts,
                    "RepairAttempts": repair_attempts,
                    "Usage": usage,
                },
            }
        )
        return plan

    @staticmethod
    def _prompt_audit(document: Any) -> dict[str, Any]:
        return {
            "FileName": document.name,
            "SHA256": document.sha256,
            "LastModifiedAt": document.modified_at,
        }

    @staticmethod
    def _source_record_ids(state: SectionPlannerState) -> dict[str, Any]:
        return {
            "RequirementDeduplicationId": SectionPlannerService._record_id(
                state["requirement_record"]
            ),
            "EvaluationCriteriaId": SectionPlannerService._record_id(
                state["evaluation_record"]
            ),
        }

    @staticmethod
    def _add_usage(total: dict[str, int], current: dict[str, int]) -> None:
        for key in ("InputTokens", "OutputTokens", "TotalTokens"):
            total[key] = total.get(key, 0) + current.get(key, 0)

    @staticmethod
    def _node_counts(plan: ProposalPlan) -> tuple[int, int]:
        sections = sum(len(group.Sections) for group in plan.ProposalGroups)
        subsections = sum(
            len(section.SubSections)
            for group in plan.ProposalGroups
            for section in group.Sections
        )
        return sections, subsections

    def persist_plan(
        self, document: dict[str, Any], regenerate: bool
    ) -> dict[str, Any]:
        try:
            return self.repository.save_plan(document, regenerate)
        except Exception as exc:
            raise PersistenceError("Unable to persist Tender Section Plan") from exc
