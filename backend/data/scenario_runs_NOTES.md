# Run log provenance notes

There are two run-log files in this directory. Both are appended automatically by
`POST /api/design/generate` (`_append_run_row` in `backend/app/api/design.py`).
Every call to that endpoint adds a row, including calls made while developing or
debugging, so rows that do not represent a valid measurement have to be removed
by hand and recorded here.

| File | Covers | Status | Run numbering |
| --- | --- | --- | --- |
| `scenario_runs.csv` | Part 1 (single-model pipeline, no escalation) | Frozen — receives no new rows | 1–95 |
| `scenario_runs_part2.csv` | Part 2 (model escalation + topology retry gate) | Active — all new runs land here | Restarts at 1 |

## Why the split (Part 2, Phase 6)

Part 2 changed what a run *is*. A Part 1 run made exactly one topology attempt on
Groq and silently fell back to the deterministic SME layout when that attempt was
rejected. A Part 2 run makes up to four attempts, escalates to GPT-5.5 after the
first, and records which model actually produced the accepted design.

Appending Part 2 rows to `scenario_runs.csv` would have put two different
experimental conditions in one table under identical column headings, so any
aggregate over the whole file (mean runtime, success rate) would silently mix
them. Runtime in particular is not comparable: a Part 2 run that escalates spends
tens of seconds in additional model calls that no Part 1 run could have made.

`scenario_runs.csv` is therefore frozen as the pre-escalation baseline and must
not be deleted or edited. Run numbering restarts at 1 in the new file because it
is a separate dataset, not a continuation — a "Run 12" exists in both files and
refers to different runs.

## Columns

`scenario_runs_part2.csv` keeps all seven original columns and adds three:

- `Topology Source` — `groq`, `openai_escalated`, or `deterministic_fallback`.
  Empty for runs that ended before topology generation (e.g. clarification).
- `Topology Retries` — `topology_retry_count`, the number of topology attempts
  beyond the first.
- `Escalated` — `Yes` when `Topology Source` is set and is not `groq`. Runs that
  never reached topology generation are `No`, not `Yes`; an absent source is not
  evidence of escalation.

Note that the pre-existing `Retries` column means something different: it tracks
`retry_count`, the validation→config loop, and says nothing about topology
attempts or escalation. The two retry columns are independent.

Full per-attempt provenance (`agent`, `model`, `attempt`, `status`, `outcome`) is
not in the CSV. It is returned in the API response as `agent_trace`.

## Excluded rows

### `scenario_runs_part2.csv` run 1 — removed (Part 2, Phase 6)

Original row:

```
1,Yes,0,Yes,0,30.092,Success,openai_escalated,1,Yes
```

The row that created the file, from the invocation used to verify the new
columns. Excluded on two counts: it was a verification call rather than a
measurement, and its escalation was caused by the Groq daily token quota
(HTTP 429) rather than by the quality gate, so counting it would inflate the
escalation rate with a billing artifact.

Worth keeping as an observation even though the row is gone: the retry gate
handled a provider outage exactly as it handles a rejected design — attempt 0
failed with the 429, attempt 1 escalated to GPT-5.5, and the pipeline completed
successfully. Escalation therefore covers provider availability as well as
output quality.

### `scenario_runs.csv` run 96 — removed (Part 2, Phase 5)

Original row:

```
96,Yes,0,Yes,0,93.041,Success
```

Excluded because the row is not a valid observation of pipeline behaviour. It
was produced by a debugging invocation during Phase 5, while a defect in the
escalation path was still present: `max_completion_tokens` for gpt-5 class
models did not account for the fact that those models bill internal reasoning
against the completion budget. Every escalated topology attempt spent its whole
2000-token budget on reasoning and returned empty content with
`finish_reason="length"`, so all three retries failed and the run finished on
the deterministic SME fallback.

The row is misleading in three separate columns:

- `Result = Success` and `Design Generated = Yes` — the design came from the
  deterministic fallback, not from generation.
- `Retries = 0` — this column tracks `retry_count` (the validation→config loop).
  The run actually made four topology attempts, which that column does not
  capture.
- `Runtime = 93.041` — inflated by three escalated calls that could not have
  succeeded, so it does not characterise either the normal or the escalated path.

The defect was fixed in the same phase (`LLM_MAX_OUTPUT_TOKENS` and
`_REASONING_TOKEN_ALLOWANCE` in `backend/app/utils/llm.py`, plus an explicit
error when a model returns empty content). Runs recorded after that fix are
valid.

## Prompt revision affecting comparability (Part 2, pre-Phase 6)

The topology prompt was sharpened before Phase 6 to state the required device
inventory explicitly. Previously the only mention of a core switch sat in the
spatial-layout section, which Groq read as positioning advice rather than an
existence requirement; it omitted the core switch in 12 of 12 baseline runs
across 2, 5, 10 and 15 departments, and was rejected by the quality gate every
time. With the sharpened prompt it produced the correct inventory in 4 of 4 runs.

Escalation rates measured before that change reflect the prompt defect, not model
capability, and should not be compared against rows recorded afterwards. All rows
in `scenario_runs_part2.csv` use the sharpened prompt.
