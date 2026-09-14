# Part 2 findings (tables only)

Source: live measurements and tests recorded during Part 2 work. No new figures.

---

## 1. Planning latency by case type (GPT-5.5)


| # | Case | Seconds | Requirements clear | Departments |
|---|---|---|---|---|
| 1 | vague | 3.32 | False | [] |
| 2 | delegation | 6.27 | True | HR, IT, Finance |
| 3 | clear | 5.62 | True | IT, OP |
| 4 | vague | 2.74 | False | [] |
| 5 | delegation | 5.51 | True | HR, IT, Finance |
| 6 | clear | 4.85 | True | Sales, Support |
| 7 | vague | 2.66 | False | [] |
| 8 | delegation | 5.27 | True | HR, IT, Finance |
| 9 | clear | 4.88 | True | Finance, Legal |
| 10 | vague | 2.51 | False | [] |
| 11 | delegation | 9.02 | True | HR, IT, Finance |
| 12 | clear | 3.14 | True | Engineering, Marketing |
| 13 | vague | 2.60 | False | [] |
| 14 | delegation | 3.60 | True | HR, IT, Finance |
| 15 | clear | 3.41 | True | Admin, Research |

| Case | Min (s) | Max (s) | Mean (s) | Stdev (s) |
|---|---|---|---|---|
| vague | 2.51 | 3.32 | 2.77 | 0.32 |
| delegation | 3.60 | 9.02 | 5.93 | 1.98 |
| clear | 3.14 | 5.62 | 4.38 | 1.06 |


---

## 2. OpenAI `reasoning_effort` parameter shape (live gpt-5.5)


| Shape | Result |
|---|---|
| Top-level `reasoning_effort="low"` | Accepted — content returned, `reasoning_tokens` in usage |
| Nested `reasoning={"effort": "low"}` | Rejected — `TypeError: create() got an unexpected keyword argument 'reasoning'` |
| Key omitted | Accepted — model default (medium) |

---

## 3. Planning: medium vs low (single pass, then 7×3)


| Case | Medium ok | Low ok | Med reasoning tokens | Low reasoning tokens | Med s | Low s |
|---|---|---|---|---|---|---|
| vague | PASS | PASS | 57 | 62 | 3.75 | 2.78 |
| delegation | PASS | PASS | 179 | 46 | 5.58 | 4.16 |
| clear IT/OP | PASS | PASS | 153 | 44 | 7.28 | 3.51 |
| 4-dept SME | PASS | PASS | 54 | 41 | 2.44 | 1.87 |
| finance + JS multiturn | PASS | PASS | 392 | 144 | 8.46 | 4.35 |
| **TOTAL** | **all** | **all** | **835** | **337** | **27.5** | **16.7** |

`Repeated trial (7 cases × 3 repeats)`:

| Case | Med min / mean / max (s) | Low min / mean / max (s) | Mean Δ |
|---|---|---|---|
| vague | 2.71 / 3.86 / 5.42 | 2.30 / 3.20 / 4.59 | −17% |
| delegation | 4.67 / 5.21 / 5.64 | 3.90 / 4.52 / 5.12 | −13% |
| clear_IT_OP | 4.47 / 4.92 / 5.48 | 3.40 / 3.96 / 4.33 | −19% |
| scenario4_count | 2.24 / 2.86 / 3.90 | 2.33 / 2.53 / 2.76 | −12% |
| finance_JS_multiturn | 9.79 / 10.33 / 11.00 | 5.21 / 5.57 / 6.21 | −46% |
| qualifier_clause | 6.93 / 7.46 / 8.20 | 4.32 / 4.40 / 4.57 | −41% |
| flat_inventory | 5.29 / 6.04 / 6.49 | 4.41 / 4.74 / 5.22 | −22% |

| Case | Med mean reasoning tokens | Low mean reasoning tokens | Correctness |
|---|---|---|---|
| vague | 92.3 | 55.7 | both |
| delegation | 154.3 | 72.3 | both |
| clear_IT_OP | 107.7 | 69.3 | both |
| scenario4_count | 56.0 | 44.3 | both |
| finance_JS_multiturn | 509.0 | 151.7 | both |
| qualifier_clause | 283.3 | 103.3 | both |
| flat_inventory | 239.3 | 105.3 | both |

---

## 4. Escalated GPT-5.5 output vs reasoning by design size


| Departments | Reasoning tokens | Content tokens | Total vs 8000 ceiling |
|---|---|---|---|
| 5 | 404 (7% of then-headroom) | 1,425 | 23% |
| 10 | 485 (8%) | 2,839 | 42% |
| 15 | 512 (9%) | 3,556 | 51% |

---

## 5. Core-switch prompt ambiguity (primary Groq, Llama 3.3)



| Departments | Baseline (3 runs each) | Sharpened |
|---|---|---|
| 2 | 2/3 switches, core 0/3, accepted 0/3 | 3/3 switches, core 3/3, accepted 3/3 |
| 5 | 5/6 switches, core 0/3, accepted 0/3 | 6/6 switches, core 1/1, accepted 1/1 |
| 10 | 10/11 switches, core 0/3, accepted 0/3 | not run |
| 15 | 15/16 switches, core 0/3, accepted 0/3 | not run |



---

## 6. Topology escalated: medium vs low (4 sizes × 2 efforts × 3 reps = 24 calls)


