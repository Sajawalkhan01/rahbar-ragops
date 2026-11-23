# Real-LLM spot check (negative result)

Command: `python -m ragops.evaluation.suite --label llm_spotcheck --experiment experiments/baseline/baseline.yaml --provider ollama-host --limit 6 --repeat 1`
Result file: `eval/results/suite-llm_spotcheck-20261123T142750Z.json`. Model `llama3.2:3b` on CPU only (host Ollama), first 6 golden questions q01-q06.

Outcome: **0 of 6 produced an accepted answer.** Every question took about 185-193 s and ended in the fallback message
("I could not produce a reliable answer ..."). The log shows 14 "model output rejected" lines, so the provider's output
validation (JSON shape / citations) rejected the model's replies and retries ran out. false_abstention_rate = 1.0, answer_correctness = 0.0.

What this does and does not show:
- It shows the pipeline degrades safely: no unvalidated model text reached the user.
- It does NOT show the model is "bad" in general: with a CPU-only 3B model, speed (about 1.5 tokens/s) and strict JSON-output validation interact.
  The exact cause of each rejection (timeout vs malformed JSON vs invalid citation) was not analysed.
- The deterministic extractive provider remains the basis for all suite numbers in the report.
