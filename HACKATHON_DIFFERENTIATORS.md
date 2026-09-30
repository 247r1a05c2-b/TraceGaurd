# TraceGaurd — What makes the demo distinctive

TraceGaurd is designed as an incident-response control plane rather than a chatbot that merely explains an error.

## 1. Evidence-weighted confidence

Every agent exposes a 0–100 confidence/quality score and the basis used to calculate it. Root-cause confidence is separate from pipeline confidence. The UI should label these as estimates, never as guaranteed accuracy.

## 2. Confidence for every agent

| Agent | Primary evaluation metric |
|---|---|
| Ingestion Agent | Data quality |
| Noise Filter Agent | Signal quality |
| Correlation Agent | Correlation strength |
| RAG Agent | Retrieval relevance |
| Root Cause Agent | Root-cause confidence |
| Diagnostic Agent | Diagnosis coverage |
| Guardrail Agent | Safety gate score |
| Timeline Agent | Timeline completeness |

## 3. Evidence chain, not unexplained AI output

The RCA screen can connect the hypothesis to incident signals, RAG documents, correlations, diagnosis steps and the proposed action.

## 4. Human-in-the-loop safety boundary

A risky remediation is not treated as authorized merely because an LLM proposed it. The Guardrail Agent classifies the action and the engineer explicitly approves before controlled execution.

## 5. Closed-loop verification

TraceGaurd is designed to show the result of remediation, including verification signals and audit history, instead of stopping at “here is a suggested fix”.

## 6. Multi-agent observability

The system exposes the execution trace of each agent, its output, status, metric, confidence and measurement basis. This lets judges inspect the orchestration rather than accepting a black-box “AI result”.

## 7. RAG-grounded diagnosis

RAG is shown as a visible evidence layer with retrieved documents and relevance scores, rather than being hidden behind a generic “RAG enabled” label.

## 8. LLM + deterministic fallback

The LLM can produce root-cause hypotheses and diagnostic plans when configured. If the external LLM is unavailable, deterministic safety logic still permits the demo workflow to run.

## 9. Production-oriented identity and persistence

Engineer authentication, client identities, approvals, remediation records and audit events are backed by the application's database layer.

## 10. The right claim to make on stage

Do not claim “TraceGaurd is 94% accurate” unless a ground-truth evaluation dataset supports that statement. Say:

> “TraceGaurd currently reports a 94% evidence-weighted root-cause confidence for this incident. The score is calculated from observed signals, correlations and retrieved evidence; it is not a guarantee of correctness.”

That distinction makes the evaluation metric technically credible.
