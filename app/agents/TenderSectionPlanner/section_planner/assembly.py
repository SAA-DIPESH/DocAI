from __future__ import annotations

import json
import uuid
from collections import Counter
from typing import Any

from .models import (
    EvaluationCriterion,
    EvaluationCriterionMapping,
    EvaluationSummary,
    EvidenceRequirementTrigger,
    ProposalGroup,
    ProposalPlan,
    RequirementMapping,
    RequirementPlanningDisposition,
    RequirementNodeMapping,
    SectionNode,
    SectionPlannerLLMDecision,
    Traceability,
    ValidationResult,
)


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dedupe(values: list[Any]) -> tuple[list[Any], bool]:
    result: list[Any] = []
    seen: set[str] = set()
    duplicate = False
    for value in values:
        key = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
        if key in seen:
            duplicate = True
            continue
        seen.add(key)
        result.append(value)
    return result, duplicate


def _node_id(node: dict[str, Any], subsection: bool = False) -> str:
    value = node.get("SubSectionId") if subsection else node.get("SectionId")
    if subsection and not value:
        value = node.get("SectionId")
    return str(value or "")


def build_allowed_node_catalogue(configuration: dict[str, Any]) -> list[dict[str, Any]]:
    catalogue: list[dict[str, Any]] = []
    for group_index, group in enumerate(_list(configuration.get("Groups"))):
        group_id = str(group.get("GroupId") or "")
        for section_index, section in enumerate(_list(group.get("Sections"))):
            section_id = _node_id(section)
            catalogue.append(
                {
                    "NodeId": section_id,
                    "NodeType": "Section",
                    "NodeName": str(section.get("SectionName") or ""),
                    "ParentGroupId": group_id,
                    "ParentSectionId": None,
                    "GroupOrder": group.get("Order", group_index),
                    "NodeOrder": section.get("Order", section_index),
                    "Dependencies": [
                        str(x) for x in _list(section.get("Dependencies"))
                    ],
                    "PermittedRequirementTypes": [
                        str(x) for x in _list(section.get("RequirementTypes"))
                    ],
                }
            )
            for subsection_index, subsection in enumerate(
                _list(section.get("SubSections"))
            ):
                catalogue.append(
                    {
                        "NodeId": _node_id(subsection, subsection=True),
                        "NodeType": "SubSection",
                        "NodeName": str(
                            subsection.get("SubSectionName")
                            or subsection.get("SectionName")
                            or ""
                        ),
                        "ParentGroupId": group_id,
                        "ParentSectionId": section_id,
                        "GroupOrder": group.get("Order", group_index),
                        "NodeOrder": subsection.get("Order", subsection_index),
                        "Dependencies": [
                            str(x) for x in _list(subsection.get("Dependencies"))
                        ],
                        "PermittedRequirementTypes": [
                            str(x) for x in _list(subsection.get("RequirementTypes"))
                        ],
                    }
                )
    return catalogue


