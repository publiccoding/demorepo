#!/bin/bash
# resumeflusher.sh: Script generates /etc/rc2.d/S30resumeflusher script to resume flusher when it is stuck
# - Defect(s) it works around: 126236, 154247
# - Reapply the work around, if node rescue takes place on same setup
# - rc script will be automatically removed during TPD upgrade
#   It is applicable for TPD=3.1.3.MU1 and 3.2.1.MU2
#
# How script works:
# Script supports --install, --verify, --uninstall options
# Pre-check conditions for any option:
# - It checks whether all nodes are integrated? If not exit.
# - Is sysmgr up and running? If not exit.
# - It checks are we on valid supported TPD version? If not exit.
#
# In --install option:
# - It confirms whether user like to install S30resumeflusher rc script? If not exit.
# - Script generates S30resumeflusher rc script with executable permissions.
# - Copies to each node in the cluster then starts /etc/rc2.d/S30resumeflusher script.
# - Posts event below:
#    S30resumeflusher: Successfully installed /etc/rc2.d/S30resumeflusher file on all the nodes.
# - Install log will be at /var/log/tpd/resumeflusher.sh.log. It will be available in insplore.
#
# In --verify option:
# - Checks whether /etc/rc2.d/S30resumeflusher file is present? If then lists it.
# - It checks whether S30resumeflusher is running? If then gives ps output.
# - Fetches event logs in last hour with S30resumeflusher string.
#
# In --unistall option:
# - If S30resumeflusher script file is present. It calls with S30resumeflusher for every node.
# - Removes earlier /etc/rc2.d/S30resumeflusher file.
# - Posts event below:
#   S30resumeflusher: Successfully uninstalled /etc/rc2.d/S30resumeflusher file from all the nodes.
# 
# On how S30resumeflusher works:
# - While generating the script it imports few variables from resumeflusher.sh
# - It exports required environment variable. To make the script wok on node or cluster reboot.
# - When script starts it posts message below to node messages file.
#   Launching /etc/rc2.d/S30resumeflusher script to work around flusher is stuck issue by 
#   resuming flusher threads
# - Script starts forever while loop. Monitors the condition every 5 min from master node.
#   * It checks whether all online nodes are integrated to cluster. If not goes to sleep.
#   * Script fetches "statcmp -iter 1" data.
#   * In "Queue Statistics" checks WrtSched >= $MAX_WRTSCHED for any node? If then starts node loop
#       It checks whether all node pairs are integrated? If not break from node loop.
#       Before taking action, it posts event below for given node:
#         S30resumeflusher: For node? WrtSched=? is >=$MAX_WRTSCHED.. ctcr_force_tick_mismatch=1 ..
#     It runs, command below 10 times to make sure none of the required threads missed it.
#       setmemval kernel? none u8 ctcr_force_tick_mismatch 1
#   * sleep $SLEEP_TIME then loop back for to monitor again.

Version=1.07

TPD_VERSION="3.1.3.230|3.2.1.200|3.2.1.292"
PROBLEM="flusher is stuck"

RC_SCRIPT_FILE=S30resumeflusher
DIR=/etc/rc2.d
INFORMATIONAL=5

