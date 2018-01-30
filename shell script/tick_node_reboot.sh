#!/bin/bash
# tick_node_reboot.sh: is used to reboot ticket node to reset log potiner
# This is to workaround bug 136753
# This script is applicable when InServ is upgrading from 3.1.3.GA or 3.1.3.MU1
# This script will call two scripts:
#    rm_ticket_config_dump.gdb: check if there is any nonNull log pointer and logentry type mismatch
#    chkioctl.sh: check if there is any pending ioctl
# 
# (1) 3.1.3.MU1 + P10
#     - logentry is corrupted, reboot ticket node
#     - logentry is not corrupted, no need to reboot ticket node
# (2) 3.1.3.MU1 - No P10 or 3.1.3.GA
#     - log pointer is not NULL, reboot ticket node
#     - log pointer is already NULL, no need to reboot ticket node.
#

Version=1.0
TPD_VERSION="3.1.3.202|3.1.3.230"
DIR=/common/support
TICK_CONFIG_CHECK=rm_ticket_config_dump.gdb
IOCTL_CHECK=chkioctl.sh
DTD_LOG=dtd_log.txt
TICK_TYPE_MATCH="DTD_Tick_type_mismatch=0"
NULL_LOGP="DTD_nonNULL_lopg=0"

GetConfirmation()
{
  local MSG="$1"

  echo -e "$MSG"
  while true ; do
    echo -e -n "select q=quit y=yes n=no: "
    read reply
    if [ $reply == "y" ]; then
        echo
        break
    elif [[ $reply == "q" || $reply == "n" ]]; then
        exit
    else
        echo "Unrecognized input \"$reply\""
    fi
  done
}

cleanup_dtd_log()
{
   rm $DIR/$DTD_LOG  >/dev/null 2>&1 
}


showversion -b | grep "Release version" | egrep -qw "$TPD_VERSION"
if [ $? -ne 0 ]; then
    echo -e "ERROR: Script is not applicable for this release or version\n" >&2
    (set -x; showversion -b)
    exit 1
fi



# Make sure sysmgr is up and running
showsysmgr |grep -q "System is up and running"
if [ $? -ne 0 ]; then
        echo "showsysmgr failed: $(showsysmgr)"
        (set -x; showsysmgr -d)
        exit 1
fi

$(clwait --bash)

if [ $online -ne $integrated ]; then
    echo "Not all nodes are integrated (clwait: $(clwait))"
    exit 1
fi


showrcopy -d | egrep "Group Information" >/dev/null
if [ $? -ne 0 ]; then
        echo -e "ERROR: Script is not applicable since there is no Remote Copy Group on this system.\n" >&2
        exit 1
fi

cleanup_dtd_log

P10_installed=0
TPD=$(showversion -b | grep Release | awk '{ print $3}')
showversion -b | egrep P10 > /dev/null
if [ $? -ne 0 ]; then
    echo -e "\n- You are using script version=$Version, TPD=$TPD and running it on $(date)\n"
else
    echo -e "\n- You are using script version=$Version, TPD=$TPD + P10 and running it on $(date)\n"
    P10_installed=1
fi

tnode=$(showmemval  kernel$mynode  none  8  1  primary_node | awk '{ print $2 }')
echo "ticket node is node $tnode"

if [ $mynode -ne $tnode ]; then
    echo "Need to run the script from ticket node $tnode, please re-run the script from ticket node $tnode"
    exit 1
fi


if [ ! -f $DIR/$TICK_CONFIG_CHECK ]; then
    echo "script $DIR/$TICK_CONFIG_CHECK doesn't exist "
    exit 1
fi



echo "running script $DIR/$TICK_CONFIG_CHECK now."

echo "source $DIR/$TICK_CONFIG_CHECK" | crash -s > $DIR/$DTD_LOG

egrep $TICK_TYPE_MATCH $DIR/$DTD_LOG > /dev/null
if [ $? -eq 0 ]; then
    if [ $P10_installed -eq 1 ]; then
        echo "System is running with P10 and there is no DTD type mismatch, you don't need to reboot ticket node, exit now"
        cleanup_dtd_log
        exit 1
    else
        egrep $NULL_LOGP $DIR/$DTD_LOG > /dev/null
        if [ $? -eq 0 ]; then
            echo "Log pointer has been reset, you don't need to reboot ticket node, exit now"
            cleanup_dtd_log
            exit 1
        fi
    fi 
fi

cleanup_dtd_log
echo "Found invalid log pointer, need to reboot ticket node $tnode to reset log pointer"


if [ ! -f $DIR/$IOCTL_CHECK ]; then
    echo "script $DIR/$IOCTL_CHECK doesn't exist "
    exit 1
fi

chmod +x $DIR/$IOCTL_CHECK


# ChkPendingIoctls313plus

GetConfirmation "\nDo you want to run script $DIR/$IOCTL_CHECK to check if there is any pending ioctl ?"

$DIR/$IOCTL_CHECK | egrep "STATUS: PASS" >/dev/null
if [ $? -ne 0 ]; then
        echo -e "Exit due to pending ioctl\n" >&2
        exit 1
fi


GetConfirmation "\nAre you sure you want to reboot ticket node $tnode now ?"

echo "Reboot ticket node $tnode now"
(set -x; shutdownnode reboot $tnode)

