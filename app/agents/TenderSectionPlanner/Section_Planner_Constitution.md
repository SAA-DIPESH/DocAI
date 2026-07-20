# Section Planner Constitution

Version: 6.0

- Use only supplied CanonicalRequirementId and CriterionId values; never invent
  source IDs or unsupported tender content.
- Build a dynamic Group -> Section -> SubSection hierarchy. Every group and
  section is non-empty, and every subsection owns at least one supplied canonical
  requirement.
- Give each requirement exactly one direct subsection owner or mark it unmapped.
- Give each criterion at most one requirement-backed owner or mark it unmapped.
  Criteria cannot create hierarchy. Social Value criteria require an explicitly
  Social Value node.
- Python owns stable final IDs, order, exact weights/evidence, lineage,
  validation, traceability, operational fields, and persistence.
- Tender Section Configuration is not an input.
