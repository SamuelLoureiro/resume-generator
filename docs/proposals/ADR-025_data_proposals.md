# Proposals for Candidate Data & Prompt Improvements (ADR-025)

**Status:** Proposed (Awaiting Human Review & Manual Application)  
**Date:** 2026-10-12  
**Context:** Observations from the generated CV for *Inalfa Roof Systems (AI Processing in Automotive ECUs, EN)*.

Under the project rules (`.agents/GEMINI.md`), the agent must **NEVER** directly modify `data/candidate_facts.yaml`, `data/candidate_profile.yaml`, or `docs/lessons.md`. The data-level gaps, fact fusions, prompt leaks, schema extensions, and track enum divergences observed during the Inalfa defect analysis are documented here for the human maintainer to apply manually.

---

## 1. Defect 10: Missing TinyML Hardware Metrics (Data Gap)

### Problem
The Inalfa job posting strongly emphasizes embedded resource constraints (MCU RAM, Flash footprint, inference latency, power budget). The generated resume could not cite concrete TinyML metrics because they are entirely missing from `data/candidate_profile.yaml` and `data/candidate_facts.yaml`. If an LLM produces numbers like "under 50ms latency" or "<32KB RAM", the claim verifier will rightly flag them as `FABRICATION_NUMBER`.

### Maintainer Decision
The maintainer has confirmed: **Keep candidate facts as-is (do not add/modify any TinyML metrics in `candidate_facts.yaml`).** The generation and verification pipelines will continue to reject ungrounded metrics and avoid fabricating numbers.

### Reference (for future reference if benchmarks are run)
If measured values are ever obtained from experimental firmware logs or Edge Impulse dashboards:
- **Rule:** Do NOT invent numbers. Only use values backed by real hardware measurements.

#### Which Facts Would Hold Them:
1. `proj_edge_impulse` (or new dedicated fact `proj_edge_impulse_metrics`):
   - **Target hardware:** e.g. ARM Cortex-M4 (Nordic nRF52840 or STM32F4).
   - **Measurements required from human:**
     - Measured RAM allocation / peak arena (in KB)
     - Measured Flash / ROM footprint (in KB)
     - Measured inference latency per window/frame (in ms)
     - Model architecture & quantization (e.g. int8 quantized CNN / spectrogram)
     - Audio or sensor sample rate and classification accuracy (%)

#### Example Format for `data/candidate_facts.yaml`:
```yaml
  proj_edge_impulse_benchmarks:
    claim: "Benchmarked and deployed quantized int8 audio classifier on ARM Cortex-M4 with [HUMAN_MEASURED_RAM] KB RAM, [HUMAN_MEASURED_FLASH] KB Flash, and [HUMAN_MEASURED_LATENCY] ms inference latency via Edge Impulse."
    category: "projects"
    scope_level: 3
    scope_ceiling: 3
    tracks:
      - "embedded"
      - "ai"
    priority: 1
    allowed_terms:
      - "TinyML"
      - "Edge Impulse"
      - "ARM Cortex-M4"
      - "RAM"
      - "Flash"
      - "latency"
```

---

## 2. Defect 9 & Defect 3: Asimov Awards Split & Fact Fusion Prevention

