# Experiment E01 — Baselines Benchmark (B0, B1, B3)

> Governed by `docs/research_plan.md` (Sections 4, 5, 7).
> Evaluates the reference baselines B0 (Deterministic fallback), B1 (Hybrid RAG), and B3 (Full-Context) across the 7 development internship postings.

## Experiment Metadata

- **Date:** 2026-10-05T17:18:29.429038
- **Git SHA:** `459c8cadd1ecf8b7007dc91c7768394577c27211`
- **Dataset Manifest SHA-256:** `73451000f576b6692027a4f1d7ba24e8c7597ed64d307b2228923c2a181673b9`
- **Generator Model:** `gemini-3.5-flash-lite`
- **Judge Model:** `gemini-3.1-flash-lite`
- **Judge Prompt Version:** `claim_judge_v2.0`
- **Total API Calls Made:** 35
  - Generator calls (`gemini-3.5-flash-lite`): 14 (7 B1 + 7 B3)
  - Judge calls (`gemini-3.1-flash-lite`): 21 (7 B0 + 7 B1 + 7 B3)

## Headline Metrics Summary

| Variant | Description | Hard-Pass Rate | M1 Fabrication (Det + Judge) | M2 Inflation Rate | M3 Coverage | M4 Truthful KW | M5 Format Pass |
|---|---|---|---|---|---|---|---|
| **B0** | Deterministic Fallback (No LLM) | **14.3%** (1/7) | 0.00 claims/res | 0.0% | 56.1% | 100.0% | 14.3% (1/7) |
| **B1** | Hybrid RAG Pipeline (Gemini) | **0.0%** (0/7) | 11.71 claims/res | 16.7% | 14.2% | 100.0% | 100.0% (7/7) |
| **B3** | Full Knowledge Base in Prompt (Gemini) | **0.0%** (0/7) | 7.43 claims/res | 28.6% | 15.6% | 100.0% | 85.7% (6/7) |

## Per-Posting Results

| Variant | Job ID | Language | Track | Hard Pass | M1 Det (Tools/Num/Dates) | M1d Claims | M2 Inflated | M3 Coverage | M4 KW | M5 Format |
|---|---|---|---|---|---|---|---|---|---|---|
| `b0` | `genai_rag_intern` | `pt` | `ai` | ❌ FAIL | 0/0/0 | 0/7 | 0/10 | 50% | 100% | FAIL (single_language) |
| `b0` | `data_science_ml_intern` | `pt` | `data` | ❌ FAIL | 0/0/0 | 0/6 | 0/10 | 57% | 100% | FAIL (single_language) |
| `b0` | `backend_python_intern` | `pt` | `backend` | ❌ FAIL | 0/0/0 | 0/6 | 0/10 | 55% | 100% | FAIL (single_language) |
| `b0` | `swe_algorithms_intern` | `pt` | `core_swe` | ❌ FAIL | 0/0/0 | 0/5 | 0/10 | 67% | 100% | FAIL (single_language) |
| `b0` | `data_engineering_intern` | `pt` | `data` | ❌ FAIL | 0/0/0 | 0/6 | 0/10 | 57% | 100% | FAIL (single_language) |
| `b0` | `fr_stellantis_data_science` | `fr` | `data` | ❌ FAIL | 0/0/0 | 0/5 | 0/10 | 57% | 100% | FAIL (single_language) |
| `b0` | `en_criteo_ml_intern` | `en` | `ai` | ✅ PASS | 0/0/0 | 0/5 | 0/10 | 50% | 100% | PASS |
| `b1` | `genai_rag_intern` | `pt` | `ai` | ❌ FAIL | 2/0/16 | 0/10 | 0/3 | 20% | 100% | PASS |
| `b1` | `data_science_ml_intern` | `pt` | `data` | ❌ FAIL | 1/0/2 | 2/7 | 0/0 | 0% | 100% | PASS |
| `b1` | `backend_python_intern` | `pt` | `backend` | ❌ FAIL | 1/0/10 | 1/7 | 0/2 | 9% | 100% | PASS |
| `b1` | `swe_algorithms_intern` | `pt` | `core_swe` | ❌ FAIL | 6/0/11 | 1/4 | 0/1 | 0% | 100% | PASS |
| `b1` | `data_engineering_intern` | `pt` | `data` | ❌ FAIL | 5/0/11 | 1/6 | 0/0 | 0% | 100% | PASS |
| `b1` | `fr_stellantis_data_science` | `fr` | `data` | ❌ FAIL | 0/0/12 | 0/13 | 0/1 | 0% | 100% | PASS |
| `b1` | `en_criteo_ml_intern` | `en` | `ai` | ❌ FAIL | 0/0/0 | 0/6 | 3/11 | 70% | 100% | PASS |
| `b3` | `genai_rag_intern` | `pt` | `ai` | ❌ FAIL | 2/0/2 | 1/6 | 1/1 | 10% | 100% | FAIL (single_language) |
| `b3` | `data_science_ml_intern` | `pt` | `data` | ❌ FAIL | 1/0/2 | 1/7 | 0/0 | 0% | 100% | PASS |
| `b3` | `backend_python_intern` | `pt` | `backend` | ❌ FAIL | 1/0/4 | 1/6 | 0/0 | 0% | 100% | PASS |
| `b3` | `swe_algorithms_intern` | `pt` | `core_swe` | ❌ FAIL | 6/0/6 | 1/10 | 0/3 | 7% | 100% | PASS |
| `b3` | `data_engineering_intern` | `pt` | `data` | ❌ FAIL | 1/0/5 | 3/11 | 0/3 | 29% | 100% | PASS |
| `b3` | `fr_stellantis_data_science` | `fr` | `data` | ❌ FAIL | 1/0/12 | 0/9 | 0/0 | 14% | 100% | PASS |
| `b3` | `en_criteo_ml_intern` | `en` | `ai` | ❌ FAIL | 0/0/0 | 2/5 | 3/7 | 50% | 100% | PASS |

