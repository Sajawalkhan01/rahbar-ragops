#!/usr/bin/env bash
# F2: change a gate threshold in the ConfigMap, rerun the SAME evaluation Job on the SAME image, see the verdict change.
#   bash scripts/k8s-threshold-demo.sh relax     (max_mrr_drop 0.03 -> 0.08, max_ndcg5_drop 0.03 -> 0.05)
#   bash scripts/k8s-threshold-demo.sh restore   (back to the committed thresholds in k8s/20-configmaps.yaml)
cd "$(dirname "$0")/.." || exit 1
case "$1" in
  relax)
    kubectl get configmap release-thresholds -n ragops -o yaml \
      | sed -e 's/max_mrr_drop: 0.03/max_mrr_drop: 0.08/' -e 's/max_ndcg5_drop: 0.03/max_ndcg5_drop: 0.05/' \
      | kubectl apply -f - ;;
  restore)
    kubectl apply -f k8s/20-configmaps.yaml ;;
  *) echo "usage: $0 relax|restore"; exit 2 ;;
esac
kubectl get configmap release-thresholds -n ragops -o jsonpath='{.data.release_thresholds\.yaml}' | grep -E "max_mrr_drop|max_ndcg5_drop"