| Departments | Med mean wall time (s) | Low mean wall time (s) | Mean Δ |
|---|---|---|---|
| 2 | 20.26 | 12.63 | −38% |
| 5 | 26.33 | 19.34 | −27% |
| 10 | 34.35 | 33.62 | −2% |
| 15 | 41.41 | 48.98 | +18% |


| Departments | Med mean reasoning tokens | Low mean reasoning tokens |
|---|---|---|
| 2 | 504.0 | 109.3 |
| 5 | 397.7 | 135.3 |
| 10 | 490.3 | 125.7 |
| 15 | 512.0 | 144.3 |



| Departments | Med mean content tokens | Low mean content tokens |
|---|---|---|
| 2 | 644 | 901 |
| 5 | 1,829 | 1,644 |
| 10 | 2,497 | 3,215 |
| 15 | 3,566 | 5,229 |



| Departments | Med $ | Low $ | Δ |
|---|---|---|---|
| 2 | 0.0398 | 0.0357 | −10% |
| 5 | 0.0727 | 0.0593 | −18% |
| 10 | 0.0965 | 0.1072 | +11% |
| 15 | 0.1302 | 0.1691 | +30% |

Sum of means: $0.339 → $0.371 (+9%).

---

## 7. threshold (escalated effort by department count)


| Size | Effort sent | Correctness (gate + structural) |
|---|---|---|
| 5 × 4 | `'low'` every time | 4/4 PASS (12 nodes each) |
| 10 × 4 | `None` (medium) every time | 4/4 PASS (22 nodes each) |


---

## 8. Groq Free-tier TPM (confirmed on this org)


| Plan | `qwen/qwen3.6-27b` | `openai/gpt-oss-120b` |
|---|---|---|
| Free (this org) | 30 RPM · 1K RPD · **8K TPM** · 200K TPD | Same: 30 / 1K / 8K / 200K |
| Developer (docs) | 250K TPM · 1K RPM | Same: 250K TPM · 1K RPM |

---

## 9. Qwen primary swap before `reasoning_effort="none"` / 5700 cap


| Metric | Result |
|---|---|
| API success | 1/8 |
| Gate accept (JSON as returned) | 0/8 |
| Attempt 0 would avoid escalation | 0/8 |

---

## 10. Disabling Qwen thinking (`reasoning_effort="none"`)


| Call | `<think>` present | Gate |
|---|---|---|
| n2_a | none | accepted |
| n2_b | none | accepted |

---

## 11. Primary token budget at `max_tokens=5000` (not production)


| Departments | Prompt tokens | Completion tokens | `finish_reason` | Prompt + 5000 reserved | Under 8000 TPM? | Quality gate |
|---|---|---|---|---|---|---|
| 2 | 1,306 | 1,550 | stop | 6,306 | Yes | Accepted |
| 5 | 1,510 | 2,724 | stop | 6,510 | Yes | Accepted |
| 10 | 1,859 | 4,879 | stop | 6,859 | Yes | Accepted |
| 15 | 2,214 | 5,000 | length | 7,214 | Yes | Rejected (truncated JSON) |

---

## 12. Traced pipeline at production primary cap (5700)


| Departments | Topology source | Attempt 0 (primary) | Attempt 1 (escalated) | Gate | Qwen prompt tokens | Qwen completion tokens |
|---|---|---|---|---|---|---|
| 2 | groq | Accepted | Not used | accepted | 1,346 | 1,369 |
| 10 | groq | Accepted | Not used | accepted | 1,900 | 5,340 |
| 15 | openai_escalated | Rejected (unterminated JSON) | Accepted | primary rejected → escalated accepted | 2,254 | 5,700 |

| Departments | LangWatch trace |
|---|---|
| 2 | https://app.langwatch.ai/toposcribe-9prTbV/traces/8f918bcf1bd83374f73926d586567460 |
| 10 | https://app.langwatch.ai/toposcribe-9prTbV/traces/0b02b7f2ee92ef0ffc8f861cc7854600 |
| 15 | https://app.langwatch.ai/toposcribe-9prTbV/traces/8cf316621c3971ff69b40ccc001cb0de |


| Departments | Nested spans |
|---|---|
| 2 | Generate Network Topology → Planning Agent (tier=planning, effort=low) → ChatCompletion gpt-5.5 (699 / 303); Topology Agent (tier=primary, effort=none, attempt=0, source=groq, gate=accepted) → Completions qwen/qwen3.6-27b (1346 / 1369) |
| 10 | Same shape; Planning gpt-5.5 717 / 671; Topology primary accepted; Qwen 1900 / 5340 |
| 15 | Planning gpt-5.5 727 / 881; Topology Agent primary rejected (Qwen 2254 / 5700); Topology Agent escalated accepted (gpt-5.5 1974 / 4304) |

---

## 13. Automated regression suite


| Checkpoint | Result |
|---|---|
| After Planning `reasoning_effort="low"` | 135 passed |
| After Lever 1 threshold tests | 142 passed |
| After Groq Qwen model-string swap | 142 passed, 1 warning |
| After primary `max_tokens=5700` | 142 passed, 1 warning |


---

## 14. Run-log files (evaluation source of record)


| File | Covers | Status | Run numbering |
|---|---|---|---|
| `scenario_runs.csv` | Part 1 (single-model pipeline, no escalation) | Frozen — no new rows | 1–95 |
| `scenario_runs_part2.csv` | Part 2 (model escalation + topology retry gate) | Active | Restarts at 1 |
