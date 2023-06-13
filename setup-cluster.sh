redis-cli --cluster create 10.5.0.2:6379 10.5.0.3:6379 10.5.0.4:6379 --cluster-yes

master1="$( echo "$(redis-cli -u redis://127.0.0.1:6380 cluster nodes)" | sed -n '1p' | awk '{print $1; exit}')"
master2="$( echo "$(redis-cli -u redis://127.0.0.1:6380 cluster nodes)" | sed -n '2p' | awk '{print $1; exit}')"
master3="$( echo "$(redis-cli -u redis://127.0.0.1:6380 cluster nodes)" | sed -n '3p' | awk '{print $1; exit}')"

echo "Connecting to $master1"
redis-cli --cluster add-node 10.5.0.5:6379 10.5.0.2:6379 --cluster-slave --cluster-master-id $master1
echo "Connecting to $master2"
redis-cli --cluster add-node 10.5.0.6:6379 10.5.0.2:6379 --cluster-slave --cluster-master-id $master2
echo "Connecting to $master3"
redis-cli --cluster add-node 10.5.0.7:6379 10.5.0.2:6379 --cluster-slave --cluster-master-id $master3