function generate_rcscript_file
{

cat << "EOF"
#!/bin/bash
# /etc/rc2.d/S30resumeflusher: It works around in resuming IOs when flusher is stuck
# - Defect(s) it works around: 126236
# - It is suggested work around when you notice >100k in WrtSched for "statcmp -d -iter 1" command in 3.1.3.MU1, 3.2.1.MU2
#
# Note:
# - Script will be automatically removed during TPD upgrade.

MAX_WRTSCHED=100000
SCRIPT=$(basename $0)

# Defines below used while fetching clf_scan_stop_reason from kernel for each flusher
CLF_SCAN_STOP_REASON_OFFSET=100
CLF_DEV_NPGS_OFFSET=164
CMP_LD_FSTAT_SIZE=240
MAX_LD_FLUSHER_NUM=4

CLWAIT=/opt/tpd/bin/clwait
SETMEMVAL=/opt/tpd/bin/setmemval
SHOWMEMVAL=/opt/tpd/bin/showmemval
EM_TEST=/opt/tpd/bin/em_test
STATCMP=/opt/tpd/bin/statcmp

SLEEP_TIME=45
MAJOR=2
INFORMATIONAL=5
ALERT_POSTED=2 # To clear earlier alert if any
EOF

cat << EOF # Export varibles to here-document
PROBLEM="$PROBLEM"
ALERT_MSG="$RC_SCRIPT_FILE: statcmp WrtSched is too high, invoking resume flusher"
EOF

cat << "EOF"

function is_node_pair_integrated
{
  local integrated=$integrated

  res="YES"
  for pair in 1 3 5 7; do
    node1_state=$((integrated >> pair & 1))
    node2_state=$((integrated >> pair-1 & 1))

    if [ $node1_state != $node2_state ]; then
        res="NO"
	break
    fi

    echo pair: $pair node1_state: $node1_state node2_state: $node2_state
  done

  echo $res
}

function clear_alert
{
    if [ $ALERT_POSTED -ne 0 ]; then
	ALERT_ID=$(showalert -oneline -wide -n | grep "$ALERT_MSG" | awk '{ print $1 }')
	if [ "$ALERT_ID" != "" ]; then
	  setalert fixed ${ALERT_ID}
	  ALERT_POSTED=0
	else
	  ((ALERT_POSTED--))
	fi
    fi
}

# Exporting environment variables
export PATH=/common/test/common/bin:/opt/tpd/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin:/opt/tpd/lbin:$PATH
export PEGASUS_HOME=/opt/tpd/apihome
export LD_LIBRARY_PATH=/opt/tpd/lib
export TPDSYSNAME=localhost
export TPDPWFILE=/tmp/.cli_pwfile
export TPDCACHEDIR=/tmp/.tpd_cache
export TPDCLIENTHOST=$(hostname)

clear_alert_count=0
  case "$1" in
    start)
	echo "Launching $0 script to work around $PROBLEM issue by resuming flusher threads"
	prev_pid=""
	prev_master=""
        while true ; do
          eval $($CLWAIT --bash)

          if [[ "$integrated" != "" && "$online" != "" && "$mynode" != "" && "$master" != "" && $mynode -eq $master ]]; then

	    (( mask=1<<mynode ))
	    (( integrated_mask=mask&integrated ))

            if [[ $integrated_mask -ne 0 ]]; then # This node is in cluster

	      Node_WrtSched=$($STATCMP -iter 1 | awk -v MAX_WRTSCHED=$MAX_WRTSCHED '
		/^ .* [A-Z]/ { data=0 }
		/Queue Statistics/ { data=1 }
		{
		  if (data && $1 ~ /[0-7]/) {
		    Node=$1
		    WrtSched=$6
		    if (WrtSched >= MAX_WRTSCHED) print Node, WrtSched
		  }
		}
	      ')

	      if [ "$Node_WrtSched" != "" ]; then
		echo "$Node_WrtSched" | while read Node WrtSched; do # Work around will be applied on every node where WrtSched >= MAX_WRTSCHED

		  $(CLWAIT --bash)
		  NODE_PAIR_INTEGRATED=$(is_node_pair_integrated $integrated)
		  if [ "$NODE_PAIR_INTEGRATED" == "NO" ]; then # One of the node pair is down
			break
		  fi

		  message="For node$Node WrtSched=$WrtSched is >=$MAX_WRTSCHED. Setting ctcr_force_tick_mismatch=1 in kernel$Node"
		  $EM_TEST --severity=$INFORMATIONAL --post="$SCRIPT: $message"
		  $EM_TEST --severity=$MAJOR --postalert="$ALERT_MSG"
		  ALERT_POSTED=10 # Recheck alert 10 times when issue is not around then mark it as fixed

                  flusher=0
                  while [ $flusher -lt $MAX_LD_FLUSHER_NUM ]; do
                    # Log an event for each flusher with clf_scan_stop_reason data logged
                    CLF_SCAN_STOP_REASON=$(
                        $SHOWMEMVAL kernel$Node none 32 8 cmp_ld_fstat+$((flusher * CMP_LD_FSTAT_SIZE + CLF_SCAN_STOP_REASON_OFFSET)) | \
                        awk '{ printf "%#x %#x %#x %#x %#x %#x %#x %#x\n", $2, $3, $4, $5, $6, $7, $8, $9 }'
                    )
                    message="clf_scan_stop_reason for flusher $flusher: $CLF_SCAN_STOP_REASON in kernel$Node"
                    $EM_TEST --severity=$INFORMATIONAL --post="$SCRIPT: $message"

                    # Log an event for each flusher with clf_dev_npgs data logged
                    CLF_DEV_NPGS=$(
                        $SHOWMEMVAL kernel$Node none 32 8 cmp_ld_fstat+$((flusher * CMP_LD_FSTAT_SIZE + CLF_DEV_NPGS_OFFSET)) | \
                        awk '{ printf "%#x %#x %#x %#x %#x %#x %#x %#x\n", $2, $3, $4, $5, $6, $7, $8, $9 }'
                    )
                    message="clf_dev_npgs for flusher $flusher: $CLF_DEV_NPGS in kernel$Node"
                    $EM_TEST --severity=$INFORMATIONAL --post="$SCRIPT: $message"
                    ((flusher++))
                  done

		  cnt=0
		  while [ $cnt -lt 10 ]; do
		    $SETMEMVAL kernel$Node none u8 ctcr_force_tick_mismatch 1
		    ((cnt++))
		    sleep 3
		  done # end of while cnt

		done # end of while read Node WrtSched
	      else
                # When flusher issue is resolved, it watches earlier posted alerts then it marks them as fixed
		clear_alert

		((clear_alert_count++))
		if [ $clear_alert_count -eq 20 ]; then
		  clear_alert_count=0
		  if [ $ALERT_POSTED -le 0 ]; then
		    ALERT_POSTED=2
		  fi
		fi
	      fi # end of Node_WrtSched

	    fi # end of integrated_mask

	  fi # end of $integrated

	  sleep $SLEEP_TIME
	done < /dev/null >/dev/null 2>&1 & # end of while-loop (close i/p & o/p to follow thru)
	;;

    stop)
	PID=$(ps -ef | grep "$0 .*start" | egrep -v "grep|onallnodes" | awk '{ print $2 }')
	if [ "$PID" != "" ]; then
	    echo "Terminating $0 script (pid=$PID)"
	    kill $PID
	fi
	;;

    *)
	echo "Usage: $0 start|stop"
	exit 1
	;;
  esac
