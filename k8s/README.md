# RAHBAR + RAGOps on Kubernetes (minikube)

Everything below was run on minikube v1.37 (Docker driver, containerd) inside WSL2, namespace `ragops`.
Output of each step is saved unmodified in `reports/evidence/F*.txt`; result files and traces copied out of the
cluster are in `eval/results/k8s/` and `traces/logs/k8s/`.

## What runs

| Object | Kind | Notes |
| --- | --- | --- |
| `chroma` | StatefulSet + PVC `data-chroma-0` | vector store, 1 replica |
| `redis` | Deployment | semantic cache |
| `api` | Deployment, 2 replicas | `RollingUpdate`, `maxSurge: 1`, `maxUnavailable: 0`; readiness = collection exists |
| `api-candidate` | Deployment + Service | candidate on its own collection `rahbar_c200` |
| `ragops-config` | ConfigMap | environment for every pod (embedding model stated once) |
| `release-thresholds` | ConfigMap | gate thresholds, mounted as `/app/config/release_thresholds.yaml` |
| `ragops-data`, `ragops-results`, `ragops-traces` | PVCs | data lake + ledger; result files; JSONL traces |
| `ingest`, `ingest-candidate`, `ingest-batch-b` | Jobs | the only writers of the vector store |
| `ingest-cron` | CronJob `0 */6 * * *`, `concurrencyPolicy: Forbid` | scheduled ingestion of `/data/inbox/incoming` |
| `eval`, `eval-candidate`, `eval-candidate-topk3`, `eval-candidate-bad` | Jobs | evaluation + gate; exit non-zero when the gate fails |

One image, `ragops:v1`, for the API, ingestion and evaluation (`imagePullPolicy: IfNotPresent`).

## Prerequisites and image

* WSL2 or Linux, Docker, `minikube`, `kubectl`. A model server for embeddings on the host: Ollama listening on `0.0.0.0:11434`
  with `nomic-embed-text` (pods reach it at `http://host.minikube.internal:11434`).
* `minikube start --memory=3500 --cpus=3`
* **Image.** `docker build -t ragops:v1 .` uses `Dockerfile`. **That build did not finish on the network used for this
  assignment** (pip and apt downloads stalled), so it is not verified. The image actually deployed was built offline with
  `bash scripts/build-image-local.sh` (`Dockerfile.local`): it copies the Python packages from the virtualenv the tests and
  suites were run with. Consequence: **the cluster image has no tesseract/poppler**, so scanned PDFs cannot be OCR'd inside
  the cluster. Everything ingested here has a text layer or is Markdown/HTML.
* `minikube image load ragops:v1`

## Deploy

```bash
kubectl apply -k k8s/                      # namespace, PVCs, ConfigMaps, Chroma, Redis, API, candidate
kubectl get pods -n ragops                 # api pods stay 0/1 until the collection exists (readiness), by design
```

## Load documents and ingest (single writer)

```bash
kubectl apply -f k8s/jobs/loader-pod.yaml && kubectl wait --for=condition=Ready pod/loader -n ragops
kubectl exec -n ragops loader -- mkdir -p /data/inbox/batch_a /data/inbox/batch_b
kubectl cp data/inbox/batch_a/. ragops/loader:/data/inbox/batch_a
kubectl cp eval/batch_b/.      ragops/loader:/data/inbox/batch_b

kubectl apply -f k8s/ingest-job.yaml                       # Batch A -> collection rahbar   (601 chunks, 28 min on CPU)
kubectl apply -f k8s/jobs/ingest-candidate.yaml            # Batch A -> rahbar_c200, chunk 200 (726 chunks)
# take the baseline BEFORE Batch B changes the data:
kubectl apply -f k8s/eval-job.yaml                         # baseline suite, run twice
kubectl apply -f k8s/jobs/ingest-batch-b.yaml              # Batch B -> rahbar (18 files, 26 chunks embedded, 10 quarantined)
kubectl logs -n ragops job/ingest --tail=3                 # reports also land on the results volume
kubectl apply -f k8s/ingest-cronjob.yaml                   # scheduled run; trigger by hand:
kubectl create job ingest-cron-manual --from=cronjob/ingest-cron -n ragops
```

**Single writer.** Only the ingestion Jobs/CronJob mount the data volume read-write and set `RAGOPS_ROLE=ingestor`; the API pods
do not mount it and are not given the role (the writer refuses to start without it). The writer also takes a file lock on the data volume, and the CronJob uses
`concurrencyPolicy: Forbid`. The Jobs were run one after another. **A deliberate two-writers-at-once test was not run in
the cluster**; the lock and the role check are unit-tested only (`tests/test_ingestion.py`).

## Evaluate, gate, and reject a candidate

