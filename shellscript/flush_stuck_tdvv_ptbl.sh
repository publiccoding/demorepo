#!/bin/bash
# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
# flush_stuck_tdvv_ptbl.sh: Flush stuck TDVV page table entries
# Defect(s) it covers: 224559
#
# How script works:
# - Validate whether script is running in supported TPD version or not?
# - Check sysmgr is up or not?
# - Check all nodes are integrated or not?
# - It checks 3.2.1.MU3  + P80 patch installed?
# - Make sure $TEMP_SNAP_VOLUME volume doesn't exists.
# - Make sure setup has TDVV volumes and get list of TDVV base and snapshot volumes.
# - If user specifies --install option then "Flush stuck page table entries for all TDVV volumes."
#   It perfroms flush stuck TDVV page table entries if any.
#   For each TDVV volume, on each node basis script calls:
#       setmemval kernel$node none u32 scan_ptbl_in_progress 1
#       setmemval kernel$node none u32 scan_ptbl_mid $vv_id
#       setmemval kernel$node none u32 scan_ptbl_opcode 1
#   To flush IOs, it creates snapshot volume:
#       If volume is not assigned with snp_cpg then assign UsrCPG as SnpCPG later it unassign it.
#       createsv -ro hpe_flush_stuck_tdvv_ptbl $vv_name
#       removevv -f -snaponly hpe_flush_stuck_tdvv_ptbl
#   On each node basis it verifies scan_ptbl_rval value:
#       showmemval kernel$node none u32 1 scan_ptbl_rval
#   - If scan_ptbl_rval set to TE_PASS/TE_FAIL/TE_BUSY/TE_INVALID/TE_RETRY error codes then takes respective action.
#   - If script is passed for all volumes the it adds "$RESULT_DONE" string in $FLUSH_STUCK_TDVV_PTBL_VV_LIST file to avoid next execution of the script.
#
# - If user specifies --uninstall, it removes $FLUSH_STUCK_TDVV_PTBL_VV_LIST in the cluster to clear earlier history of execution.
#
# - If user specifies --verify option then "Verify any other TDVV volumes need to flush stuck TDVV page table entries."
#   It generates list of volumes due in performing flush stuck TDVV page table entries.

Version=1.02

# Patches needed: 3.2.1.MU3+P80
# For EGA specify GA and EMUx specify MUx
TPD_VERSIONS="3.2.1.MU3"

FLUSH_STUCK_TDVV_PTBL_VV_LIST=/var/log/tpd/flush_stuck_tdvv_ptbl_vv.lst
TEMP_SNAP_VOLUME=hpe_flush_stuck_tdvv_ptbl
RESULT_DONE=":DONE:"
SCAN_FIX=1 # To scan and fix ptbl entries. 0: Scan only. 1: Scan and Fix

SCRIPT=flush_stuck_tdvv_ptbl.sh
LOCK_FILE=/tmp/LCK_${SCRIPT%.sh}

# Return codes from Kernel
TE_PASS=0      # No issue is seen : Passed
TE_FAIL=1      # It failed or volume doesn't exists : Failed
TE_OFFLINE=3   # Volume is not in normal state: Failed
TE_INVALID=8   # Volume is removed : Passed
TE_RETRY=12    # unable to lock VV or page table - retry again 9 times if still fails: Failed
TE_DEVBUSY=159 # Found stuck ptbl and fixed: Passed

# Usage of the script.
usage()
{
    echo "Usage:"
    echo "${0##*/} --install   : Flush stuck page table entries for all TDVV volumes."
    echo "${0##*/} --uninstall : Clear earlier history of flush stuck TDVV page table entries."
    echo "${0##*/} --verify    : Verify any other TDVV volumes need to flush stuck TDVV page table entries."

    echo -e "\nNote: During script --install execution, snapshot creation may be blocked or failed for the volume on which scan is in progress."

    exit 1
}

cleanup()
{
    [ ${mynode:-} ] && eval $(clwait --bash) # It exports mynode, master, online and integrated
    for node in {0..7}; do
        if (( (online & (1 << node)) == 0 )); then # Check whether node is online
            continue
        fi

        # Reset to default
        set_scan_ptbl_globals $node 0 4294967294 0
    done
    # Remove $TEMP_SNAP_VOLUME snapshot irrespectively if it was created
    removevv -f -snaponly $TEMP_SNAP_VOLUME >/dev/null 2>&1
    rm -f $LOCK_FILE
    trap "" EXIT
    exit
}

