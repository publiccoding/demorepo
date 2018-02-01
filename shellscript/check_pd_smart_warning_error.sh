#!/bin/bash
# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
#
# check_pd_smart_warning_error.sh: Check physical drives with smart warning or error in last $MIN minutes.
#
# How script works:
# - Check sysmgr is up or not?
# - Check all nodes are integrated or not?
# - Checks whether $MFR and $DRIVE_MODEL_LIST drives are present or not?
# - Read event logs with '$EVENT_PATTERN' in last $MIN minutes.
#   Abstract drive WWNs from event log output.
# - Map event log based PD WWN with showpd output then get drive IDs.
# - List drives to be replaced prior to upgrade.
#
# Defect(s) covered: 221548

Version=1.00

# Viper-C drive models
DRIVE_MODEL_LIST="HVIPC0300GBFC15K|HVIPC0600GBFC15K"

# Manufacturer
MFR="HITACHI"

# Search event logs for $MIN minutes
MIN=1440

EVENT_PATTERN="PD .* is not being failed, but as emitted SMART"

usage()
{
    echo -e "Usage: ${0##*/} --verify : To check physical drives with smart warning or error in last $MIN minutes."

    exit 1
}

# Get version of the script.
get_script_version()
{
    local script=$1

    echo "- You are using ${script} script version=$Version and running it on $(date "+%Y-%m-%d %T")"
    echo -e "- clwait: $(clwait)"
    if [ $# -ne 0 ]; then
        echo "- User command line: $@"
    fi
    echo
}

# Check whether sysmgr is up and running, if not exit.
is_sysmgr_up()
{
    showsysmgr | grep -q "System is up and running"
    if [ $? -ne 0 ]; then
        (set -x; showsysmgr -d)
        echo -e "\n${0##*/}: sysmgr is not started." >&2
        exit 1
    fi
}

# Check whether all nodes integrated, if not exit.
isallnodesintegrated()
{
    eval $(clwait --bash) # It exports mynode, master, online and integrated
    if [ $integrated -ne $online ]; then
        echo "${0##*/}: Error: Not all nodes integrated. clwait: $(clwait)" >&2
        exit 1
    fi
}

# Check pd smart warning error for $MFR and $DRIVE_MODEL_LIST events in last $MIN minutes
check_pd_smart_warning_error()
{
    local drives_list=$(
        showpd -nohdtot -showcols Id,State,MFR,Model,Node_WWN |
            grep -w "$MFR" | egrep -w "$DRIVE_MODEL_LIST" | grep -vw "failed"
    )

    if [ -z "$drives_list" ]; then
        echo "${FUNCNAME[0]}: It is not applicable as $MFR manufacturer drive models ${DRIVE_MODEL_LIST//|/,} are not in this setup."
        return 5
    fi

    echo "${FUNCNAME[0]}: Reading event logs with '$EVENT_PATTERN' in last $MIN minutes."
    local PD_WWID_LIST=$(showeventlog -min $MIN -oneline -debug -msg "$EVENT_PATTERN"  |
        grep -v -e "^Time" -e "No event matched your criteria" |
        sed -e "s/.* PD //g" -e "s/ is not being failed, but as emitted SMART.*//g" | sort -u | sed -e "s/ /|/g")

    if [ -z "$PD_WWID_LIST" ]; then
        echo -e "\n${FUNCNAME[0]}: No SMART Warning/error reported by any drive."
        return 0
    fi

    drives_list=$(echo "$drives_list" | egrep "$PD_WWID_LIST" | awk 'BEGIN { flag=0 } ($1 != "---") {
        if (flag) { printf "," }
        printf "%s", $1
        flag=1
    }'
    )

    if [ -z "$drives_list" ]; then
        echo -e "\n${FUNCNAME[0]}: Drive(s) with following WWNs are no longer present in the system.\n$PD_WWID_LIST"
        return 0
    fi

    echo -e "\n${FUNCNAME[0]}: SMART Warning or error reported by PD $drives_list.\nConsult support to replace listed drives before proceeding to upgrade."
    return 1
}

get_script_version ${0##*/} "$@"

option=${1:-}

case $option in
    "--verify")
        ;;

    *)
        usage
        ;;
esac

is_sysmgr_up

isallnodesintegrated

check_pd_smart_warning_error
retval=$?
exit $retval
