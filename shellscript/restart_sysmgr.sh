#!/bin/bash
# restart_sysmgr.sh: Restart sysmgr if earlier upgrade is failed - need root access
# Script work arounds: 125767, 126748, 127905
# - It asks for user confirmation prior to restarting sysmgr
# - Once user replies 'y' then restarts sysmgr in master node then restarts in other nodes in the cluster
Version=1.00

  echo "You are using script version: $Version; clwait: $(clwait); $(date)"
  echo -e "\nAre you sure you want to restart the sysmgr on all nodes without app dump?"
  while true ; do
    echo -e -n "select q=quit y=yes n=no: "
    read reply
    if [ $reply == "y" ]; then
        break
    elif [[ $reply == "q" || $reply == "n" ]]; then
        exit
    else
        echo "Unrecognized input \"$reply\""
    fi
  done

  $(clwait --bash)
  echo -e "\n- Restarting sysmgr in Master node$master"
  OUT=$(setsysmgr -f quiet_restart 2>&1)
  echo $OUT | grep -q EA_PROCESS_DOWN
  if [ $? -ne 0 ]; then
    echo "$OUT" >&2
    echo -e "\nERROR: Unable to restart sysmgr. Consult Support" >&2
    exit 1
  fi

  echo "$OUT" >&2

  for node in $(seq 0 7); do
    if (( (online & (1 << node)) == 0 || (node == master) )); then
        continue
    fi

    echo -e "\n- Restarting sysmgr in node$node"
    (set -x; killall -9 sysmgr)
  done

  echo -e "\nsysmgr restarted successfully in all nodes"