class ProposalPlanAssembler:
    """Build a ProposalPlan only from configured nodes and canonical requirements."""


    def validate_decisions(
        self,
        decision: SectionPlannerLLMDecision,
        configuration: dict[str, Any],
        requirements: list[dict[str, Any]],
        evaluation: dict[str, Any],
    ) -> list[str]:
        issues: list[str] = []

        catalogue = build_allowed_node_catalogue(configuration)

        nodes = {item["NodeId"]: item for item in catalogue}

        requirement_by_id = {item["CanonicalRequirementId"]: item for item in requirements}

        requirement_ids = set(requirement_by_id)

        response_ids = {
            item["CanonicalRequirementId"]
            for item in requirements
            if item.get("ResponseApplicability") is True
        }

        criteria_by_id = {
            str(item["CriterionId"]): item for item in _list(evaluation.get("Criteria"))
        }

        criterion_ids = set(criteria_by_id)

        mapping_node_ids = [item.NodeId for item in decision.Mappings]

        duplicate_nodes = sorted(
            item for item, count in Counter(mapping_node_ids).items() if count > 1
        )

        if duplicate_nodes:
            issues.append(f"Duplicate node mappings: {duplicate_nodes}")

        requirement_owners: list[str] = []
        criterion_owners: list[str] = []
        active_section_ids: set[str] = set()

        for mapping in decision.Mappings:
            node = nodes.get(mapping.NodeId)

            if node is None:
                issues.append(
                    "NodeId is not in ALLOWED NODE CATALOGUE: " f"{mapping.NodeId}"
                )
                continue

            if not mapping.CanonicalRequirementIds:
                issues.append("Mapping has no canonical requirement: " f"{mapping.NodeId}")

            unknown_requirements = set(mapping.CanonicalRequirementIds) - requirement_ids

            if unknown_requirements:
                issues.append(
                    "Invented CanonicalRequirementIds in "
                    f"{mapping.NodeId}: "
                    f"{sorted(unknown_requirements)}"
                )

            non_response = (
                set(mapping.CanonicalRequirementIds) & requirement_ids
            ) - response_ids

            if non_response:
                issues.append(
                    "Non-response requirements cannot map to "
                    f"{mapping.NodeId}: "
                    f"{sorted(non_response)}"
                )

            unknown_criteria = set(mapping.EvaluationCriterionIds) - criterion_ids

            if unknown_criteria:
                issues.append(
                    f"Invented CriterionIds in {mapping.NodeId}: "
                    f"{sorted(unknown_criteria)}"
                )

            invalid_type_requirement_ids = self._validate_requirement_types(
                issues,
                mapping,
                node,
                requirement_by_id,
            )

            valid_owned_requirement_ids = [
                requirement_id
                for requirement_id in mapping.CanonicalRequirementIds
                if requirement_id in response_ids
                and requirement_id not in invalid_type_requirement_ids
            ]

            requirement_owners.extend(valid_owned_requirement_ids)

            # Evaluation criteria cannot activate a node
            # without a valid requirement-backed mapping.
            if valid_owned_requirement_ids:
                criterion_owners.extend(
                    criterion_id
                    for criterion_id in mapping.EvaluationCriterionIds
                    if criterion_id in criterion_ids
                )

                self._validate_social_value_mapping(
                    issues,
                    mapping,
                    node,
                    criteria_by_id,
                )

                active_section_ids.add(str(node.get("ParentSectionId") or node["NodeId"]))

        duplicate_requirements = sorted(
            item for item, count in Counter(requirement_owners).items() if count > 1
        )

        if duplicate_requirements:
            issues.append(
                "Canonical requirements have multiple direct "
                f"owners: {duplicate_requirements}"
            )

        duplicate_criteria = sorted(
            item for item, count in Counter(criterion_owners).items() if count > 1
        )

        if duplicate_criteria:
            issues.append(
                "Evaluation criteria have multiple owners: " f"{duplicate_criteria}"
            )

        owned = set(requirement_owners)

        unknown_unmapped = set(decision.UnmappedCanonicalRequirementIds) - response_ids

        if unknown_unmapped:
            issues.append(
                "Unknown UnmappedCanonicalRequirementIds: " f"{sorted(unknown_unmapped)}"
            )

        if owned & set(decision.UnmappedCanonicalRequirementIds):
            issues.append("A canonical requirement cannot be both " "mapped and unmapped")

        expected_unmapped = response_ids - owned

        if set(decision.UnmappedCanonicalRequirementIds) != expected_unmapped:
            issues.append(
                "UnmappedCanonicalRequirementIds must exactly "
                "list response-applicable requirements without "
                "an owner"
            )

        configured_sections = {
            item["NodeId"]: item for item in catalogue if item["NodeType"] == "Section"
        }

        for section_id in active_section_ids:
            section = configured_sections.get(section_id)

            if not section:
                continue

            for dependency in section["Dependencies"]:
                if dependency not in active_section_ids:
                    issues.append(
                        f"Mapped section {section_id} has "
                        f"inactive dependency {dependency}"
                    )

        return list(dict.fromkeys(issues))


    @staticmethod
    def _validate_requirement_types(
        issues: list[str],
        mapping: RequirementNodeMapping,
        node: dict[str, Any],
        requirement_by_id: dict[
        str,
        dict[str, Any],
    ],
    ) -> set[str]:
        permitted = {
            str(value).strip().casefold()
            for value in node["PermittedRequirementTypes"]
            if value is not None and str(value).strip()
        }

        invalid_requirement_ids: set[str] = set()

        # Empty permitted list means unrestricted node.
        if not permitted:
            return invalid_requirement_ids

        for requirement_id in mapping.CanonicalRequirementIds:
            requirement = requirement_by_id.get(requirement_id)

            if requirement is None:
                continue

            actual_values = [
                requirement.get("RequirementType"),
                *_list(requirement.get("RequirementTypes")),
            ]

            actual = {
                str(value).strip().casefold()
                for value in actual_values
                if value is not None and str(value).strip()
            }

            if actual and not actual.intersection(permitted):
                invalid_requirement_ids.add(requirement_id)

                issues.append(
                    f"Requirement {requirement_id} type "
                    f"is not permitted for node "
                    f"{mapping.NodeId}"
                )

        return invalid_requirement_ids

    @staticmethod
    def _validate_social_value_mapping(
        issues: list[str],
    mapping: RequirementNodeMapping,
    node: dict[str, Any],
    criteria_by_id: dict[str, dict[str, Any]],
    ) -> None:
        for criterion_id in mapping.EvaluationCriterionIds:
            criterion = criteria_by_id.get(criterion_id)
            if not criterion:
                continue
            criterion_text = " ".join(
                str(criterion.get(key) or "")
                for key in ("Name", "Description", "PrimaryCategory")
            ).casefold()
            node_text = " ".join(
                [node.get("NodeName", ""), *node.get("PermittedRequirementTypes", [])]
            ).casefold()
            if "social value" in criterion_text and "social value" not in node_text:
                issues.append(
                    f"Social Value criterion must not map to unrelated node {mapping.NodeId}"
                )

    def assemble(
        self,
        decision: SectionPlannerLLMDecision,
        configuration: dict[str, Any],
        requirements: list[dict[str, Any]],
        evaluation: dict[str, Any],
        *,
        company_id: str,
        tender_id: str,
        project_id: str,
    ) -> ProposalPlan:
        mapping_by_node = {item.NodeId: item for item in decision.Mappings}
        requirements_by_id = {
            item["CanonicalRequirementId"]: item for item in requirements
        }
        response_ids = {
            item["CanonicalRequirementId"]
            for item in requirements
            if item.get("ResponseApplicability") is True
        }
        warnings: list[str] = []
        information: list[str] = []
        criteria_by_id: dict[str, dict[str, Any]] = {}
        for source_criterion in _list(evaluation.get("Criteria")):
            criterion = dict(source_criterion)
            evidence, duplicate = _dedupe(_list(criterion.get("SourceEvidence")))
            criterion["SourceEvidence"] = evidence
            criterion_id = str(criterion["CriterionId"])
            criteria_by_id[criterion_id] = criterion
            if duplicate:
                warnings.append(
                    f"Duplicate SourceEvidence normalized for criterion {criterion_id}"
                )

        owner_locations: dict[str, tuple[str, str | None]] = {}
        criterion_locations: list[tuple[str, str, str | None]] = []
        evidence_triggers: list[EvidenceRequirementTrigger] = []
        case_study_triggers: list[EvidenceRequirementTrigger] = []
        groups: list[ProposalGroup] = []
        used_node_ids: set[str] = set()

        for group_index, group in enumerate(_list(configuration.get("Groups"))):
            group_id = str(group.get("GroupId") or "")
            sections: list[SectionNode] = []
            for section in _list(group.get("Sections")):
                section_id = _node_id(section)
                section_mapping = mapping_by_node.get(section_id)
                direct_requirement_ids = self._valid_mapping_requirements(
                    section_mapping, response_ids
                )
                direct_criterion_ids = self._valid_mapping_criteria(
                    section_mapping, criteria_by_id
                )
                subsections: list[SectionNode] = []
                for subsection in _list(section.get("SubSections")):
                    subsection_id = _node_id(subsection, subsection=True)
                    subsection_mapping = mapping_by_node.get(subsection_id)
                    subsection_requirement_ids = self._valid_mapping_requirements(
                        subsection_mapping, response_ids
                    )
                    if not subsection_requirement_ids:
                        continue
                    subsection_criterion_ids = self._valid_mapping_criteria(
                        subsection_mapping, criteria_by_id
                    )
                    subsection_node, evidence, cases = self._source_node(
                        subsection,
                        subsection_requirement_ids,
                        subsection_criterion_ids,
                        requirements_by_id,
                        criteria_by_id,
                        subsection=True,
                        section_id=section_id,
                    )
                    subsections.append(subsection_node)
                    used_node_ids.add(subsection_id)
                    evidence_triggers.extend(evidence)
                    case_study_triggers.extend(cases)
                    for requirement_id in subsection_requirement_ids:
                        owner_locations[requirement_id] = (section_id, subsection_id)
                    criterion_locations.extend(
                        (criterion_id, section_id, subsection_id)
                        for criterion_id in subsection_criterion_ids
                    )

                aggregate_requirement_ids = list(
                    dict.fromkeys(
                        direct_requirement_ids
                        + [
                            requirement_id
                            for subsection in subsections
                            for requirement_id in subsection.RequirementIds
                        ]
                    )
                )
                if not aggregate_requirement_ids:
                    continue
                section_node, evidence, cases = self._source_node(
                    section,
                    aggregate_requirement_ids,
                    direct_criterion_ids,
                    requirements_by_id,
                    criteria_by_id,
                    section_id=section_id,
                    subsections=subsections,
                )
                sections.append(section_node)
                used_node_ids.add(section_id)
                evidence_triggers.extend(evidence)
                case_study_triggers.extend(cases)
                for requirement_id in direct_requirement_ids:
                    owner_locations[requirement_id] = (section_id, None)
                criterion_locations.extend(
                    (criterion_id, section_id, None)
                    for criterion_id in direct_criterion_ids
                )
            if sections:
                groups.append(
                    ProposalGroup(
                        GroupId=group_id,
                        GroupName=str(group.get("GroupName") or ""),
                        Order=int(group.get("Order", group_index) or 0),
                        Sections=sections,
                    )
                )

        requirement_mappings = [
            self._requirement_mapping(
                requirements_by_id[requirement_id], location, warnings
            )
            for requirement_id, location in owner_locations.items()
        ]
        criterion_mappings = [
            EvaluationCriterionMapping(
                CriterionId=criterion_id,
                SectionId=section_id,
                SubSectionId=subsection_id,
                SourceEvidence=_list(
                    criteria_by_id[criterion_id].get("SourceEvidence")
                ),
            )
            for criterion_id, section_id, subsection_id in criterion_locations
        ]
        dispositions = [
            self._planning_disposition(requirement, warnings)
            for requirement in requirements
        ]
        non_response = [
            item
            for item in dispositions
            if not item.ResponseApplicability and item.Disposition != "REVIEW_REQUIRED"
        ]

        review_required_dispositions = [
            item for item in dispositions if item.Disposition == "REVIEW_REQUIRED"
        ]

        review_required_ids = {
            item.CanonicalRequirementId for item in review_required_dispositions
        }
        non_response_ids = {item.CanonicalRequirementId for item in non_response}
        mapped_requirement_ids = set(owner_locations)
        mapped_criterion_ids = {item[0] for item in criterion_locations}
        requirement_ids = set(requirements_by_id)
        criterion_ids = set(criteria_by_id)
        unmapped_response_ids = response_ids - mapped_requirement_ids
        unresolved_requirement_ids = unmapped_response_ids | review_required_ids
        unmapped_criterion_ids = criterion_ids - mapped_criterion_ids

        blocking_issues: list[str] = []
        if unmapped_response_ids:
            blocking_issues.append(
                "Response-applicable requirements lack a proposal owner: "
                f"{sorted(unmapped_response_ids)}"
            )
        if unmapped_criterion_ids:
            blocking_issues.append(
                f"Evaluation criteria remain unmapped because no requirement-backed node "
                f"is available: {sorted(unmapped_criterion_ids)}"
            )
        if evaluation.get("Conflicts"):
            blocking_issues.append(
                "Unresolved evaluation conflicts require human review"
            )
        if evaluation.get("MissingInformation"):
            blocking_issues.append("Material evaluation information is missing")
        if review_required_ids:
            blocking_issues.append(
                "Requirement dispositions require human review: "
                f"{sorted(review_required_ids)}"
            )

        catalogue = build_allowed_node_catalogue(configuration)
        information.extend(
            f"Configured node unused because no canonical requirement applies: {item['NodeId']}"
            for item in catalogue
            if item["NodeId"] not in used_node_ids
        )
        source_coverage_valid = (
            not review_required_ids
            and requirement_ids == mapped_requirement_ids | non_response_ids
        )
        proposal_coverage_valid = response_ids == mapped_requirement_ids
        blocking_issues = list(dict.fromkeys(blocking_issues))
        warnings = list(dict.fromkeys(warnings))
        information = list(dict.fromkeys(information))
        review_required = bool(
            blocking_issues
            or evaluation.get("ReviewFlags")
            or evaluation.get("RequiresHumanReview")
        )
        deduped_evidence, _ = _dedupe([item.model_dump() for item in evidence_triggers])
        deduped_cases, _ = _dedupe([item.model_dump() for item in case_study_triggers])
        return ProposalPlan(
            ProposalPlanId=str(uuid.uuid4()),
            CompanyId=company_id,
            TenderId=tender_id,
            ProjectId=project_id,
            Sector=str(configuration.get("Sector") or ""),
            PlanStatus="ValidationRequired" if review_required else "Generated",
            ProposalGroups=groups,
            MappedRequirementIds=[
                item for item in requirements_by_id if item in mapped_requirement_ids
            ],
            UnmappedRequirementIds=[
                item for item in requirements_by_id if item in unresolved_requirement_ids
            ],
            MappedEvaluationCriterionIds=[
                item for item in criteria_by_id if item in mapped_criterion_ids
            ],
            UnmappedEvaluationCriterionIds=[
                item for item in criteria_by_id if item in unmapped_criterion_ids
            ],
            RequirementDispositions=dispositions,
            NonResponseRequirements=non_response,
            ReviewRequiredRequirements=review_required_dispositions,
            EvaluationSummary=self._evaluation_summary(evaluation),
            Traceability=Traceability(
                RequirementMappings=requirement_mappings,
                EvaluationCriterionMappings=criterion_mappings,
                EvidenceRequirementTriggers=[
                    EvidenceRequirementTrigger.model_validate(item)
                    for item in deduped_evidence
                ],
                CaseStudyTriggers=[
                    EvidenceRequirementTrigger.model_validate(item)
                    for item in deduped_cases
                ],
            ),
            Validation=ValidationResult(
                RequirementCoverageValid=proposal_coverage_valid,
                EvaluationCriteriaCoverageValid=criterion_ids == mapped_criterion_ids,
                HierarchyValid=True,
                DependencyValid=True,
                NoEmptySections=True,
                NoUnsupportedWeights=True,
                Issues=blocking_issues + warnings + information,
                SourceRequirementCoverageValid=source_coverage_valid,
                ProposalRequirementCoverageValid=proposal_coverage_valid,
                BlockingIssues=blocking_issues,
                Warnings=warnings,
                Information=information,
            ),
        )

    @staticmethod
    def _valid_mapping_requirements(
        mapping: RequirementNodeMapping | None, response_ids: set[str]
    ) -> list[str]:
        if not mapping:
            return []
        return list(
            dict.fromkeys(
                item for item in mapping.CanonicalRequirementIds if item in response_ids
            )
        )

    @staticmethod
    def _valid_mapping_criteria(
        mapping: RequirementNodeMapping | None,
        criteria_by_id: dict[str, dict[str, Any]],
    ) -> list[str]:
        if not mapping or not mapping.CanonicalRequirementIds:
            return []
        return list(
            dict.fromkeys(
                item
                for item in mapping.EvaluationCriterionIds
                if item in criteria_by_id
            )
        )

    def _source_node(
        self,
        configured: dict[str, Any],
        requirement_ids: list[str],
        criterion_ids: list[str],
        requirements_by_id: dict[str, dict[str, Any]],
        criteria_by_id: dict[str, dict[str, Any]],
        *,
        section_id: str,
        subsection: bool = False,
        subsections: list[SectionNode] | None = None,
    ) -> tuple[
        SectionNode,
        list[EvidenceRequirementTrigger],
        list[EvidenceRequirementTrigger],
    ]:
        node_id = _node_id(configured, subsection=subsection)
        node = SectionNode(
            SectionId=node_id,
            SectionName=str(
                configured.get("SubSectionName") or configured.get("SectionName") or ""
            ),
            SectionDescription=self._source_description(
                configured, requirement_ids, requirements_by_id
            ),
            Required=True,
            Priority=self._source_priority(
                configured, requirement_ids, requirements_by_id
            ),
            RequirementIds=requirement_ids,
            EvaluationCriteria=self._criteria(criterion_ids, criteria_by_id),
            SubSections=subsections or [],
            EvidenceRequired=False,
            CaseStudyRequired=False,
            Dependencies=[str(x) for x in _list(configured.get("Dependencies"))],
            AutoCreated=False,
            AutoCreatedReason=None,
        )
        evidence, cases = self._source_triggers(
            requirement_ids,
            criterion_ids,
            requirements_by_id,
            criteria_by_id,
            section_id,
            node_id if subsection else None,
        )
        node.EvidenceRequired = bool(evidence)
        node.CaseStudyRequired = bool(cases)
        return node, evidence, cases

    @staticmethod
    def _source_description(
        configured: dict[str, Any],
        requirement_ids: list[str],
        requirements_by_id: dict[str, dict[str, Any]],
    ) -> str:
        configured_description = str(configured.get("SectionDescription") or "").strip()
        if configured_description:
            return configured_description
        source_texts = [
            str(requirements_by_id[item].get("CanonicalRequirement") or "").strip()
            for item in requirement_ids
            if item in requirements_by_id
        ]
        return "; ".join(item for item in source_texts if item)

    @staticmethod
    def _source_priority(
        configured: dict[str, Any],
        requirement_ids: list[str],
        requirements_by_id: dict[str, dict[str, Any]],
    ) -> str:
        source_priorities = [
            str(priority).casefold()
            for requirement_id in requirement_ids
            for priority in _list(requirements_by_id[requirement_id].get("Priorities"))
            if requirement_id in requirements_by_id
        ]
        for value in ("high", "medium", "low"):
            if value in source_priorities:
                return value.title()
        weight = configured.get("PriorityWeight")
        if isinstance(weight, (int, float)):
            if weight >= 13:
                return "High"
            if weight >= 8:
                return "Medium"
            return "Low"
        return "Unknown"

    @staticmethod
    def _criteria(
        ids: list[str], criteria_by_id: dict[str, dict[str, Any]]
    ) -> list[EvaluationCriterion]:
        return [
            EvaluationCriterion.model_validate(criteria_by_id[item])
            for item in ids
            if item in criteria_by_id
        ]

    @staticmethod
    def _source_triggers(
        requirement_ids: list[str],
        criterion_ids: list[str],
        requirements_by_id: dict[str, dict[str, Any]],
        criteria_by_id: dict[str, dict[str, Any]],
        section_id: str,
        subsection_id: str | None,
    ) -> tuple[list[EvidenceRequirementTrigger], list[EvidenceRequirementTrigger]]:
        evidence_terms = (
            "evidence",
            "proof",
            "demonstrate",
            "assurance",
            "certification",
            "certificate",
            "completed price schedule",
            "supporting document",
        )
        case_terms = (
            "case study",
            "case studies",
            "previous example",
            "comparable delivery",
            "references",
            "prior experience",
            "lessons learned",
        )
        sources: list[tuple[str, str, str]] = []
        for requirement_id in requirement_ids:
            requirement = requirements_by_id.get(requirement_id)
            if not requirement:
                continue
            text = " ".join(
                [
                    str(requirement.get("CanonicalRequirement") or ""),
                    *[str(x) for x in _list(requirement.get("EvidenceSections"))],
                    *[
                        str(item.get("RequirementText") or "")
                        for item in _list(requirement.get("SourceRequirements"))
                        if isinstance(item, dict)
                    ],
                ]
            )
            sources.append(("Requirement", requirement_id, text))
        for criterion_id in criterion_ids:
            criterion = criteria_by_id.get(criterion_id)
            if not criterion:
                continue
            text = " ".join(
                [
                    str(criterion.get("Name") or ""),
                    str(criterion.get("Description") or ""),
                    *[str(x) for x in _list(criterion.get("QuestionReferences"))],
                ]
            )
            sources.append(("EvaluationCriterion", criterion_id, text))

        def matches(terms: tuple[str, ...]) -> list[EvidenceRequirementTrigger]:
            result: list[EvidenceRequirementTrigger] = []
            for source_type, source_id, source_text in sources:
                lowered = source_text.casefold()
                trigger = next((item for item in terms if item in lowered), None)
                if trigger:
                    result.append(
                        EvidenceRequirementTrigger(
                            SectionId=section_id,
                            SubSectionId=subsection_id,
                            SourceType=source_type,
                            SourceId=source_id,
                            Trigger=trigger,
                            SourceText=source_text,
                        )
                    )
            return result

        return matches(evidence_terms), matches(case_terms)

    @staticmethod
    def _requirement_mapping(
        requirement: dict[str, Any],
        location: tuple[str, str | None],
        warnings: list[str],
    ) -> RequirementMapping:
        sources = _list(requirement.get("SourceRequirements"))
        source_documents = _list(requirement.get("SourceDocuments"))

        source_requirement_ids, duplicate_requirements = _dedupe(
            [
                str(item.get("RequirementId"))
                for item in sources
                if isinstance(item, dict) and item.get("RequirementId")
            ]
            + [str(item) for item in _list(requirement.get("RequirementIds")) if item]
        )

        source_document_ids, duplicate_documents = _dedupe(
            [
                str(item.get("DocumentId"))
                for item in sources
                if isinstance(item, dict) and item.get("DocumentId")
            ]
            + [
                str(item.get("DocumentId") if isinstance(item, dict) else item)
                for item in source_documents
                if item
            ]
        )

        source_chunk_ids, duplicate_chunks = _dedupe(
            [
                str(item.get("ChunkId"))
                for item in sources
                if isinstance(item, dict) and item.get("ChunkId")
            ]
        )

        if duplicate_requirements or duplicate_documents or duplicate_chunks:
            warnings.append(
                "Duplicate lineage IDs normalized for requirement "
                f"{requirement['CanonicalRequirementId']}"
            )

        return RequirementMapping(
            CanonicalRequirementId=requirement["CanonicalRequirementId"],
            CanonicalRequirement=requirement["CanonicalRequirement"],
            SourceRequirementIds=source_requirement_ids,
            SourceDocumentIds=source_document_ids,
            SourceChunkIds=source_chunk_ids,
            SectionId=location[0],
            SubSectionId=location[1],
        )

    @staticmethod
    def _planning_disposition(
        requirement: dict[str, Any],
        warnings: list[str],
    ) -> RequirementPlanningDisposition:
        sources = _list(requirement.get("SourceRequirements"))

        source_requirements, duplicate_requirements = _dedupe(
            [
                str(item.get("RequirementId"))
                for item in sources
                if isinstance(item, dict) and item.get("RequirementId")
            ]
            + [str(item) for item in _list(requirement.get("RequirementIds")) if item]
        )

        source_documents, duplicate_documents = _dedupe(
            [
                str(item.get("DocumentId"))
                for item in sources
                if isinstance(item, dict) and item.get("DocumentId")
            ]
            + [
                str(item.get("DocumentId") if isinstance(item, dict) else item)
                for item in _list(requirement.get("SourceDocuments"))
                if item
            ]
        )

        if duplicate_requirements or duplicate_documents:
            warnings.append(
                "Duplicate disposition lineage normalized for requirement "
                f"{requirement['CanonicalRequirementId']}"
            )

        return RequirementPlanningDisposition(
            CanonicalRequirementId=requirement["CanonicalRequirementId"],
            Disposition=requirement["Disposition"],
            ResponseApplicability=bool(requirement["ResponseApplicability"]),
            Reason=str(requirement["DispositionReason"]),
            Confidence=float(requirement["DispositionConfidence"]),
            SourceRequirementIds=source_requirements,
            SourceDocumentIds=source_documents,
        )

    @staticmethod
    def _evaluation_summary(evaluation: dict[str, Any]) -> EvaluationSummary:
        return EvaluationSummary.model_validate(
            {
                key: evaluation.get(key)
                for key in (
                    "EvaluationModelDetected",
                    "ExtractionStatus",
                    "Criteria",
                    "OverallScoring",
                    "MandatoryConditions",
                    "Conflicts",
                    "MissingInformation",
                    "ReviewFlags",
                    "RequiresHumanReview",
                    "SourceDocuments",
                )
            }
        )
