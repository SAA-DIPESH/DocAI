from __future__ import annotations

from collections import Counter
from typing import Any

from .models import ProposalPlan


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


class PlanValidator:
    def validate(
        self,
        plan: ProposalPlan,
        configuration: dict[str, Any],
        requirements: list[dict[str, Any]],
        evaluation: dict[str, Any],
        company_id: str,
        tender_id: str,
    ) -> list[str]:
        issues: list[str] = []
        if plan.CompanyId != company_id or plan.TenderId != tender_id:
            issues.append("Plan CompanyId or TenderId does not match the request")
        requirement_ids = {item["CanonicalRequirementId"] for item in requirements}
        response_requirement_ids = {
            item["CanonicalRequirementId"]
            for item in requirements
            if item.get("ResponseApplicability") is True
        }
        criteria = {item["CriterionId"]: item for item in _list(evaluation.get("Criteria"))}
        criterion_ids = set(criteria)
        nodes = list(self._nodes(plan))
        section_ids = {
            section.SectionId for group in plan.ProposalGroups for section in group.Sections
        }
        configured = self._configured_ids(configuration)
        configured_groups, configured_sections, configured_subsections = self._configuration_maps(
            configuration
        )

        seen_groups: set[str] = set()
        for group in plan.ProposalGroups:
            if group.GroupId in seen_groups:
                issues.append(f"Duplicate GroupId: {group.GroupId}")
            seen_groups.add(group.GroupId)
            source_group = configured_groups.get(group.GroupId)
            if source_group is None:
                issues.append(f"Group is outside the configured hierarchy: {group.GroupId}")
                continue
            if group.GroupName != str(source_group.get("GroupName") or ""):
                issues.append(f"Configured GroupName was modified: {group.GroupId}")
            if group.Order != int(source_group.get("Order", 0) or 0):
                issues.append(f"Configured group order was modified: {group.GroupId}")
            if not group.Sections:
                issues.append(f"Empty proposal group: {group.GroupId}")
            for section in group.Sections:
                source_section = configured_sections.get(section.SectionId)
                if source_section is not None:
                    configured_group_id, raw_section = source_section
                    if configured_group_id != group.GroupId:
                        issues.append(f"Section has wrong parent group: {section.SectionId}")
                    if section.SectionName != str(raw_section.get("SectionName") or ""):
                        issues.append(f"Configured SectionName was modified: {section.SectionId}")
                    expected_dependencies = [
                        str(item) for item in _list(raw_section.get("Dependencies"))
                    ]
                    if section.Dependencies != expected_dependencies:
                        issues.append(
                            f"Configured dependencies were modified: {section.SectionId}"
                        )
                for subsection in section.SubSections:
                    source_subsection = configured_subsections.get(subsection.SectionId)
                    if source_subsection is None:
                        issues.append(
                            "Subsection is outside the configured hierarchy: "
                            f"{subsection.SectionId}"
                        )
                        continue
                    parent_section_id, raw_subsection = source_subsection
                    if parent_section_id != section.SectionId:
                        issues.append(
                            f"Subsection has wrong parent section: {subsection.SectionId}"
                        )
                    expected_name = str(
                        raw_subsection.get("SubSectionName")
                        or raw_subsection.get("SectionName")
                        or ""
                    )
                    if subsection.SectionName != expected_name:
                        issues.append(
                            f"Configured SubSectionName was modified: {subsection.SectionId}"
                        )

        for _, node, is_subsection in nodes:
            label = "subsection" if is_subsection else "section"
            if not node.RequirementIds:
                issues.append(f"Requirement-empty {label}: {node.SectionId}")
            unknown = set(node.RequirementIds) - requirement_ids
            if unknown:
                issues.append(f"Invented requirement IDs in {node.SectionId}: {sorted(unknown)}")
            non_response = set(node.RequirementIds) - response_requirement_ids
            if non_response:
                issues.append(
                    f"Non-response requirement IDs in {node.SectionId}: "
                    f"{sorted(non_response)}"
                )
            if node.SectionId not in configured:
                issues.append(f"Section is outside the configured hierarchy: {node.SectionId}")
            if node.AutoCreated or node.AutoCreatedReason is not None:
                issues.append(f"Auto-created nodes are forbidden: {node.SectionId}")
            for dependency in node.Dependencies:
                if dependency not in section_ids:
                    issues.append(f"Unsatisfied dependency for {node.SectionId}: {dependency}")
            for criterion in node.EvaluationCriteria:
                source = criteria.get(criterion.CriterionId)
                if source is None:
                    issues.append(f"Invented criterion ID: {criterion.CriterionId}")
                    continue
                source_weight = source.get("WeightPercent")
                if type(criterion.WeightPercent) is not type(source_weight) or criterion.WeightPercent != source_weight:
                    issues.append(f"Unsupported weight for criterion {criterion.CriterionId}")

        trace = plan.Traceability.model_dump()
        requirement_mappings = _list(trace.get("RequirementMappings"))
        mapped_trace_ids = [str(item.get("CanonicalRequirementId", "")) for item in requirement_mappings]
        duplicates = sorted(item for item, count in Counter(mapped_trace_ids).items() if count > 1)
        if duplicates:
            issues.append(f"Requirements have multiple direct owners: {duplicates}")
        unknown_trace = set(mapped_trace_ids) - requirement_ids
        if unknown_trace:
            issues.append(f"Traceability contains invented requirement IDs: {sorted(unknown_trace)}")
        missing_owners = response_requirement_ids - set(mapped_trace_ids)
        undeclared_missing_owners = missing_owners - set(plan.UnmappedRequirementIds)
        if undeclared_missing_owners:
            issues.append(
                "Response-applicable requirements lack a declared owner or unmapped "
                f"disposition: {sorted(undeclared_missing_owners)}"
            )
        mapped_non_response = set(mapped_trace_ids) - response_requirement_ids
        if mapped_non_response:
            issues.append(
                f"Non-response requirements have proposal owners: {sorted(mapped_non_response)}"
            )
        valid_node_pairs = {
            (section.SectionId, subsection.SectionId if subsection else None)
            for _, section, subsection in self._owner_pairs(plan)
        }
        for mapping in requirement_mappings:
            pair = (mapping.get("SectionId"), mapping.get("SubSectionId"))
            if pair not in valid_node_pairs:
                issues.append(f"Requirement traceability points to an unknown owner: {pair}")

        criterion_mappings = _list(trace.get("EvaluationCriterionMappings"))
        mapped_criterion_ids = [str(item.get("CriterionId", "")) for item in criterion_mappings]
        duplicate_criterion_mappings = sorted(
            item
            for item, count in Counter(mapped_criterion_ids).items()
            if count > 1
        )
        if duplicate_criterion_mappings:
            issues.append(
                "Evaluation criteria have multiple owners: "
                f"{duplicate_criterion_mappings}"
            )
        if set(mapped_criterion_ids) - criterion_ids:
            issues.append("Evaluation traceability contains invented criterion IDs")
        criterion_pairs = {
            (
                section.SectionId,
                subsection.SectionId if subsection else None,
                criterion.CriterionId,
            )
            for _, section, subsection in self._owner_pairs(plan)
            for criterion in (subsection or section).EvaluationCriteria
        }
        for mapping in criterion_mappings:
            triple = (
                mapping.get("SectionId"),
                mapping.get("SubSectionId"),
                mapping.get("CriterionId"),
            )
            if triple not in criterion_pairs:
                issues.append(
                    "Evaluation traceability points to a criterion that is not "
                    f"hydrated on its requirement-backed owner: {triple}"
                )
        if set(plan.MappedRequirementIds) != set(mapped_trace_ids):
            issues.append("MappedRequirementIds does not match requirement traceability")
        review_required_ids = {
            item.CanonicalRequirementId
            for item in plan.RequirementDispositions
            if item.Disposition == "REVIEW_REQUIRED"
        }
        expected_unmapped_ids = (
            response_requirement_ids - set(mapped_trace_ids)
        ) | review_required_ids
        if set(plan.UnmappedRequirementIds) != expected_unmapped_ids:
            issues.append("UnmappedRequirementIds is inconsistent")
        if set(plan.MappedEvaluationCriterionIds) != set(mapped_criterion_ids):
            issues.append("MappedEvaluationCriterionIds does not match evaluation traceability")
        if set(plan.UnmappedEvaluationCriterionIds) != criterion_ids - set(mapped_criterion_ids):
            issues.append("UnmappedEvaluationCriterionIds is inconsistent")

        disposition_ids = [item.CanonicalRequirementId for item in plan.RequirementDispositions]
        if Counter(disposition_ids) != Counter(requirement_ids):
            issues.append("Every canonical requirement must have exactly one planning disposition")
 
 
        expected_non_response = {
            item.CanonicalRequirementId
            for item in plan.RequirementDispositions
            if not item.ResponseApplicability
            and item.Disposition != "REVIEW_REQUIRED"
        }

        if {item.CanonicalRequirementId for item in plan.NonResponseRequirements} != expected_non_response:
            issues.append("NonResponseRequirements is inconsistent with planning dispositions")
        if {
            item.CanonicalRequirementId for item in plan.ReviewRequiredRequirements
        } != review_required_ids:
            issues.append(
                "ReviewRequiredRequirements is inconsistent with planning dispositions"
            )

        dispositions_by_id = {
            item.CanonicalRequirementId: item for item in plan.RequirementDispositions
        }
        for requirement in requirements:
            raw_source_ids = list(
                dict.fromkeys(
                    str(value)
                    for value in _list(requirement.get("RequirementIds"))
                    if value is not None and str(value).strip()
                )
            )
            disposition = dispositions_by_id.get(requirement["CanonicalRequirementId"])
            if disposition and raw_source_ids and disposition.SourceRequirementIds != raw_source_ids:
                issues.append(
                    "Requirement disposition lineage does not match RequirementIds: "
                    f"{requirement['CanonicalRequirementId']}"
                )
        expected_source_coverage = (
            not review_required_ids
            and requirement_ids
            == set(mapped_trace_ids) | expected_non_response
        )
        if plan.Validation.SourceRequirementCoverageValid != expected_source_coverage:
            issues.append("SourceRequirementCoverageValid is incorrect")
        expected_proposal_coverage = response_requirement_ids == set(mapped_trace_ids)
        if plan.Validation.ProposalRequirementCoverageValid != expected_proposal_coverage:
            issues.append("ProposalRequirementCoverageValid is incorrect")

        evidence_trigger_nodes = {
            (item.SectionId, item.SubSectionId)
            for item in plan.Traceability.EvidenceRequirementTriggers
        }
        case_trigger_nodes = {
            (item.SectionId, item.SubSectionId)
            for item in plan.Traceability.CaseStudyTriggers
        }
        for _, section, subsection in self._owner_pairs(plan):
            node = subsection or section
            pair = (section.SectionId, subsection.SectionId if subsection else None)
            if node.EvidenceRequired and pair not in evidence_trigger_nodes:
                issues.append(f"EvidenceRequired lacks a source trigger: {node.SectionId}")
            if node.CaseStudyRequired and pair not in case_trigger_nodes:
                issues.append(f"CaseStudyRequired lacks a source trigger: {node.SectionId}")

        review_required = bool(
            evaluation.get("Conflicts")
            or evaluation.get("MissingInformation")
            or evaluation.get("ReviewFlags")
            or evaluation.get("RequiresHumanReview")
            or plan.Validation.BlockingIssues
            or review_required_ids
        )
        expected_status = "ValidationRequired" if review_required else "Generated"
        if issues:
            expected_status = "ValidationRequired"
        if plan.PlanStatus != expected_status:
            issues.append(f"PlanStatus must be {expected_status} for the generated result")
        return list(dict.fromkeys(issues))

    @staticmethod
    def _nodes(plan: ProposalPlan):
        for group in plan.ProposalGroups:
            for section in group.Sections:
                yield group.GroupId, section, False
                for subsection in section.SubSections:
                    yield group.GroupId, subsection, True

    @staticmethod
    def _owner_pairs(plan: ProposalPlan):
        for group in plan.ProposalGroups:
            for section in group.Sections:
                yield group.GroupId, section, None
                for subsection in section.SubSections:
                    yield group.GroupId, section, subsection

    @staticmethod
    def _configured_ids(configuration: dict[str, Any]) -> set[str]:
        result: set[str] = set()
        for group in _list(configuration.get("Groups")):
            for section in _list(group.get("Sections")):
                section_id = section.get("SectionId")
                if section_id:
                    result.add(str(section_id))
                for subsection in _list(section.get("SubSections")):
                    sub_id = subsection.get("SectionId") or subsection.get("SubSectionId")
                    if sub_id:
                        result.add(str(sub_id))
        return result

    @staticmethod
    def _configuration_maps(
        configuration: dict[str, Any],
    ) -> tuple[
        dict[str, dict[str, Any]],
        dict[str, tuple[str, dict[str, Any]]],
        dict[str, tuple[str, dict[str, Any]]],
    ]:
        groups: dict[str, dict[str, Any]] = {}
        sections: dict[str, tuple[str, dict[str, Any]]] = {}
        subsections: dict[str, tuple[str, dict[str, Any]]] = {}
        for group in _list(configuration.get("Groups")):
            group_id = str(group.get("GroupId") or "")
            groups[group_id] = group
            for section in _list(group.get("Sections")):
                section_id = str(section.get("SectionId") or "")
                sections[section_id] = (group_id, section)
                for subsection in _list(section.get("SubSections")):
                    subsection_id = str(
                        subsection.get("SubSectionId")
                        or subsection.get("SectionId")
                        or ""
                    )
                    subsections[subsection_id] = (section_id, subsection)
        return groups, sections, subsections
