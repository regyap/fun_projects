# Continuous Kubernetes Troubleshooting Agent

A continuously running, **read-only** monitoring agent. It polls pods, detects selected failures, collects Kubernetes events and logs, optionally asks an LLM for a diagnosis, and appends incidents to a JSONL file. It does **not** remediate or modify the cluster.

## Run

Requires Python 3.10+, kubectl, a working kubeconfig, and Kubernetes permissions to get/list pods and get pod logs.

```powershell
cd continuous-k8s-agent
python -m pip install -r requirements.txt
kubectl get pods -n default
$env:K8S_NAMESPACE="default"
$env:POLL_SECONDS="60"
# Optional: enables AI-generated diagnosis
$env:OPENAI_API_KEY="your-api-key"
python agent.py
```

Stop with Ctrl+C. Without an API key, it records diagnostic evidence without calling an LLM. Results are appended to `incidents.jsonl`. Keep this file private: logs may contain sensitive information.

## Loop design

Observe → detect unhealthy pod → gather evidence → diagnose → persist result → wait → observe again. Repeated identical incidents are deduplicated during a running process. This is a learning prototype, not a production controller: deduplication is in-memory, polling may miss transient failures, and no automated repair is performed.

## Next improvements

- Add unit tests and mocked kubectl responses
- Persist incident state across restarts
- Add backoff, rate limits, and retention controls
- Redact secrets before sending logs to an LLM
- Use Kubernetes watch API instead of polling
- Add approval-gated remediation and verification
- Package as a container with least-privilege RBAC
