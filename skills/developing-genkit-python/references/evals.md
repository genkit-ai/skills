# Evals — Genkit Python (Deprecated in 0.13; Removed in 1.0)

> **Deprecation & Removal Warning:** Evaluators (`ai.define_evaluator`, `ai.define_batch_evaluator`, `ai.evaluate`, `genkit.evaluator`, and `genkit-evaluators`) are **deprecated in Genkit Python 0.13** (`genkit-evaluators` 0.13 requires `genkit<1`) and **removed in Genkit 1.0** (the release right after 0.13) while evaluators are redesigned across all Genkit SDKs.
> - **New projects:** do not add `genkit-evaluators` or `define_evaluator` unless you intend to stay pinned to `genkit==0.13.*`. Prefer standard `pytest` assertions against your flows and prompts until the redesigned evaluator API ships.
> - **Migrating from 0.12:** stop and ask the developer before porting evaluator code (see [Migrating from 0.12 to 0.13](migrating-from-0.12.md)).

The patterns below document the exact `0.13.*` evaluator API for projects staying on the 0.13 release line.

---

## Install (0.13 Only)

```bash
uv add 'genkit-evaluators==0.13.*'
```

## Two Evaluator Types

1. **Built-in** — provided by `genkit-evaluators`, registered via `register_genkit_evaluators(ai)` (`genkitEval/regex`, `genkitEval/deep_equal`, `genkitEval/jsonata`). Deterministic built-in evaluators do not require a model plugin or `GEMINI_API_KEY`.
2. **BYO** — custom row-by-row (`ai.define_evaluator`) or batch (`ai.define_batch_evaluator`) functions, including LLM judges.

## Dataset Format

```json
[
  {"testCaseId": "case1", "input": "x", "output": "banana", "reference": "ba?a?a"},
  {"testCaseId": "case2", "input": "x", "output": "apple",  "reference": "ba?a?a"}
]
```

Fields: `testCaseId`, `input`, `output`, `reference` (optional for reference-free evaluators).

## Built-In Evaluators & Programmatic Execution

```python
from genkit_evaluators import register_genkit_evaluators

register_genkit_evaluators(ai)

# `ai.evaluate` runs one evaluator per call (`evaluator=`, singular), takes `config=`
# (renamed from `options=`), and returns `list[EvaluatorResponse]` directly (no `.root`).
results = await ai.evaluate(
    evaluator='genkitEval/regex',
    dataset=my_dataset,
    config={},
)
for row in results:
    print(row.test_case_id, row.evaluation)
```

## BYO Evaluator (`EvaluatorResponse`, `Score`, `ScoreStatus`, `ScoreDetails`)

In 0.13, `EvalFnResponse` is renamed to `EvaluatorResponse`, `EvalStatusEnum` to `ScoreStatus`, and `Details` to `ScoreDetails`. `evaluation` takes a `list[Score]`, and `ai.define_evaluator` takes `(name, fn)` positionally with required keyword-only `display_name=` and `definition=`:

```python
from genkit.evaluator import (
    BaseDataPoint,
    EvaluatorResponse,
    Score,
    ScoreDetails,
    ScoreStatus,
)


async def exact_match(datapoint: BaseDataPoint, _options: object = None) -> EvaluatorResponse:
    output = str(datapoint.output or '').strip()
    reference = str(datapoint.reference or '').strip()
    passed = output == reference
    return EvaluatorResponse(
        test_case_id=datapoint.test_case_id or '',
        evaluation=[
            Score(
                score=1.0 if passed else 0.0,
                status=ScoreStatus.PASS if passed else ScoreStatus.FAIL,
                details=ScoreDetails(reasoning='Exact match check'),
            )
        ],
    )


ai.define_evaluator(
    'byo/exact_match',
    exact_match,
    display_name='Exact Match',
    definition='Checks exact match of output against reference.',
)
```

For batch evaluation across the whole dataset at once, register `async def my_batch_eval(req: EvaluatorRequest) -> list[EvaluatorResponse]:` with `ai.define_batch_evaluator('byo/batch', my_batch_eval, display_name='...', definition='...')` (`from genkit.evaluator import EvaluatorRequest`).

## LLM-Based Judge

`prompts/judge.prompt`:

```yaml
---
model: googleai/gemini-flash-latest
input:
  schema:
    output: string
    reference: string
---
Score how well the candidate matches the reference from 0.0 to 1.0.
Reply with ONLY a number (e.g. 0.8), nothing else.

Reference: {{reference}}
Candidate: {{output}}
```

```python
import re
from genkit.evaluator import BaseDataPoint, EvaluatorResponse, Score, ScoreStatus
from genkit_google_genai import GoogleAI


async def llm_eval(datapoint: BaseDataPoint, _options: object = None) -> EvaluatorResponse:
    rendered = await ai.prompt('judge').render(
        {'output': str(datapoint.output), 'reference': str(datapoint.reference)}
    )
    response = await ai.generate(
        model=GoogleAI.gemini('gemini-flash-latest'),
        messages=rendered.messages,
    )
    m = re.search(r'0?\.\d+|1\.0|[01]', (response.text or '').strip())
    score = float(m.group(0)) if m else 0.0
    return EvaluatorResponse(
        test_case_id=datapoint.test_case_id or '',
        evaluation=[
            Score(
                score=score,
                status=ScoreStatus.PASS if score >= 0.5 else ScoreStatus.FAIL,
            )
        ],
    )


ai.define_evaluator(
    'byo/llm_judge',
    llm_eval,
    display_name='LLM Judge',
    definition='Scores candidate vs reference with a judge model.',
)
```

Built-in `genkitEval/regex` scores are `bool` (`True` / `False`); BYO numeric scores are typically `0.0`–`1.0` — normalize before aggregating.

## CLI Execution

`genkit eval:run` requires an active Genkit runtime (either already running via `genkit start` or launched inline after `--`):

```bash
# One-shot: launches the app runtime, evaluates, and exits
genkit eval:run datasets/my_dataset.json --evaluators=genkitEval/regex,byo/exact_match -- uv run src/main.py

# Write machine-readable results to a file
genkit eval:run datasets/my_dataset.json --evaluators=byo/exact_match --output=eval_out.json -- uv run src/main.py
```

`No runtimes found` means no Genkit runtime is active — pass `-- uv run src/main.py` or start `genkit start` in another terminal.