```bash
kubectl apply -f k8s/jobs/eval-candidate.yaml              # chunk-200 candidate vs the baseline on the results volume
kubectl get job eval-candidate -n ragops                   # Failed = gate rejected (the Job exits 1)
kubectl logs job/eval-candidate -n ragops | grep -A14 "RELEASE GATE"
kubectl apply -f k8s/jobs/eval-candidate-topk3.yaml        # top_k 3 candidate: gate PASS, Job Complete
# k8s/jobs/eval-candidate-bad.yaml (top_k 1, floor 0.90) exists but was NOT run in the cluster; the bad candidate's
# gate FAIL was shown outside the cluster (eval/results/gate-candidate-bad-*.json). The cluster evidence for a rejected
# candidate is chunk-200 above.
```

Results here (`reports/evidence/F3-*`): chunk-200: recall@5 0.957 (up) but MRR 0.780 and nDCG@5 0.816 fall more than the
allowed 0.03 -> **FAIL, release rejected, never rolled out** (its Deployment `api-candidate` keeps serving only its own
collection and is not promoted). top_k 3: all metrics equal to baseline -> **PASS**. The numbers are the same as the
earlier run outside the cluster (recall@5 0.913, MRR 0.855 for the baseline in both).

**Change a threshold, same image** (`reports/evidence/F2-threshold-change-gate-pass.txt`):
```bash
bash scripts/k8s-threshold-demo.sh relax       # ConfigMap: max_mrr_drop 0.03 -> 0.08, max_ndcg5_drop 0.03 -> 0.05
kubectl delete job eval-candidate -n ragops && kubectl apply -f k8s/jobs/eval-candidate.yaml   # same candidate
bash scripts/k8s-threshold-demo.sh restore     # put the committed thresholds back
```
The same candidate that failed now passes (MRR drop 0.075 <= 0.08), with no image rebuild. This shows the gate is a
policy you can change, not that the chunk-200 candidate became better: it did not.

## Release, bad release, rollback

```bash
bash scripts/k8s-release-demo.sh good    # rolling update to the gate-PASSED candidate: TOP_K 5 -> 3 (revision 2)
bash scripts/k8s-release-demo.sh bad     # a release that skipped the gate: rahbar_c200, TOP_K=1, floor 0.90 (revision 3)
kubectl rollout status deployment/api -n ragops
kubectl rollout undo deployment/api -n ragops             # = bash scripts/k8s-release-demo.sh undo
kubectl rollout history deployment/api -n ragops
```
With `maxUnavailable: 0` the old pods were removed only after new ones were Ready (`F4`, `F5`, `F6`). After the bad
release the trace of a live query shows `collection: rahbar_c200` (index_id `b5b904ab...`), and a two-part question that
works on `rahbar` is refused ("the documents do not cover that question", `F5b`). After `rollout undo` the new trace shows
`collection: rahbar`, `embedding_model_version: 0a109f422b47`, `index_id: f81ed7dd...`, the same as before the bad
release. `rollout undo` returns to the previous *revision* (the top_k 3 release), not to revision 1; the history renumbers it as 4.
Note: the undo query had no `top_score` in its trace because the semantic cache answered it.

## Metrics and traces

```bash
kubectl port-forward -n ragops svc/api 8000:8000          # then http://localhost:8000/metrics (Prometheus)
kubectl logs -n ragops -l app=api --tail=50               # each query = one JSON trace line on stdout and in /traces
kubectl apply -f k8s/jobs/results-reader.yaml             # pod to copy results/traces out with kubectl cp
```

## Resources (F5): measured, and what is not

`kubectl top` did not work here (metrics-server could not scrape the kubelet: "timeout to access kubelet"), so
`scripts/k8s-measure.sh` reads `crictl stats` inside the node (`F7`). One sample idle and one right after 30 queries:

| Pod | Measured memory | Request | Limit |
| --- | --- | --- | --- |
| api | about 77-102 MB | 192Mi | 384Mi |
| chroma | about 100-160 MB | 256Mi | 1Gi |
| redis | about 7 MB | 64Mi | 128Mi |
| ingest / eval Jobs | **not measured** (finished before sampling) | 512Mi / 384Mi | 1536Mi / 768Mi |

Limits are about 3-4x the measured API/Chroma use, to survive spikes. For the Jobs the only evidence is that they
completed with no restart and no OOMKill under those limits (`F7`); that shows the limits are sufficient, not minimal.
CPU samples are single instants and say little; CPU requests/limits are conservative guesses.

## Not done / known limits

* No test of two concurrent writers in the cluster (see above). No HPA or Ingress is used by A3.
* `kubectl top` unavailable on this machine (see above).
* The extractive generator is used in the cluster; the LLM is not (CPU-only 3B model: 0 of 6 answers accepted, `eval/results/LLM-SPOTCHECK.md`).
* `k8s/base` and `k8s/overlays` are the Assignment 2 manifests, kept for history and not used by A3.

## Cleanup

```bash
kubectl delete namespace ragops        # removes everything above, including the PVCs and their data
minikube stop                          # or: minikube delete
```
