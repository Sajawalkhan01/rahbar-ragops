#!/usr/bin/env bash
# F5: measured resource use of the long-running pods, idle and under a short query load.
# metrics-server could not scrape the kubelet on this machine (kubectl top fails), so this reads the container
# runtime statistics inside the minikube node (crictl stats) instead. Values are one sample each, not a profile.
cd "$(dirname "$0")/.." || exit 1
stats() { minikube ssh -- "sudo crictl stats -a 2>/dev/null" | tr -d '\r' | grep -E "^CONTAINER|  (api|chroma|redis) " ; }
echo "== idle"; stats
kubectl port-forward -n ragops svc/api 18000:8000 >/dev/null 2>&1 & PF=$!
for i in $(seq 1 20); do curl -s -o /dev/null localhost:18000/healthz && break; sleep 1; done
python3 - <<'PY'
import json, urllib.request, time
qs = [json.loads(l)["question"] for l in open("eval/golden.jsonl", encoding="utf-8")][:30]
t0 = time.time()
for q in qs:
    req = urllib.request.Request("http://localhost:18000/api/ask", json.dumps({"question": q}).encode(), {"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=60).read()
print(f"sent {len(qs)} golden questions in {time.time()-t0:.1f}s")
PY
echo "== right after the load"; stats
kill $PF 2>/dev/null
echo "== configured requests / limits"
kubectl get pods -n ragops -o custom-columns='POD:.metadata.name,REQ_CPU:.spec.containers[0].resources.requests.cpu,REQ_MEM:.spec.containers[0].resources.requests.memory,LIM_CPU:.spec.containers[0].resources.limits.cpu,LIM_MEM:.spec.containers[0].resources.limits.memory'
echo "== OOMKilled / restarts"
kubectl get pods -n ragops -o jsonpath='{range .items[*]}{.metadata.name}{" restarts="}{.status.containerStatuses[0].restartCount}{" lastState="}{.status.containerStatuses[0].lastState.terminated.reason}{"\n"}{end}'
