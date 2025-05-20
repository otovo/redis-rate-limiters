#!/bin/bash
set -euo pipefail

# Wait for all Redis nodes to be ready
for host in 10.5.0.2 10.5.0.3 10.5.0.4 10.5.0.5 10.5.0.6 10.5.0.7; do
  echo "Waiting for Redis at $host:6379..."
  for i in {1..30}; do
    if redis-cli -h $host -p 6379 PING > /dev/null 2>&1; then
      echo "$host:6379 is up."
      break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
      echo "Redis at $host:6379 did not become available in time!" >&2
      exit 1
    fi
  done
done

# Create the cluster with 3 masters
redis-cli --cluster create 10.5.0.2:6379 10.5.0.3:6379 10.5.0.4:6379 --cluster-yes

# Get master node IDs
master1="$(redis-cli -u redis://127.0.0.1:6380 cluster nodes | awk '$3 ~ /master/ {print $1}' | sed -n 1p)"
master2="$(redis-cli -u redis://127.0.0.1:6380 cluster nodes | awk '$3 ~ /master/ {print $1}' | sed -n 2p)"
master3="$(redis-cli -u redis://127.0.0.1:6380 cluster nodes | awk '$3 ~ /master/ {print $1}' | sed -n 3p)"

# Add slaves
redis-cli --cluster add-node 10.5.0.5:6379 10.5.0.2:6379 --cluster-slave --cluster-master-id $master1
redis-cli --cluster add-node 10.5.0.6:6379 10.5.0.2:6379 --cluster-slave --cluster-master-id $master2
redis-cli --cluster add-node 10.5.0.7:6379 10.5.0.2:6379 --cluster-slave --cluster-master-id $master3

# Force rebalance to ensure all slots are covered (no data, so safe)
redis-cli --cluster rebalance --cluster-use-empty-masters 10.5.0.2:6379 --cluster-yes

# Wait for cluster to be healthy and all slots to be covered using redis-cli --cluster check
max_attempts=30
attempt=1
while true; do
    echo "Checking cluster health and slot coverage (attempt $attempt)..."
    redis-cli --cluster check 10.5.0.2:6379
    if redis-cli --cluster check 10.5.0.2:6379 | grep -q "[OK]"; then
        echo "All slots are covered and cluster is healthy."
        break
    fi
    if [ $attempt -ge $max_attempts ]; then
        echo "Cluster slots are not fully covered after $max_attempts attempts. Exiting with error."
        exit 1
    fi
    attempt=$((attempt+1))
    sleep 2
done

# Final check
redis-cli --cluster check 10.5.0.2:6379