# Get version of the script.
get_script_version()
{
    local script=$1

    echo "- You are using ${script} script version=$Version and running it on $(date "+%Y-%m-%d %T %Z")"
    echo -e "- clwait: $(clwait)"
    if [ $# -ne 0 ]; then
        echo "- User command line: $@"
    fi
    echo
}

# From showversion output, translate TPD version to 3.3.1.GA or 3.3.1.MU1 etc.,
translate_tpd_release_version()
{
    local tpd_release_version="$1"

    echo "$tpd_release_version" | grep "^Release version" | sed -e 's/Release version//g' -e 's/[()]//g' | sort -u | awk '
    {
        if (NF==1) TAG="GA"
        else TAG=$2

        split($1, t, ".");
        tpd_version=t[1]"."t[2]"."t[3]"."TAG
        print tpd_version
    }'
}

# Get specified partition's TPD version.
get_tpd_version()
{
  local partition=$1

  (if [[ "$partition" == "root" || "$partition" == "both" ]]; then
     showversion -b
   fi

   if [[ "$partition" == "altroot" || "$partition" == "both" ]]; then
     showversion -b -r
   fi
  ) | grep "^Release version" | sed -e 's/Release version//g' -e 's/[()]//g' | sort -u | awk '
  {
    if (NF==1) TAG="GA"
    else TAG=$2

    split($1, t, ".");
    tpd_version=t[1]"."t[2]"."t[3]"."TAG
    print tpd_version
  }'
}

# Function to check TPD version.
check_tpd_version()
{
    if [ $# -lt 2 ]; then
        echo "${0##*/}: wrong number of arguments passed to ${FUNCNAME[0]}." >&2
        exit 1
    fi

    local tpd_versions="$1"
    local partition=$2

    if [ "$tpd_versions" != "ALL" ]; then
        local current_tpd=$(get_tpd_version $partition)
        echo "$current_tpd" | egrep -qw "$tpd_versions"
        if [ $? -ne 0 ]; then
            echo "${0##*/}: Script is not applicable for $current_tpd release or version." >&2
            exit 1
        fi
    fi
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

# Prompt the user before taking critical action.
# If user says 'n' or 'q' then update GETCONFIRMATION="SKIP-IT".
# If user says 'y' then update GETCONFIRMATION="APPLY-IT".
GetConfirmation()
{
    local msg="$1"
    local func="$2"
    local reply

    GETCONFIRMATION=""
    if [ $# -eq 2 ]; then
        printf "$msg" $func
    fi
    while [ "$GETCONFIRMATION" == "" ]; do
        echo -n "select y=yes n=no q=quit : "
        read reply
        if [ "$reply" == "y" ]; then
            printf "User reply='%s'. User accepted %s workaround. Applying workaround.\n" $reply $func
            GETCONFIRMATION="APPLY-IT"
        elif [[ "$reply" == "q" || "$reply" == "n" ]]; then
            printf "User reply='%s'. Not applying %s workaround.\n" $reply $func
            GETCONFIRMATION="SKIP-IT"
        else
            printf "Unrecognized input '%s'\n" "$reply"
        fi
    done
}

# Prompt the user to continue or quit from execution. If no response from user within finite time then continue in execution
GetTimedConfirmation()
{
    local max_time=$1
    local inter_delay=$2
    local MSG="$3"
    local reply

    stty -echo
    while read -e -s -t 0.1 -n 10000; do : ; done # Flush earlier user inputs
    stty echo icanon icrnl
    USER_REPLY=""
    local time=0
    while [ $time -lt $max_time ]; do
        echo -e -n "\n$MSG Reply within $((max_time - time)) seconds : "
        reply=""
        read -t $inter_delay reply
        if [ -n "$reply" ]; then
            if [ "$reply" == "y" ]; then
                USER_REPLY="Yes"
                echo
                break
            fi
            if [[ "$reply" == "q" || "$reply" == "n" ]]; then
                USER_REPLY="No"
                break
            fi
            echo "Unrecognized input '$reply'"
        fi
        ((time+=inter_delay))
    done
}

# Chceck whether $LOCK_FILE file exists. Call it before trap call
check_lock_file()
{
    local lock_file_status=$(onallnodes "ls $LOCK_FILE 2>/dev/null" | grep -B1 $LOCK_FILE | awk '
      /^Node/ { Node="node"$2 }
      /LCK/ { print Node $0 }
      '
    )

    if [ -n "$lock_file_status" ]; then
        echo -e "ERROR: $(basename $0) is already running. Lock file is at, $lock_file_status"

        echo -e "\n- Contents of the lock file shows"
        onallnodes "cat $LOCK_FILE 2>/dev/null" | grep -B1 "^Pid="

        echo -e "\n- If no such process is running then clean-up '$lock_file_status' file then run the script again."
        exit 1
    fi
}

# Get lock file before applying workaround
get_lock_file()
{
    check_lock_file
    eval $(clwait --bash)
    echo "Pid=$$, Script=$0, Node$mynode StartDate=\"$(date "+%x %T")\"" > $LOCK_FILE
}

# Check whether required patch or superseded patch is installed.
# If TPD doesn't matches then return 0
# If TPD matches and valid patch doesn't exists then exit
# If TPD matches and valid patch exists then return 1
is_patch_installed()
{
    local check_tpd=$1
    local check_patch="$2"
    local current_tpd=$(showversion -b)

    current_tpd=$(translate_tpd_release_version "$current_tpd")
    if [ $check_tpd != "$current_tpd" ]; then
        # If TPD is not matching then it is not applicable
        return 0
    fi

    if [ -f /opt/tpd/patch_descriptions/$check_patch ] || showversion | grep -q "^Patches: .*$check_patch" || grep -q "Patch ID: $check_patch" /opt/tpd/patch_descriptions/P* 2>/dev/null; then
        : # Found the patch
    else
        echo "${0##*/}: It cannot be performed because prerequisite patch $check_patch has not been installed."
        exit 1
    fi
    return 1
}

# Get TDVV volumes and it's snapshot list
get_tdvv_volume_list()
{
    showvv -showsysobjs -nohdtot -showcols Id,Name,Prov,Type,CopyOf,Rd,Detailed_State,UsrCPG,SnpCPG | awk '{
        if ($3 == "tdvv") {
            tdvv_flag=1
        } else if ($3 != "snp") {
            tdvv_flag=0
        }
        if (tdvv_flag) print
    }'
}

set_scan_ptbl_globals()
{
    local node=$1
    local retval=0

    setmemval kernel$node none u32 scan_ptbl_in_progress $2 > /dev/null
    (( retval |= $? ))
    setmemval kernel$node none u32 scan_ptbl_mid $3 > /dev/null
    (( retval |= $? ))
    setmemval kernel$node none u32 scan_ptbl_opcode $4 > /dev/null
    (( retval |= $? ))

    if [ $retval -ne 0 ]; then
        echo "Error: setmemval failed for node$node. Consult Support."
        exit 1
    fi
}

# Function to create snap volume then remove it to flush outstanding IOs
# Don't press Ctrl-C during create_remove_sv() execution. It may cause $usr_cpg as snp_cpg same forever
# TODO: Use 'stty intr' to disable Ctrl-C
create_remove_sv()
{
    local vv_name=$1
    local snap_vv_name=$2
    local usr_cpg=$3
    local snp_cpg=$4

    # If snp_cpg is not assigned then assign $usr_cpg as snp_cpg temporarily
    if [ $snp_cpg == "--" ]; then
        (set -x; setvv -snp_cpg $usr_cpg $vv_name)
    fi

    (set -x; createsv -ro $snap_vv_name $vv_name)
    # Remove $TEMP_SNAP_VOLUME snapshot irrespectively if it was created
    removevv -f -snaponly $snap_vv_name >/dev/null 2>&1

    # Restore snp_cpg as unassigned
    if [ $snp_cpg == "--" ]; then
        (set -x; setvv -snp_cpg "" $vv_name)
    fi
}

# It will flush stuck TDVV page table entries if any.
flush_stuck_tdvv_ptbl()
{
    local option=$1
    local result
    local vv_failed_list=""
    local count=0
    local due_count=0
    local retval=0
    local vv_failed=0
    local scan_ptbl_rval[8]
    local retry_node_mask
    local node_list=""

    # Check whether All volumes "Flush stuck TDVV page table entries" is complete
    local result_done=$(grep "^${RESULT_DONE}" $FLUSH_STUCK_TDVV_PTBL_VV_LIST 2>/dev/null)
    if [ -n "$result_done" ]; then
        echo "${FUNCNAME[0]}: All volumes \"Flush stuck TDVV page table entries\" is alreay completed at ${result_done/$RESULT_DONE} "
        return 0
    fi

    local total_count=$(echo "$TDVV_VOLUME_LIST" | wc -l)
    echo -e "\nList of $total_count TDVV volumes in POA:"
    echo "$TDVV_VOLUME_LIST"
    echo -e "\nWARNING: During script --install execution, snapshot creation may be blocked or failed for the volume on which scan is in progress."

    if [ $option == "--install" ]; then

        GetConfirmation "\n%s: Would you like to flush stuck TDVV page table entries for above $total_count volume(s)?\n" ${FUNCNAME[0]}
        if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
            exit 1
        fi
    fi

    if [[ -s $FLUSH_STUCK_TDVV_PTBL_VV_LIST ]]; then
        echo -e "\n- Volumes below already performed flush stuck TDVV page table entries, they will be excluded."
        awk '{ print "\t" $0 }' $FLUSH_STUCK_TDVV_PTBL_VV_LIST
    fi

    # Converting each new line into bash array to fetch values and allow read() to work in the while loop.
    IFS=$'\n' TDVV_VOLUME_LIST=($(echo "$TDVV_VOLUME_LIST"))

    while [ $count -lt $total_count ]; do
        local vv_id=$(echo "${TDVV_VOLUME_LIST[count]}" | awk '{ print $1 }')
        local vv_name=$(echo "${TDVV_VOLUME_LIST[count]}" | awk '{ print $2 }')
        local vv_prov=$(echo "${TDVV_VOLUME_LIST[count]}" | awk '{ print $3 }')
        local vv_type=$(echo "${TDVV_VOLUME_LIST[count]}" | awk '{ print $4 }')
        local vv_copyof=$(echo "${TDVV_VOLUME_LIST[count]}" | awk '{ print $5 }')
        local vv_rd=$(echo "${TDVV_VOLUME_LIST[count]}" | awk '{ print $6 }')
        local vv_state=$(echo "${TDVV_VOLUME_LIST[count]}" | awk '{ print $7 }')
        local usr_cpg=$(echo "${TDVV_VOLUME_LIST[count]}" | awk '{ print $8 }')
        local snp_cpg=$(echo "${TDVV_VOLUME_LIST[count]}" | awk '{ print $9 }')

        echo -e "\n$(date "+%Y-%m-%d %T %Z") Processing $vv_name(Id=$vv_id, Prov=$vv_prov, CopyOf=$vv_copyof, Rd=$vv_rd, UsrCPG=$usr_cpg, SnpCPG=$snp_cpg) volume ($((++count)) of $total_count):"
        [ -s $FLUSH_STUCK_TDVV_PTBL_VV_LIST ] && grep -q " $vv_id ${vv_name}$" $FLUSH_STUCK_TDVV_PTBL_VV_LIST
        if [ $? -eq 0 ]; then
            echo -e "- $vv_name volume already performed flush stuck TDVV page table entries, skipping it."
            continue
        fi

        if [ $option == "--verify" ]; then
            echo "- $vv_name volume is due to perform flush stuck TDVV page table entries."
            ((due_count++))
            continue
        fi

        eval $(clwait --bash) # Refresh nodes in cluster

        echo "- Setting scan_ptbl_in_progress=1, scan_ptbl_opcode=$SCAN_FIX, scan_ptbl_mid=$vv_id for all nodes."
        for node in {0..7}; do
            if (( (online & (1 << node)) == 0 )); then # Check whether node is online
                continue
            fi

            # Set for scan and fix
            set_scan_ptbl_globals $node 1 $vv_id $SCAN_FIX
        done # End of node-loop #1

        retry_node_mask=$online
        for retry in {0..9}; do
            # Wait for a second before retrying again
            if [[ $retry -ge 1 && -n "$node_list" ]]; then
                echo "- TE_RETRY reported for $vv_name volume from $node_list. Performing retry count=$retry."
                sleep 1
            fi

            # To flush outstanding IOs of RO snapshot assign create_remove_sv on RW volume
            if [ $vv_rd == "RO" ]; then
                create_remove_sv $vv_copyof $TEMP_SNAP_VOLUME $usr_cpg $snp_cpg
            else
                create_remove_sv $vv_name $TEMP_SNAP_VOLUME $usr_cpg $snp_cpg
            fi

            # List of values for scan_ptbl_rval:
            #   0: TE_PASS (No ptbl issue noticed for the volume) : Passed
            #   1: TE_FAIL (Generic error code) : Add the volume to failure list
            #   3: TE_OFFLINE (Volume is not in normal state) : Add the volume to failure list
            #   8: TE_INVALID (VV is removed) : Passed
            #  12: TE_RETRY (unable to lock VV or page table) : Retry 9 times before adding the volume to failure list
            # 159: TE_DEVBUSY (Found stuck ptbl and fixed): Passed

            node_list=""
            for node in {0..7}; do
                if (( (retry_node_mask & (1 << node)) == 0 )); then
                    continue
                fi
                scan_ptbl_rval[$node]=$(showmemval kernel$node none u32 1 scan_ptbl_rval | awk '{ print $NF }')
                # If it is TE_RETRY then retry again otherwise break from retry loop
                if [ ${scan_ptbl_rval[$node]} -ne $TE_RETRY ]; then
                    (( retry_node_mask &= ~(1 << node) )) # Exclude node from retry list
                    # Reset to default
                    set_scan_ptbl_globals $node 0 4294967294 0
                else
                    node_list=${node_list:+$node_list","}
                    node_list="${node_list}node$node"
                    # Set for scan and fix
                    set_scan_ptbl_globals $node 1 $vv_id $SCAN_FIX
                fi
            done # End of node-loop #2

            if (( retry_node_mask == 0 )); then
                echo "${FUNCNAME[0]}: $vv_name volume passed for all nodes in the cluster after $retry retries."
                break
            fi
        done # End of retry-loop

        vv_failed=0
        # Log scan_ptbl_rval on each node basis
        for node in {0..7}; do
            if (( (online & (1 << node)) == 0 )); then # Check whether node is online
                continue
            fi

            case ${scan_ptbl_rval[$node]} in
            $TE_PASS)
            ;;

            $TE_FAIL)
                vv_failed=1 # To list the volume as failed
                echo "${FUNCNAME[0]}: $vv_name volume reported TE_FAIL for node$node."
            ;;

            $TE_OFFLINE)
                vv_failed=1 # To list the volume as failed
                echo "${FUNCNAME[0]}: $vv_name volume reported TE_OFFLINE (volume is not in normal state) for node$node."
            ;;

            $TE_INVALID)
                vv_failed=2 # For not to list the volume in the end result
                echo "${FUNCNAME[0]}: $vv_name volume reported TE_INVALID (volume is removed) for node$node."
            ;;

            $TE_RETRY)
                vv_failed=1 # To list the volume as failed
                echo "${FUNCNAME[0]}: $vv_name volume reported TE_RETRY (unable to lock VV or page table) for node$node"
                # Reset to default
                set_scan_ptbl_globals $node 0 4294967294 0
            ;;

            $TE_DEVBUSY)
                echo "${FUNCNAME[0]}: $vv_name volume reported TE_DEVBUSY (found stuck ptbl and fixed) for node$node."
            ;;

            *)  vv_failed=1 # To list the volume as failed
                echo "${FUNCNAME[0]}: $vv_name volume reported ${scan_ptbl_rval[$node]} (unknown) for node$node."
            ;;
            esac
        done # End of node-loop #3

        if [ $vv_failed -eq 1 ]; then
                vv_failed_list=${vv_failed_list:+$vv_failed_list","}
                vv_failed_list="${vv_failed_list}$vv_name"
        elif [ $vv_failed -eq 0 ]; then
            onallnodes "echo $(date "+%Y-%m-%d %T") $vv_id $vv_name >> $FLUSH_STUCK_TDVV_PTBL_VV_LIST" > /dev/null
        fi

        if [ $count -lt $total_count ] ;then
            echo -e "\n\n############################################################"
            echo -e -n "# - ${FUNCNAME[0]} completed for $count out of $total_count volumes."
            GetTimedConfirmation 10 2 "# Enter 'n' or 'q' to exit from the script. Otherwise it will proceed."
            if [ "$USER_REPLY" == "No" ]; then
                echo -e "\n*** User requested to quit from the script - exiting now. ***\n"
                retval=1
                break
            fi
            echo -e "\n# - No reply from user, proceeding to next volume."
            echo -e "############################################################"
        fi
    done

    if [ -n "$vv_failed_list" ]; then
        local vv_failed_list_count=$(echo ${vv_failed_list//,/ } | wc -w)
        echo -e "\n${FUNCNAME[0]}: hat_vol_scan_ptbls() failed for $vv_failed_list_count volume(s) below. Consult Support or rerun the script."
        echo -e "- Failed to run volume(s) list: ${vv_failed_list}"
        retval=1
    fi

   if [[ $option == "--install"  && $retval -eq 0 && -z "$vv_failed_list" ]]; then
        onallnodes "echo \"${RESULT_DONE} $(date "+%Y-%m-%d %T")\" >> $FLUSH_STUCK_TDVV_PTBL_VV_LIST" > /dev/null
        echo -e "\n${FUNCNAME[0]}: Successfully performed Flush stuck TDVV page table entries."
   elif [ $option == "--verify"  ]; then
        echo -e "\n${FUNCNAME[0]}: $due_count out of $total_count volume(s) due to perform flush stuck TDVV page table entries."
   fi

    return $retval
}

get_script_version ${0##*/} "$@"

if [ $# -ne 1 ]; then
    usage
fi

is_sysmgr_up

isallnodesintegrated

check_tpd_version "$TPD_VERSIONS" root

is_patch_installed 3.2.1.MU3 P80  # Check 3.2.1.MU3 + P80 installed.

showvv -nohdtot -showcols Name $TEMP_SNAP_VOLUME | grep -q "$TEMP_SNAP_VOLUME"
if [ $? -eq 0 ]; then
    echo "Error: $TEMP_SNAP_VOLUME volume exists. Remove it before running the script." >&2
    exit 1
fi

TDVV_VOLUME_LIST=$(get_tdvv_volume_list)

if [ -z "$TDVV_VOLUME_LIST" ]; then
    echo -e "\n${0##*/}: No TDVV volume(s) found. This script is not applicable." >&2
    exit 5
fi

echo "$TDVV_VOLUME_LIST" | awk 'BEGIN { retval=0 } ($7 != "normal") { retval=1; print } END { exit retval }'
if [ $? -ne 0 ]; then
    echo -e "\nError: Above volumes(s) not in \"normal\" state. Resolve them before running the script. Consult Support." >&2
    exit 1
fi

retval=0
case $1 in
    --install)
        check_lock_file
        trap cleanup EXIT SIGINT SIGQUIT SIGILL SIGTRAP SIGABRT SIGBUS SIGFPE SIGKILL SIGSEGV SIGTERM # handle signals
        get_lock_file
        flush_stuck_tdvv_ptbl $1
        retval=$?
    ;;

    --verify)
        flush_stuck_tdvv_ptbl $1
    ;;

    --uninstall)
        GetConfirmation "\n%s: Would you like to remove $FLUSH_STUCK_TDVV_PTBL_VV_LIST file, it clears earlier history of execution?\n" ${0##*/}
        if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
            exit 1
        fi

        echo "- Removing $FLUSH_STUCK_TDVV_PTBL_VV_LIST file from all nodes of the cluster."
        onallnodes "(set -x; rm -f $FLUSH_STUCK_TDVV_PTBL_VV_LIST)"
        echo -e "\n- Successfully removed $FLUSH_STUCK_TDVV_PTBL_VV_LIST file from the cluster."
        exit 0
    ;;

    *) usage
    ;;
esac

exit $retval