## Execution Commands

```bash
# Dry run (offline check)
python3 scripts/run_baselines.py --dry-run

# Live execution of all baselines
python3 scripts/run_baselines.py --variants b0,b1,b3 --max-calls 100
```

## Interpretation

1. **Comportamento do Piso Determinístico (B0):**
   - O baseline B0 cumpriu seu papel de piso factual: obteve **0.00 alegações fabricadas por currículo** e **0.0% de verbos inflados**, comprovando a fidelidade absoluta aos fatos atômicos verificados.
   - O resultado de 14.3% (1/7) no `hard_pass` decorreu unicamente da regra `single_language` do check M5: como o fallback não utiliza LLM, ele copiou os bullets originais em inglês para vagas em português e francês sem tradução. Na vaga em inglês (`en_criteo_ml_intern`), o B0 obteve **100% de aprovação (PASS)**.
   - O B0 obteve a maior cobertura de fatos relevantes (M3: **56.1%**), preservando a maior densidade de informações verdadeiras do candidato.

2. **Falha de Fidelidade dos Modelos sem Verificação (B1 e B3):**
   - Tanto o pipeline de produção atual **B1 (RAG Híbrido)** quanto o baseline **B3 (Contexto Completo no Prompt)** obtiveram **0.0% de Hard-Pass** (0 de 7 aprovados).
   - Sem uma camada de verificação pós-geração, o LLM fabrica em média **11.71 alegações não fundamentadas** por currículo no B1 e **7.43** no B3. O juiz atômico e as regras determinísticas detectaram alterações de datas/períodos de atuação, adição de tecnologias não dominadas e invenção de responsabilidades de liderança/arquitetura.
   - A taxa de inflação de verbos (M2) foi expressiva: **16.7% no B1** e **28.6% no B3** (ex: o verbo "Architected" usado em projetos onde o teto de evidência permitia apenas desenvolvimento ou gestão operacional).
   - A cobertura de fatos relevantes (M3) caiu drasticamente em ambos (**14.2% no B1** e **15.6% no B3**), pois o LLM tendeu a sintetizar o currículo em poucos bullets generalistas para respeitar o limite de 1 página (M5: 100% no B1 e 85.7% no B3).

## Conclusions

1. **Confirmação Empírica da Hipótese H0:**
   - Os baselines B1 e B3 evidenciam que prompts convencionais de LLM em etapa única (*one-step generation*) falham sistematicamente no requisito de fidelidade estrita. Recuperar diretrizes de recrutamento via RAG ou via prompt completo não impede a alucinação de dados do candidato.

2. **Mandatoriedade do Verificador (Hipótese H1):**
   - Os dados do experimento E01 estabelecem a referência necessária para o projeto: para que o gerador produza currículos seguros para candidaturas reais, é mandatório implementar a **Fase P8 (Verificador V1 com regeneração orientada por erros e reparo determinístico)**.

3. **Comparativo Preliminar RAG vs. Contexto Completo (Hipótese H4):**
   - A diferença de cobertura entre B1 (14.2%) e B3 (15.6%) é marginal (+1.4 ponto percentual para B3). O B3 teve menor taxa absoluta de fabricação (7.43 vs. 11.71), porém maior taxa de inflação (28.6% vs. 16.7%). A decisão sobre a permanência do módulo de RAG (H4) só poderá ser avaliada conclusivamente após a adição do verificador V1, que removerá o ruído das alucinações.