### Problem
The candidate received two distinct awards at Asimov Jr.:
1. **Area of the Month** (team recognition awarded to the Mobile development team during candidate's tenure as Mobile Area Manager).
2. **Member of the Month** (individual recognition awarded to the candidate).

In `data/candidate_facts.yaml`, both recognitions were compressed into a single entry `exp_asimov_awards`. In generation, this caused:
- **Defect 9:** "Member of the Month" was dropped due to space and single-fact compression.
- **Defect 3 (Fact Fusion):** Sentences merged `exp_asimov_leadership` ("founded Data Science department") with `exp_asimov_awards` ("won Area of the Month"), generating false implications that the award belonged to the Data Science department or was earned for Data Science initiatives.

### Proposed Action for Human
Split `exp_asimov_awards` into two distinct facts with higher priority, updated tracks, and explicit subject scope ceilings.

#### In `data/candidate_facts.yaml`:
```yaml
  exp_asimov_mobile_area_of_month:
    claim: "Led the Mobile Area team of 5+ developers to win 'Area of the Month' for top organizational performance at Asimov Jr."
    category: "experience"
    scope_level: 2
    scope_ceiling: 2
    subject: "mobile_team"
    tracks:
      - "embedded"
      - "ai"
      - "core_swe"
      - "management"
    priority: 2
    allowed_terms:
      - "Area of the Month"
      - "Mobile Area Manager"
      - "Asimov Jr."
      - "mobile development team"

  exp_asimov_member_of_month:
    claim: "Recognized as 'Member of the Month' at Asimov Jr. for outstanding individual execution and project delivery."
    category: "experience"
    scope_level: 2
    scope_ceiling: 2
    subject: "candidate"
    tracks:
      - "embedded"
      - "ai"
      - "core_swe"
    priority: 2
    allowed_terms:
      - "Member of the Month"
      - "individual recognition"
      - "Asimov Jr."
```

---

## 3. Atomic Facts Schema Extension: Optional `subject` Field

### Problem
Verifiers and claim judges can easily confuse individual actions with team-level achievements (e.g. attributing a team award to a different sub-department or personal scope).

### Proposed Schema Addition in `src/data/facts.py`:
Add an optional `subject` field to `AtomicFact`:
```python
SubjectType = Literal["candidate", "team", "department", "organization"]

class AtomicFact(BaseModel):
    id: str
    text: str
    category: FactCategory
    scope_ceiling: int = Field(ge=1, le=4)
    tracks: list[str] = Field(default_factory=list)
    priority: int = Field(default=2, ge=1, le=3)
    subject: SubjectType = Field(
        default="candidate",
        description="Entity to which the action or achievement belongs (candidate, team, department)",
    )
    metrics: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
```

**Benefit:** Enables deterministic verification check `B3_SUBJECT_TRANSFER`: if a bullet has subject "candidate" claiming an award with subject "team", or attaches a "team" subject to a different department, flag the transfer before rendering.

---

## 4. Track Enum Divergence Analysis

### Problem
The project research plan (`docs/research_plan.md`) and recruitment guidelines establish 6 canonical benchmark tracks:
1. `ai` (Artificial Intelligence / LLMs / RAG)
2. `data` (Data Science / ML)
3. `backend` (Software Engineering / Backend)
4. `core_swe` (Core SWE / Systems / Algorithms)
5. `data_eng` (Data Engineering / ETL)
6. `embedded` (Embedded Systems / Automotive ECUs / Edge AI)
Plus `general`.

However, inspecting `data/candidate_facts.yaml` reveals 13 distinct tracks:
- Canonical tracks present: `ai` (11), `backend` (12), `core_swe` (16), `data` (8), `embedded` (11), `general` (2).
- **Tracks outside canonical enum:**
  - `algorithms` (1 fact)
  - `hardware` (2 facts)
  - `iot` (1 fact)
  - `management` (2 facts)
  - `mobile` (4 facts: `exp_asimov_developer`, `exp_asimov_leadership`, `exp_asimov_awards`, `proj_flutter_app`)
  - `robotics` (6 facts: `exp_rio_branco_robotics_coach`, `proj_stm32_line_follower`, `proj_can_bus_telemetry`, etc.)
  - `security` (2 facts)

### Harmonization Decision (Selected: Option B)
The human maintainer has approved **Option B (Re-tagging to Canonical Tracks)** for manual application in `data/candidate_facts.yaml`:
- `mobile` -> `core_swe` (or `backend`)
- `robotics` -> `embedded`
- `hardware` -> `embedded`
- `iot` -> `embedded`
- `algorithms` -> `core_swe`
- `management` -> `core_swe` + `general`

This keeps the canonical 6 benchmark tracks strict without proliferating specialized tracks in evaluators.

---

## 5. Coursework & Relevance Filtering Proposal

### Proposed Candidate Profile Update
Ensure `data/candidate_profile.yaml` lists embedded and systems coursework under both UTFPR and ENIB degrees:
```yaml
    relevant_coursework:
      - "Real-Time Operating Systems"
      - "Microcontrollers & Embedded Systems"
      - "Digital Signal Processing"
      - "Computer Architecture & Organization"
      - "Embedded Linux & Device Drivers"
```
This ensures high keyword overlap with automotive embedded and Edge AI job descriptions under the deterministic coursework selector.
