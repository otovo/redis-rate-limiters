redis-cli --cluster create 10.5.0.2:6379 10.5.0.3:6379 10.5.0.4:6379 --cluster-yes

master1="$( echo "$(redis-cli cluster nodes)" | sed -n '1p' | awk '{print $1; exit}')"
master2="$( echo "$(redis-cli cluster nodes)" | sed -n '2p' | awk '{print $1; exit}')"
master3="$( echo "$(redis-cli cluster nodes)" | sed -n '3p' | awk '{print $1; exit}')"

redis-cli --cluster add-node 10.5.0.5:6379 10.5.0.2:6379 --cluster-slave --cluster-master-id $master1
redis-cli --cluster add-node 10.5.0.6:6379 10.5.0.2:6379 --cluster-slave --cluster-master-id $master2
redis-cli --cluster add-node 10.5.0.7:6379 10.5.0.2:6379 --cluster-slave --cluster-master-id $master3
