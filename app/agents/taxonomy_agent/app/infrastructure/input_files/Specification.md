# Tender Document Type Resolver — Specification v1.2

## Purpose
Given one or more CPV codes, return a reusable document taxonomy for downstream document classification. If `tenderId` is present, generate a tender taxonomy. If `tenderId` is not present and `companyId` is present, generate a company taxonomy for the supplied company CPV code.

## Input JSON
```json
{
  "tenderId": "string|null",
  "companyId": "string|null",
  "cpv": {
    "code": "string",
    "label": "string|null",
    "additionalCodes": [{ "code": "string", "label": "string|null" }]
  },
  "context": {
    "country": "string|null",
    "procedure": "string|null",
    "sectorHint": "string|null"
  },
  "CPVsetfor": "Tender|Company"
}
```

## Output JSON
```json
{
  "tenderId": "string|null",
  "companyId": "string|null",
  "cpvProfile": {
    "primaryCpvCode": "string",
    "primaryCpvLabel": "string|null",
    "cpvDivision": "string",
    "sectorFamilies": ["string"],
    "confidence": "HIGH|MEDIUM|LOW|UNKNOWN",
    "rationale": "string"
  },
  "classificationSet": [
    {
      "code": "string",
      "name": "string",
      "group": "Universal|SectorSpecific",
      "priority": "Core|Likely|Optional",
      "expectedSignals": ["string"]
    }
  ],
  "downstreamUse": {
    "instruction": "Use classificationSet as the allowed taxonomy for later document classification.",
    "universalTypesIncluded": true,
    "cpvSpecificTypesIncluded": true,
    "doNotUseCpvAsDocumentEvidence": true
  },
  "warnings": ["string"],
  "CPVsetfor": "Tender|Company"
}
```

## CPV Division Resolver
Use the first two digits of each usable CPV code.

```text
03,15,16=FOOD_AGRI
30,31,32,33,34,35=EQUIPMENT_GOODS
41,42,43,44=INDUSTRIAL_GOODS
45=CONSTRUCTION_WORKS
48,72=IT_DIGITAL
50,51=MAINTENANCE_INSTALLATION
55=HOSPITALITY_CATERING
60,63,64=TRANSPORT_LOGISTICS
66=FINANCE_INSURANCE
70,71=BUILT_ENVIRONMENT_PROFESSIONAL
73=RESEARCH_DEVELOPMENT
75=PUBLIC_ADMINISTRATION
79=PROFESSIONAL_SERVICES
80=EDUCATION_TRAINING
85=HEALTH_SOCIAL_CARE
90,92,98=ENVIRONMENT_COMMUNITY_OTHER
OTHER=GENERIC_TENDER
```

## Universal Document Types
Always include these, regardless of CPV.

```text
TENDER_NOTICE|Tender / contract notice|Core|notice, opportunity, buyer, contract notice
ITT_INSTRUCTIONS|ITT / RFP / RFQ instructions|Core|instructions, tenderers, submission, procurement process
PROCUREMENT_TIMETABLE|Procurement timetable|Core|deadline, clarification date, award date, timetable
STATEMENT_OF_REQUIREMENTS|Statement of requirements|Core|requirements, outcomes, mandatory requirements
SCOPE_OF_WORK|Scope of work|Core|scope, services, works, deliverables
TECHNICAL_SPECIFICATION|Technical specification|Core|technical, functional, specification, performance
EVALUATION_CRITERIA|Evaluation criteria|Core|scoring, weighting, award criteria, pass/fail
PRICING_SCHEDULE|Pricing schedule|Core|price, cost, rate card, commercial return
CONTRACT_TERMS|Contract terms|Core|terms, conditions, draft contract, schedules
SUPPLIER_QUESTIONNAIRE|SQ / PQQ / supplier questionnaire|Likely|selection questionnaire, exclusion, financial standing
RESPONSE_FORM|Tender response form|Likely|response form, return schedule, bidder response
DECLARATIONS|Declarations and certificates|Likely|declaration, certificate, conflict, non-collusion
DATA_PROTECTION|Data protection / GDPR|Likely|personal data, processor, GDPR, DPIA
INFORMATION_SECURITY|Information security|Likely|security, cyber, ISO 27001, accreditation
INSURANCE_REQUIREMENTS|Insurance requirements|Likely|insurance, liability, indemnity
SOCIAL_VALUE|Social value|Likely|social value, community, economic benefit
SUSTAINABILITY|Sustainability / environmental|Likely|carbon, environment, sustainability, net zero
EQUALITY_DIVERSITY|Equality, diversity and inclusion|Optional|EDI, equality, diversity, inclusion
MODERN_SLAVERY|Modern slavery|Optional|modern slavery, supply chain, labour
HEALTH_SAFETY|Health and safety|Likely|health and safety, risk assessment, method statement
MOBILISATION_TRANSITION|Mobilisation / transition|Likely|mobilisation, transition, implementation, handover
SERVICE_LEVELS_KPIS|Service levels / KPIs|Likely|SLA, KPI, performance, service credits
GOVERNANCE_REPORTING|Governance and reporting|Likely|governance, reporting, meetings, escalation
RISK_REGISTER|Risk register|Optional|risk, mitigation, issue log
CLARIFICATION_QA|Clarifications / Q&A|Optional|clarification, question, answer, response log
ADDENDUM_AMENDMENT|Addendum / amendment|Optional|addendum, amendment, revised, update
APPENDIX_SUPPORTING_INFO|Appendix / supporting information|Optional|appendix, background, schedule, annex
UNKNOWN_OR_UNCLEAR|Unknown / unclear document|Core|unknown, unclear, insufficient evidence
```