EOF
}

# Function to check TPD version
function check_tpd_version
{
    showversion -b | grep "Release version" | egrep -qw "$TPD_VERSION"
    if [ $? -ne 0 ]; then
        echo -e "ERROR: Script is not applicable for this release or version\n" >&2
        (set -x; showversion -b)
        exit 1
    fi
}

function install_script()
{
  local TPD=$(showversion -b | grep Release | awk '{ print $3}')

  echo -e "\n$(date "+%x %X"): Installing ${RC_SCRIPT_FILE}, Version=$Version, TPD=$TPD"

  echo -e "\nAre you sure you want to install ${RC_SCRIPT_FILE} file to work around '$PROBLEM'?"
  while true ; do
    echo -e -n "select q=quit y=yes n=no: "
    read reply
    if [ $reply == "y" ]; then
	break
    elif [[ $reply == "q" || $reply == "n" ]]; then
  	return
    else
	echo "Unrecognized input \"$reply\""
    fi
  done

  echo -e "\n\n($((COUNT++))) Generating ${RC_SCRIPT_FILE} rc script file\n"
  generate_rcscript_file > ${RC_SCRIPT_FILE}.$$
  chmod +x ${RC_SCRIPT_FILE}.$$

  echo -e "\n($((COUNT++))) Applying work around:\n"

  result=0
  for node in $(seq 0 7); do 
    if (( (online & (1 << node)) == 0 )); then
	continue    
    fi 

    echo "Node ${node}:"
    PID=$(rsh node${node} "ps -f -C $RC_SCRIPT_FILE --no-headers" | awk '{ print $2 }')
    if [ "$PID" != "" ]; then
	echo -e "$RC_SCRIPT_FILE script is already running (pid=$PID} - skipping\n"
	continue
    fi

    (set -x; rcp ${RC_SCRIPT_FILE}.$$ node${node}:${DIR}/${RC_SCRIPT_FILE})
    (set -x; rsh node${node} ${DIR}/${RC_SCRIPT_FILE} start)
    result=1
    echo
  done

  rm -f ${RC_SCRIPT_FILE}.$$

  if [ $result -eq 1 ]; then
    message="Successfully installed ${DIR}/${RC_SCRIPT_FILE} file on all the nodes."
    echo -e $message"\n"
    em_test --severity=$INFORMATIONAL --post="$RC_SCRIPT_FILE: $message" >/dev/null
  fi

  (set -x; sleep 5)
  verify_script
}

