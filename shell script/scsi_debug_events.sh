#!/bin/bash
# scsi_debug_events.sh: Script disables NDBG() calls in driver code by modifying scsi_debug kvar.
#
# Version: 1.01
# As per HP 3PAR OS 3.1.2 MU3 Upgrade Instructions in SAW - upgrade is supported from 3.1.1.MU1/2/3 and 3.1.2.GA/MU1/2
# Added support for 3.1.1.MU1/MU2/MU3 i.e., user can run this script prior to 3.1.2.MU3 upgrade for all supported versions
#
# Version: 1.00
# - It workarounds in avoiding too many SCSI events during TPD upgrade.
# - It is created to workaround 96827, 101453, and 101600 issues i.e., seen during TPD upgrade (or) Master node panic
#   TPD=3.1.1.MU1/3.1.1.MU2/3.1.1.MU3/3.1.2.GA/3.1.2.MU1/3.1.2.MU2/3.1.2.MU3/3.1.2.MU4
#
# Script supports two options below:
# 1) scsi_debug_events.sh disable # It disables SCSI debug event logging (To workaround the issue)
# 2) scsi_debug_events.sh enable  # It enables SCSI debug event logging  (To remove the workaround)
#

SYSVARS=/var/opt/tpd/touchfiles/sysvars.init
KVAR=scsi_debug
DBG_CD_NDBG=1

# Function to check TPD version
function check_tpd_version {

    showversion -b | grep "Release version" | egrep -qw "3.1.1.342|3.1.1.410|3.1.1.448|3.1.2.278$|3.1.2.322|3.1.2.422|3.1.2.484|3.1.2.562"
    if [ $? -ne 0 ]; then
        echo -e "ERROR: Script is not applicable for this release or version\n" >&2
        (set -x; showversion -b)
        exit 1
    fi
}

# Function to apply workaround
function disable_scsi_events {

    echo "Current ${KVAR} kvar value:"
    (set -x; tcli -e "kvar show -n ${KVAR}")

    kvar_val=$(tcli -e "kvar show -n ${KVAR}" | awk -F "${mynode}:" '{split($NF, val, " "); print val[1]}')

    if [ $((kvar_val & $DBG_CD_NDBG)) -eq $DBG_CD_NDBG ]; then # Check whether KVAR set with DBG_CD_NDBG=1 ?
	((kvar_val-=DBG_CD_NDBG)) # New value for KVAR
	echo -e "\nSetting ${KVAR} kvar to new value $kvar_val"
	(set -x; tcli -e "kvar set -n ${KVAR} -v $kvar_val")

	echo -e "\nCurrent ${KVAR} value:"
	(set -x; tcli -e "kvar show -n ${KVAR}")
    else
	tcli -e "kvar set -n ${KVAR} -v $kvar_val" # Setting same required value on all nodes
    fi

    echo -e "\nSetting ${KVAR} kvar persistent across reboots and/or upgrade"

    for node in `seq 0 7`; do
        if [ $((online & (1 << node))) -eq 0 ]; then # Node must be online
            continue
        fi

	RESULT=$(rsh node${node} "grep ${KVAR} $SYSVARS 2>/dev/null")
	if [ "$RESULT" == "" ]; then
            (set -x; rsh node${node} "echo ${KVAR}=${kvar_val} >> $SYSVARS")
            echo "node$node: ${KVAR} set to persistent now"
	else
            echo $RESULT | grep -qw ${KVAR}=${kvar_val}
            if [ $? -ne 0 ]; then
                echo "ERROR: node$node: Verify $RESULT value *****" >&2
            else
                echo "node$node: ${KVAR} is persistent"
            fi
	fi
    done

    echo
    (set -x; onallnodes "grep ${KVAR} ${SYSVARS}")
}

# Function to remove workaround
function enable_scsi_events {

    echo "Current ${KVAR} kvar value:"
    (set -x; tcli -e "kvar show -n ${KVAR}")

    kvar_val=$(tcli -e "kvar show -n ${KVAR}" | awk -F "${mynode}:" '{split($NF, val, " "); print val[1]}')

    if [ $((kvar_val & $DBG_CD_NDBG)) -eq 0 ]; then # To check whether KVAR set with DBG_CD_NDBG=0 ?
	((kvar_val+=DBG_CD_NDBG)) # New value for KVAR
	echo -e "\nSetting ${KVAR} kvar to new value $kvar_val"
	(set -x; tcli -e "kvar set -n ${KVAR} -v $kvar_val")

	echo -e "\nCurrent ${KVAR} value:"
	(set -x; tcli -e "kvar show -n ${KVAR}")
    else
	tcli -e "kvar set -n ${KVAR} -v $kvar_val" # Setting same required value on all nodes
    fi

    echo -e "\nRemoving ${KVAR} kvar from $SYSVARS file"

    for node in `seq 0 7`; do
        if [ $((online & (1 << node))) -eq 0 ]; then # Node must be online
            continue
        fi

	RESULT=$(rsh node${node} "grep -v ${KVAR} $SYSVARS 2>/dev/null")

	if [ "$RESULT" != "" ]; then # Keeping other kvars if any and excluding ${KVAR}
	    echo "- Keeping other kvars for node{node}"
            (set -x; rsh node${node} "echo \"${RESULT}\" > $SYSVARS")
	else
            (set -x; rsh node${node} "rm -f $SYSVARS")
	fi

    done

    echo
    (set -x; onallnodes "cat ${SYSVARS}")
}

if [[ $# -ne 1 || "$1" != "disable" && "$1" != "enable" ]]; then
    echo "Usage: $0 <disable|enable>"

    echo "Ex1:   $0 disable # It disables SCSI debug event logging (To workaround the issue)"

    echo "Ex2:   $0 enable  # It enables SCSI debug event logging  (To remove the workaround)"
    exit 1
fi >&2

$(clwait --bash) # It exports mynode, master, online and integrated

if [ $integrated -ne $online ]; then
    echo "ERROR: Not all nodes are integrated clwait: $(clwait)" >&2
    exit 1
fi

showsysmgr | grep -q "System is up and running"
if [ $? -ne 0 ]; then
    echo "ERROR: sysmgr is not started" >&2
    exit 1
fi

case "$1" in
    disable) check_tpd_version
	     disable_scsi_events
	     ;;

    enable)  enable_scsi_events
	     ;;
esac