## Sector-Specific Extensions
Add only the extensions for resolved CPV sector families.

```text
IT_DIGITAL:
IT_ARCHITECTURE|Architecture / solution design|Likely|architecture, design, solution, blueprint
SOFTWARE_REQUIREMENTS|Software requirements|Likely|software, functional, non-functional, user stories
INTEGRATION_API|Integration / API requirements|Likely|API, interface, integration, interoperability
DATA_MIGRATION|Data migration|Likely|migration, legacy, mapping, cutover
DATA_PLATFORM|Data management / platform|Likely|data, warehouse, lakehouse, analytics, BI
CLOUD_HOSTING|Cloud hosting / infrastructure|Likely|cloud, hosting, Azure, AWS, infrastructure
CYBER_SECURITY|Cyber security requirements|Likely|cyber, penetration test, security controls
TESTING_ACCEPTANCE|Testing and acceptance|Likely|UAT, testing, acceptance, defect
SUPPORT_MAINTENANCE|Support and maintenance|Likely|support, maintenance, service desk
LICENSING_SUBSCRIPTION|Licensing / subscription|Optional|licence, subscription, SaaS
AI_AUTOMATION|AI / automation requirements|Optional|AI, automation, workflow, model

CONSTRUCTION_WORKS:
DRAWINGS_PLANS|Drawings / plans|Likely|drawing, plan, layout
BILL_OF_QUANTITIES|Bill of quantities|Likely|BoQ, quantities, schedule of rates
SITE_INFORMATION|Site information|Likely|site, access, survey, constraints
DESIGN_INFORMATION|Design information|Likely|design, specification, drawing package
CONSTRUCTION_PROGRAMME|Construction programme|Likely|programme, milestones, phasing
CDM_REQUIREMENTS|CDM / construction safety|Likely|CDM, construction safety, principal contractor
METHOD_STATEMENT|Method statement requirements|Likely|method statement, RAMS, work method
MATERIAL_SPECIFICATION|Materials specification|Likely|materials, product standard, workmanship
SITE_VISIT|Site visit instructions|Optional|site visit, inspection, walkaround

HEALTH_SOCIAL_CARE:
CLINICAL_SPECIFICATION|Clinical specification|Likely|clinical, care, patient, service specification
CARE_MODEL|Care pathway / service model|Likely|pathway, referral, discharge, care model
SAFEGUARDING|Safeguarding requirements|Likely|safeguarding, children, vulnerable adults
CLINICAL_GOVERNANCE|Clinical governance|Likely|clinical governance, audit, quality
INFORMATION_GOVERNANCE|Information governance|Likely|IG, Caldicott, patient data
STAFFING_MODEL|Staffing model|Likely|rota, staffing, workforce, qualifications
OUTCOMES_FRAMEWORK|Outcomes framework|Optional|outcomes, measures, quality indicators

PROFESSIONAL_SERVICES:
CONSULTANCY_BRIEF|Consultancy brief|Likely|brief, advisory, consultancy, objectives
METHODOLOGY_REQUIREMENTS|Methodology requirements|Likely|methodology, approach, workstream
DELIVERABLES|Deliverables|Likely|deliverables, outputs, milestones
TEAM_CV_REQUIREMENTS|Team / CV requirements|Likely|CV, personnel, key staff
CASE_STUDY_REQUIREMENTS|Case study requirements|Likely|case study, reference, experience
DAY_RATE_CARD|Day rate card|Likely|day rate, role, grade, rate card
KNOWLEDGE_TRANSFER|Knowledge transfer|Optional|handover, training, knowledge transfer

MAINTENANCE_INSTALLATION,ENVIRONMENT_COMMUNITY_OTHER:
ASSET_REGISTER|Asset register|Likely|asset, equipment list, inventory
MAINTENANCE_SCHEDULE|Maintenance schedule|Likely|planned maintenance, PPM, schedule
SERVICE_FREQUENCY|Service frequency|Likely|frequency, routine, daily, weekly
TUPE_INFORMATION|TUPE information|Optional|TUPE, employee liability, staff transfer
SITE_LIST|Site list|Likely|site list, locations, premises
COMPLIANCE_INSPECTIONS|Compliance inspections|Likely|inspection, statutory, compliance
ENVIRONMENTAL_CONTROLS|Environmental controls|Likely|waste, carbon, pollution, environmental

EQUIPMENT_GOODS,INDUSTRIAL_GOODS,FOOD_AGRI:
PRODUCT_SPECIFICATION|Product specification|Likely|product, item, technical datasheet
CATALOGUE|Catalogue / item list|Likely|catalogue, item list, SKU
DELIVERY_REQUIREMENTS|Delivery requirements|Likely|delivery, logistics, lead time
WARRANTY_REQUIREMENTS|Warranty requirements|Likely|warranty, guarantee, defects
TECHNICAL_DATASHEET|Technical datasheet|Optional|datasheet, technical sheet, specification sheet
CERTIFICATION_COMPLIANCE|Certification / compliance|Likely|certificate, compliance, standard
AFTER_SALES_SUPPORT|After-sales support|Optional|after-sales, support, repairs

TRANSPORT_LOGISTICS:
ROUTES_TIMETABLES|Routes / timetables|Likely|route, timetable, schedule
FLEET_REQUIREMENTS|Fleet requirements|Likely|fleet, vehicle, capacity
DEPOT_OPERATIONS|Depot / operating base|Optional|depot, garage, operating centre
DRIVER_COMPLIANCE|Driver compliance|Likely|driver, licence, training, checks
LOGISTICS_MODEL|Logistics operating model|Likely|logistics, distribution, routing

FINANCE_INSURANCE:
FINANCIAL_SERVICE_SCOPE|Financial service scope|Likely|finance, insurance, claims, cover
REGULATORY_COMPLIANCE|Regulatory compliance|Likely|FCA, PRA, regulation, compliance
CLAIMS_MODEL|Claims model|Optional|claims, loss, settlement
REPORTING_AUDIT|Reporting / audit|Likely|audit, reporting, reconciliation

EDUCATION_TRAINING:
TRAINING_PLAN|Training plan|Likely|training, course, delivery plan
CURRICULUM_CONTENT|Curriculum / content|Likely|curriculum, modules, learning outcomes
ASSESSMENT_MODEL|Assessment model|Likely|assessment, test, certification
LEARNER_SUPPORT|Learner support|Optional|learner, support, accessibility
ACCREDITATION|Accreditation|Optional|accreditation, qualification, awarding body

RESEARCH_DEVELOPMENT:
RESEARCH_BRIEF|Research brief|Likely|research, study, objectives
RESEARCH_METHOD|Research methodology|Likely|methodology, sampling, analysis
ETHICS_APPROVAL|Ethics / approval|Optional|ethics, consent, approval
IP_RIGHTS|IP rights|Likely|intellectual property, ownership, licence
PUBLICATION_OUTPUTS|Publication outputs|Optional|publication, report, dissemination

HOSPITALITY_CATERING:
MENU_REQUIREMENTS|Menu requirements|Likely|menu, meal, catering
NUTRITION_ALLERGENS|Nutrition / allergens|Likely|nutrition, allergen, dietary
CATERING_OPERATIONS|Catering operating model|Likely|kitchen, service, food safety
FACILITY_REQUIREMENTS|Facility requirements|Optional|facility, venue, accommodation

BUILT_ENVIRONMENT_PROFESSIONAL:
DESIGN_BRIEF|Design brief|Likely|design brief, concept, requirements
SURVEY_REPORTS|Survey reports|Likely|survey, condition, measured survey
PLANNING_CONSENTS|Planning / consents|Optional|planning, consent, approval
PROFESSIONAL_CERTIFICATION|Professional certification|Likely|chartered, RIBA, RICS, engineer
```

## Selection Rules
1. Validate primary and additional CPV codes.
2. Start with all Universal Document Types.
3. Resolve sector families from usable CPV divisions.
4. Add matching Sector-Specific Extensions.
5. If no usable sector family exists, return universal types only.
6. Set `CPVsetfor` to `Tender` when `tenderId` is present. Set `CPVsetfor` to `Company` when `tenderId` is not present and `companyId` is present.
6. Deduplicate by `code`.
7. Preserve priority and expectedSignals from this specification.
8. Return JSON in the defined output shape only.
