# Industry-Specific Intake: Field Research & Schema Rationale

## Why these five fields

Each core question maps directly to a mandatory element of a recognized OHS program structure (OSHA 29 CFR 1910.132, CCOHS, and site-specific safety planning frameworks such as those used in Procore).

| Question | OHS Program Element | Why it matters |
|---|---|---|
| **Worksite type** (office / field / mixed) | Hazard Identification & Assessment | Physical environment determines the hazard universe. Field sites introduce fall, struck-by, and weather hazards that office environments do not. Drives which control sections appear in the plan. |
| **Headcount band** (1-4 / 5-19 / 20-99 / 100+) | Program Evaluation & Training | Jurisdiction thresholds for mandatory JHSC, safety representative, and written-program requirements are headcount-gated (e.g., Ontario OHSA s.9 requires JHSC at ≥20 workers). |
| **High-risk activity flags** (multi-select) | Hazard Identification & Prevention/Control | Activities with mandatory-specific regulations (working at heights O.Reg 213/91, confined spaces O.Reg 632/05, WHMIS for chemicals) cannot be inferred from NAICS alone. Direct selection keeps the plan legally accurate without over-generating. |
| **Subcontractor involvement** (boolean) | Prevention/Control & Legal Liability | Engaging contractors triggers owner/constructor duties under provincial OHS Acts. The answer unlocks the subcontractor-management conditional question and adds a contractor-orientation section to the plan. |
| **Emergency readiness** (single select) | Emergency Response Planning | CCOHS and OSHA require a named responsible person for evacuation and first aid. The answer populates the emergency-response section header and identifies gaps. |

## Progressive disclosure triggers

| Answer that triggers | Conditional unlocked | Reason |
|---|---|---|
| `has_subcontractors = true` | `subcontractor_management` | Determines how contractor safety is communicated; affects the subcontractor section |
| `high_risk_flags` includes `chemicals_or_hazardous_materials` | `chemical_inventory` | WHMIS 2015 requires an SDS inventory; answer drives the chemical-controls section |

## NAICS-driven question variation

The `high_risk_flags` option list is extended based on the 2-digit NAICS sector:

| Sector prefix | Extra option added | Regulation anchored |
|---|---|---|
| 31-33 (Manufacturing) | `chemicals_or_hazardous_materials` | WHMIS 2015 / OSHA HazCom |
| 62 (Healthcare) | `biological_hazards` | O.Reg 67/93 / OSHA BBP standard |
| All construction (23) | `working_at_heights` already in base set | O.Reg 213/91 |

## What is deliberately excluded

The following are intentionally deferred to document-generation time or a later intake phase to keep the initial UX to 5 questions:

- Specific chemical names / SDS list (generated from inventory flag)
- Training records / competency verification (program evaluation phase)
- Inspection frequency schedules (defaulted by industry; user can edit post-generation)
- Incident history (not required to produce an initial plan)

## Proposed database schema

```
industry_intake_responses
  id          INTEGER PK
  order_id    INTEGER FK → orders.id  UNIQUE
  answers     JSON          -- flexible; additive fields never break existing clients
  updated_at  DATETIME
```

The `answers` JSON column is intentionally schema-less so that new questions can be added without a migration. The unique constraint on `order_id` enforces one response set per order (upsert semantics).
