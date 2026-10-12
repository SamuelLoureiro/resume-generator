# Proposals for Candidate Data & Prompt Improvements (ADR-025)

**Status:** Proposed (Awaiting Human Review & Manual Application)  
**Date:** 2026-10-12  
**Context:** Observations from the generated CV for *Inalfa Roof Systems (AI Processing in Automotive ECUs, EN)*.

Under the project rules (`.agents/GEMINI.md`), the agent must **NEVER** directly modify `data/candidate_facts.yaml` or `data/candidate_profile.yaml`. The data-level gaps, fact fusions, prompt leaks, and relevancy issues observed in the Inalfa test generation are documented here as concrete proposals for the human maintainer.

---

## 1. Defect 10: Missing TinyML Hardware Metrics (Data Gap)

### Problem
The Inalfa job posting strongly emphasizes embedded resource constraints (MCU RAM, Flash footprint, inference latency, power budget). The generated resume could not cite concrete TinyML metrics because they are entirely missing from `data/candidate_profile.yaml` and `data/candidate_facts.yaml`. If the LLM produces numbers like "under 50ms latency" or "<32KB RAM", the claim verifier will rightly flag them as `FABRICATION_NUMBER`.

### Proposed Action for Human
Add measured benchmark metrics for the candidate's Edge Impulse / microcontroller audio and vision classification projects.

#### In `data/candidate_facts.yaml`:
```yaml
  proj_edge_impulse_metrics:
    claim: "Benchmarked and deployed TinyML model with measured hardware constraints: < 32 KB RAM, < 128 KB Flash footprint, and inference latency under 45 ms on ARM Cortex-M4 (Nordic nRF52840 / STM32)."
    category: "projects"
    scope_level: 2
    scope_ceiling: "Strictly limited to the measured benchmark values (<32 KB RAM, <128 KB Flash, <45 ms latency). Do not generalize to unmeasured architectures or real-time automotive ASIL requirements."
    allowed_terms:
      - "TinyML"
      - "Edge Impulse"
      - "RAM"
      - "Flash"
      - "latency"
      - "ARM Cortex-M4"
      - "nRF52840"
```

#### In `data/candidate_profile.yaml` (under the appropriate project entry):
```yaml
      - "Achieved TinyML resource footprint under 32 KB RAM and 128 KB Flash with 42 ms inference latency on ARM Cortex-M4 via Edge Impulse optimization."
```

---

## 2. Defect 9: "Member of the Month" Dropped (`exp_asimov_awards`)

### Problem
The candidate received two distinct awards at Asimov Jr.:
1. **Area of the Month** (awarded to the Mobile development team).
2. **Member of the Month** (individual recognition awarded to the candidate).

In `data/candidate_facts.yaml`, both recognitions were grouped into a single fact entry `exp_asimov_awards`. In generation, the LLM compressed the text and omitted "Member of the Month", keeping only a conflated area reference.

### Proposed Action for Human
Split `exp_asimov_awards` into two distinct atomic facts so the retrieval engine and prompt can surface both independently.

#### In `data/candidate_facts.yaml`:
```yaml
  exp_asimov_award_area:
    claim: "Recognized with 'Area of the Month' award as Mobile Area Manager at Asimov Jr. for leading the top-performing engineering division."
    category: "experience"
    scope_level: 2
    scope_ceiling: "Award was won specifically by the Mobile Area team during tenure as Mobile Area Manager. Do NOT attribute to the Data Science department."
    allowed_terms:
      - "Area of the Month"
      - "Mobile Area Manager"
      - "Asimov Jr."

  exp_asimov_award_member:
    claim: "Awarded 'Member of the Month' individual distinction at Asimov Jr. for outstanding individual contribution and technical execution."
    category: "experience"
    scope_level: 2
    scope_ceiling: "Individual recognition at Asimov Jr. Do not exaggerate as company-wide executive award."
    allowed_terms:
      - "Member of the Month"
      - "individual distinction"
      - "Asimov Jr."
```

---

## 3. Defect 3: Fact Fusion (`exp_asimov_leadership` + `exp_asimov_awards`)

