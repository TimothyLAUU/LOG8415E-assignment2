#!/usr/bin/env bash
# Provisions infra with Terraform, deploys containers, runs the test.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
KEY="$ROOT/keys/lab-key"
SSH_OPTS="-i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
WORKER_MODE="${WORKER_MODE:-ml}"    # export WORKER_MODE=fallback if needed

# 1. SSH key (generated once, never committed)
if [ ! -f "$KEY" ]; then
  mkdir -p "$ROOT/keys"
  ssh-keygen -t ed25519 -N "" -f "$KEY"
fi

# 2. Infrastructure
cd "$ROOT/terraform"
terraform init -input=false
terraform apply -auto-approve -input=false

ORCH_PUB=$(terraform output -raw orchestrator_public_ip)
W1_PUB=$(terraform output -json worker_public_ips  | python3 -c "import sys,json;print(json.load(sys.stdin)[0])")
W2_PUB=$(terraform output -json worker_public_ips  | python3 -c "import sys,json;print(json.load(sys.stdin)[1])")
W1_PRIV=$(terraform output -json worker_private_ips | python3 -c "import sys,json;print(json.load(sys.stdin)[0])")
W2_PRIV=$(terraform output -json worker_private_ips | python3 -c "import sys,json;print(json.load(sys.stdin)[1])")
cd "$ROOT"

# 3. Helpers
wait_ready() {  # wait until SSH works and Docker is installed
  until ssh $SSH_OPTS ubuntu@"$1" 'test -f /tmp/docker-ready' 2>/dev/null; do
    echo "  waiting for $1 ..."; sleep 10
  done
}

deploy_worker() {  # $1=public ip, $2=worker name
  wait_ready "$1"
  scp -r $SSH_OPTS "$ROOT/worker" ubuntu@"$1":~/
  ssh $SSH_OPTS ubuntu@"$1" \
    "cd ~/worker && printf 'WORKER_NAME=$2\nWORKER_MODE=$WORKER_MODE\n' > .env && docker compose up -d --build"
}

# 4. Workers (in parallel: image build is slow)
deploy_worker "$W1_PUB" worker1 &
deploy_worker "$W2_PUB" worker2 &
wait

# 5. Orchestrator
wait_ready "$ORCH_PUB"
scp -r $SSH_OPTS "$ROOT/orchestrator" ubuntu@"$ORCH_PUB":~/
ssh $SSH_OPTS ubuntu@"$ORCH_PUB" \
  "cd ~/orchestrator && printf 'WORKER1_IP=$W1_PRIV\nWORKER2_IP=$W2_PRIV\n' > .env && docker compose up -d --build"

# 6. Wait until both workers answer /health (checked from the orchestrator, port 5000 is private)
until ssh $SSH_OPTS ubuntu@"$ORCH_PUB" \
  "curl -sf http://$W1_PRIV:5000/health && curl -sf http://$W2_PRIV:5000/health" >/dev/null; do
  echo "  waiting for workers to load the model ..."; sleep 10
done

echo "$ORCH_PUB" > "$ROOT/orchestrator_ip.txt"
echo "System ready at http://$ORCH_PUB"

# 7. Test
python3 "$ROOT/test_requests.py" "$ORCH_PUB"