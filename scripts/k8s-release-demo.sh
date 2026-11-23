#!/usr/bin/env bash
# Part F release, rejection and rollback on the live API Deployment (run from WSL, cluster must be up).
#   bash scripts/k8s-release-demo.sh good       rolling update to the gate-PASSED candidate (top_k 3)
#   bash scripts/k8s-release-demo.sh bad        a release that SKIPPED the gate (rahbar_c200, top_k 1, floor 0.90)
#   bash scripts/k8s-release-demo.sh undo       kubectl rollout undo, then a new query (trace shows the old collection)
#   bash scripts/k8s-release-demo.sh ask        one query only
# The candidate collection / settings are applied as env overrides on the Deployment, so each change is one revision.
cd "$(dirname "$0")/.." || exit 1
NS=ragops
Q="${Q:-What minimum CGPA must an undergraduate keep to avoid academic warning?}"

ask() {
  kubectl port-forward -n $NS svc/api 18000:8000 >/tmp/pf.log 2>&1 &
  PF=$!
  for i in $(seq 1 20); do curl -s -o /dev/null localhost:18000/healthz && break; sleep 1; done
  echo "--- POST /api/ask: $Q"
  curl -s -X POST localhost:18000/api/ask -H 'Content-Type: application/json' \
       -d "{\"question\": \"$Q\"}" | python3 -c "import json,sys; r=json.load(sys.stdin); print('answered_from_context:', r.get('answered_from_context')); print('answer:', (r.get('answer') or '')[:300]); print('trace_id:', r.get('trace_id'), '| citations:', len(r.get('citations') or []))"
  kill $PF 2>/dev/null
}
show_trace() {
  echo "--- newest trace line from the API pod (collection / embedding version actually used)"
  kubectl logs -n $NS -l app=api --tail=400 --max-log-requests=5 | grep '"type": "trace"' | tail -1 \
    | python3 -c "import json,sys; t=json.loads(sys.stdin.readline()); print(json.dumps({k:t.get(k) for k in ('trace_id','query','collection','collection_version','embedding_model','embedding_model_version','index_id','top_score','guardrails')}, indent=1))"
}
status() { kubectl rollout status deployment/api -n $NS --timeout=240s; kubectl get deploy api -n $NS; kubectl rollout history deployment/api -n $NS; }

case "$1" in
  good)
    kubectl set env deployment/api -n $NS TOP_K=3
    kubectl annotate deployment/api -n $NS kubernetes.io/change-cause="release candidate-topk3 (gate PASS): TOP_K 5 -> 3" --overwrite
    status; ask; show_trace ;;
  bad)
    kubectl set env deployment/api -n $NS CHROMA_COLLECTION=rahbar_c200 TOP_K=1 RELEVANCE_FLOOR=0.90
    kubectl annotate deployment/api -n $NS kubernetes.io/change-cause="BAD release, gate skipped: collection rahbar_c200, TOP_K=1, RELEVANCE_FLOOR=0.90" --overwrite
    status; ask; show_trace ;;
  undo)
    kubectl rollout undo deployment/api -n $NS
    status; ask; show_trace ;;
  ask) ask; show_trace ;;
  *) echo "usage: $0 good|bad|undo|ask"; exit 2 ;;
esac
