# Flow

        Initial State
  (company_id, industry, cpv_code)
            ↓
  read_cons_and_spec_node
            ↓
     Reads:
      - constitution.md
      - specification.md
            ↓
    wintheam_extractor_node
            ↓
    Reads:
    - system_prompt.md

    Uses:
    - constitution
    - specification
    - system_prompt
    - company_id
    - industry
    - cpv_code
            ↓
    LLM generates JSON blueprint
            ↓
    Final Output