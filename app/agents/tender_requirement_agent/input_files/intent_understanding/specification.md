# Intent Understanding Specification

## Objective

Analyze a supplier requirement and determine:

1. The business capability or capabilities required to satisfy the requirement.
2. The proposal sections most likely to contain supporting evidence.
3. The key semantic concepts that represent the requirement.

Always choose the closest matching values from the predefined lists below.

---

# Capability Intent Taxonomy

Select one or more values from the following list.

- Technical Capability
- Functional Capability
- Non-Functional Capability
- Service Delivery
- Project Management
- Program Management
- Governance
- Risk Management
- Quality Assurance
- Testing
- Support Services
- Maintenance
- Operations
- Training
- Staffing
- Resource Management
- Security
- Compliance
- Certification
- Documentation
- Reporting
- Procurement
- Submission
- Commercial
- Financial Capability
- Legal
- Insurance
- Health & Safety
- Environmental
- Sustainability
- Infrastructure
- Facilities Management
- Logistics
- Manufacturing
- Engineering
- Construction
- Consulting
- Research & Development
- Data Management
- Information Management
- Technology
- Integration
- Business Continuity
- Change Management
- Transition Management
- Customer Service
- Innovation
- Other

---

# Company Evidence Sections

Select one or more proposal sections from the following list.

- Executive Summary
- Company Overview
- Company Profile
- Organization
- Technical Solution
- Solution Overview
- Services
- Methodology
- Delivery Approach
- Delivery Model
- Implementation Plan
- Project Plan
- Governance
- Risk Management
- Quality Management
- Testing Strategy
- Security
- Compliance
- Certifications
- Policies
- Standards
- Team
- Key Personnel
- CVs
- Resource Plan
- Project Experience
- Case Studies
- References
- Customer Testimonials
- Support
- Maintenance
- Training
- Service Levels
- Commercial Response
- Pricing
- Financial Information
- Legal Response
- Contract Response
- Transition Plan
- Sustainability
- Innovation
- Appendices

---

# Semantic Anchors

Extract the important business concepts from the requirement.

Semantic Anchors may include:

- Products
- Services
- Technologies
- Standards
- Certifications
- Regulations
- Frameworks
- Platforms
- Tools
- Equipment
- Deliverables
- Job Roles
- Skills
- Departments
- Business Functions
- Organizations
- Locations
- Dates
- Timelines
- Quantities
- Financial Values
- Contract Names
- Industry Terms
- Key Business Phrases

Only extract anchors that are explicitly mentioned or clearly implied by the requirement.

---

# Mapping Rules

- Select the closest matching Capability Intent.
- Select the closest matching Company Evidence Sections.
- Do not invent new Capability Intent values.
- Do not invent new Evidence Section names.
- A requirement may map to multiple Capability Intents.
- A requirement may map to multiple Evidence Sections.
- Return empty arrays only if there is genuinely no reasonable match.

---

# Confidence

Return a confidence score between **0.00** and **1.00**.

Use:

- **0.95 – 1.00** → Very confident
- **0.80 – 0.94** → Good confidence
- **0.60 – 0.79** → Moderate confidence
- **Below 0.60** → Low confidence

---

# Output Rules

- Return ONLY valid JSON.
- Do NOT return Markdown.
- Do NOT explain your reasoning.
- Do NOT include additional text.

---

# Output JSON

```json
{
  "CapabilityIntent": [
    "Service Delivery"
  ],
  "EvidenceSections": [
    "Methodology",
    "Project Experience"
  ],
  "SemanticAnchors": [
    "Project Manager",
    "24x7 Support"
  ],
  "Confidence": 
}
```