function verify_script()
{
    echo -e "- Verifying scripts:\n"

    echo -e "($((COUNT++))) rc script ${RC_SCRIPT_FILE} files list:\n"
    onallnodes "(if [ -x ${DIR}/${RC_SCRIPT_FILE} ]; then
		   ls -l ${DIR}/${RC_SCRIPT_FILE}
		 fi
		)"

    echo -e "($((COUNT++))) rc script ${RC_SCRIPT_FILE} pid(s) on each node (if any):\n"
    onallnodes "ps -f -C $RC_SCRIPT_FILE --no-header | grep -v grep"

    echo -e "\n($((COUNT++))) Event log messages with ${RC_SCRIPT_FILE} pattern in last one hour:"
    showeventlog -min 60 -debug -oneline -msg "${RC_SCRIPT_FILE}"

    echo -e "\n($((COUNT++))) Alerts generated with ${RC_SCRIPT_FILE} pattern:"
    showalert -oneline -wide -all | grep -w "${RC_SCRIPT_FILE}"
}

function uninstall_script()
{
    INFORMATIONAL=5

    echo -e "- Terminating, removing $RC_SCRIPT_FILE script from each node\n"
    onallnodes "(if [ -f ${DIR}/${RC_SCRIPT_FILE} ]; then
		   ${DIR}/${RC_SCRIPT_FILE} stop
		 fi

    		 rm -f ${DIR}/${RC_SCRIPT_FILE}
		)" > /dev/null

    message="Successfully uninstalled ${DIR}/$RC_SCRIPT_FILE file from all the nodes."
    em_test --severity=$INFORMATIONAL --post="$RC_SCRIPT_FILE: $message" >/dev/null

    verify_script
}

function usage()
{
    echo -e "Usage: $0 <--install|--verify|--uninstall>\n"

    echo -e "--install   : Install $RC_SCRIPT_FILE rc script on each node to work around '$PROBLEM' problem. Before installing it asks for confirmation."
    echo -e "--verify    : Verify whether $RC_SCRIPT_FILE rc script installed"
    echo -e "--uninstall : Uninstall $RC_SCRIPT_FILE rc script from each node"

    exit 1
}

OPTION=$1
LOGNAME="/var/log/tpd/$(basename $0).log"
COUNT=1

eval $(clwait --bash) # It exports mynode, master, online and integrated
if [ $integrated -ne $online ]; then
    echo "ERROR: Not all nodes are integrated clwait: $(clwait)"
    exit 1
fi

showsysmgr|grep -q "System is up and running"
if [ $? -ne 0 ]; then
    echo "ERROR: sysmgr is not started"
    (set -x; showsysmgr -d)
    exit 1
fi


TPD=$(showversion -b | grep "^Release" | awk '{ print $3 }')

echo -e "\n- You are using script version=$Version, TPD=$TPD and running it on $(date)"

case $OPTION in
  "--install") check_tpd_version
	       install_script 2>&1 | tee -a $LOGNAME
	       echo -e "\n- Install log is at $LOGNAME"
	;;

  "--verify") verify_script
	;;

  "--uninstall") uninstall_script
	;;

  *) usage
	;;
esac
