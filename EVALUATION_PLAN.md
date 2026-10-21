# TraceGaurd evaluation plan

This document defines an experiment plan; it contains **no measured results**. Record results only after running the experiments against a fixed test set.

## Research question

Does retrieval-grounded multi-agent incident analysis produce more useful, evidence-supported root-cause hypotheses than a simple baseline, without bypassing the approval gate?

## Dataset

Create a versioned, de-identified set of synthetic or public incident scenarios. Each case should include:
- Observed events and timestamps
- Service/environment metadata
- Relevant runbook or historical incident evidence
- Expected root-cause category and acceptable evidence references
- A label for whether a proposed action is read-only, requires approval, or must be blocked

Do not upload production logs, credentials, personal data, or confidential incident reports.

## Baselines

1. Rule-based/deterministic diagnosis without retrieval
2. Retrieval plus a single LLM call
3. Full TraceGaurd multi-agent workflow

Use the same incident inputs and knowledge base for every baseline. Pin model names, prompts, dependency versions, and test cases.

## Metrics

- Root-cause top-1 accuracy and macro-F1 against labeled cases
- Evidence precision: fraction of cited/retrieved evidence judged relevant
- Unsupported-claim rate from manual review
- Diagnosis completeness against a predefined checklist
- Guardrail violations: attempted or executed prohibited actions (target: zero)
- Human approval bypasses (target: zero)
- Median and p95 latency, token usage, and cost where measurable

Report per-category results, sample sizes, confidence intervals where appropriate, and representative failure cases. Do not present an LLM confidence score as a calibrated probability unless calibration has been tested.

## Reproducibility checklist

- [ ] Version the dataset and evaluation script.
- [ ] Record model/provider, prompt version, configuration, and random seed where applicable.
- [ ] Run each baseline on exactly the same cases.
- [ ] Save raw predictions and metric outputs without secrets or private incident data.
- [ ] Review failures manually and document limitations.
- [ ] Publish the results table only after a completed run.