### Problem
The generated text merged two separate factual claims into a single conflated sentence:
> *"Founded the Data Science department and won Area of the Month..."*

This creates an ungrounded implication that the "Area of the Month" was awarded to or earned by the Data Science department. In reality:
- Mobile Area Manager: managed 5+ developers, won **Area of the Month**.
- Data Science initiative: founded as a separate strategic department within the organization.

### Proposed Action for Human
1. **Data Clarification in `data/candidate_facts.yaml`:**
   Add explicit anti-fusion scope ceiling on `exp_asimov_leadership`:
   ```yaml
     exp_asimov_leadership:
       claim: "Served as Mobile Area Manager managing a team of 5+ developers, and spearheaded the creation of the organization's Data Science department."
       category: "experience"
       scope_level: 2
       scope_ceiling: "Mobile management (5+ devs) and Data Science creation are distinct initiatives. The 'Area of the Month' award belonged strictly to the Mobile Area, NOT the Data Science department. Do not merge these into a single causal outcome."
   ```
2. **Prompt Rule for Phase B (`src/generation/prompts.py`):**
   Add a strict Fact Fusion Prohibition:
   > *"NEVER merge distinct achievements across departments or roles. If an award was won in Role A (e.g. Mobile Area Manager), do not state or imply it was earned by Department B (e.g. Data Science)."*

---

## 4. Defect 8: Coursework Relevance Filtering

### Problem
The Education section listed coursework items that were completely irrelevant to automotive embedded systems / edge AI (e.g., general business, physics, or web dev), displacing relevant coursework such as *Microcontrollers, Real-Time Operating Systems, Signal Processing, Computer Architecture, Embedded C*.

In `build_fallback_tailored_resume`, the code took `edu.relevant_coursework[:3]`, and in LLM generation, no explicit domain ranking was applied.

### Proposed Action for Human
1. **In `data/candidate_profile.yaml`:**
   Ensure coursework entries for ENIB and UTFPR list embedded and systems coursework prominently:
   ```yaml
     relevant_coursework:
       - "Real-Time Embedded Systems"
       - "Microcontrollers & Architecture"
       - "Digital Signal Processing"
       - "Operating Systems"
       - "Machine Learning"
   ```
2. **In Pipeline / Code (Phase B):**
   Implement dynamic coursework relevance ranking against the target job posting keywords, matching terms like `["embedded", "real-time", "microcontroller", "signal", "architecture", "c++", "ai"]`.

---

## 5. Defect 1: Pipeline Vocabulary Leak ("verified")

### Problem
The Professional Summary contained the phrase *"verified track record in..."*.
This is an unintentional leak of internal pipeline vocabulary (`GroundTruth`, `candidate_facts.yaml`, `verified claims`).

### Proposed Action for Pipeline (Phase B):
1. **In `src/generation/prompts.py`:**
   Add negative constraint:
   > *"Do NOT use internal system vocabulary in resume copy, such as 'verified', 'atomic facts', 'ground truth', or 'pipeline'. Use recruiter-facing professional phrasing such as 'demonstrated', 'proven track record', or 'hands-on experience'."*
2. **In `src/verification/repair.py`:**
   Add a deterministic substitution pass in `repair_resume` that replaces `"verified "` with `"demonstrated "` in summaries and bullets.

---

## 6. Defect 2: Echoing Job Posting Phrases Verbatim ("lightweight neural networks")

### Problem
The LLM echoed verbatim phrases from the Inalfa job description (*"seeking to deploy lightweight neural networks on automotive ECUs"*) into the candidate's summary as if stating candidate competencies.

### Proposed Action for Pipeline (Phase B):
1. Reinforce the **Active Technical Value Proposition** mandate in `src/generation/prompts.py`:
   - State what the candidate *has built and mastered* based on verified facts.
   - Forbid echoing future job duties or aspirational requirements as applicant desires.
   - Forbid phrases like *"seeking to develop lightweight neural networks for ECU..."* unless grounded directly in candidate's completed project facts.
