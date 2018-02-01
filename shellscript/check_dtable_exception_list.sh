#!/bin/bash
# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
#
# check_dtable_exception_list.sh: Check any Dirty exceptions not flushed for >= $DIRTY_EXCEPTION_THRESHOLD minutes
# - showmemval is used to check dirty exception data
#
# Defect(s) it covers: 185339,189400

# How script works:
# Check is it dedup setup
# For list 2 and 3
#   Copy global array variable as local on each list basis.
#   For Node 0 to Node 7
#     If dirty_list_len is zero then mark dlist_flag[$node]=0. i.e., to mark given node's L2/L3 dlist is empty.
#     Fetch list head then call check_dirty_exception_data() to follow thru in fetching data.
#       By using shomemval check_dirty_exception_data() gets mpg_state, mpg_busy, mpg_prv, mpg_last_flush_time values.
#       if (current time - mpg_last_flush_time) >= 10 minutes and mpg_state == DIRTY or mpg_state == DIRTY_AGAIN then
#       logs the output then returns 1 otherwise returns 0.
#     If return value is '1' then marks dlist_flag[$node]=1 to skip it from next loop and script continues next node.
#     If dirty_list_len > 1 then script calls check_dirty_exception_data() with mpg_prv pointer to proess it.
#   dlist_flag contents copied to global.
# If L2_DLIST_FLAG or L3_DLIST_FLAG of each node > 0 then node_list will be updated.
# Based on node_list script logs which nodes reported with dirty exceptions outstanding for >=10 minutes.

Version=1.02

TPD_VERSIONS="3.2.1.MU3"

DIRTY_EXCEPTION_THRESHOLD=10 # minutes

MAX_COUNT=150

L2_DLIST_FLAG=(-1 -1 -1 -1 -1 -1 -1 -1)
L3_DLIST_FLAG=(-1 -1 -1 -1 -1 -1 -1 -1)

MPG_DIRTY=3
MPG_DIRTY_AGAIN=5
MPG_STATE_TRANS=(INIT CLEAN CLEAN_NQ DIRTY FLUSHING DIRTY_AGAIN)

get_script_version()
{
    local patches=$(showversion -b | awk '/^Patches/ && $2 != "None" { print "+"$2 }')
    local tpd=$(showversion -b)
    tpd=$(translate_tpd_release_version "$tpd")

    local altroot_tpd=$(showversion -b -r)
    altroot_tpd=$(translate_tpd_release_version "$altroot_tpd")

    echo -e "- You are using $SCRIPT script version=$Version, TPD=$tpd$patches and running it on $(date "+%Y-%m-%d %X")"
    echo -e "- clwait: $(clwait)"

    if [ $# -ne 0 ]; then
      echo -e "- User command line: $*"
    fi

    echo -e "$(showsys -d | grep "^Nodes in Cluster" | sed -e 's/,/,node/g' | awk '{ printf "- Results below are applicable for node%s\n", $NF }')\n\n"
}

translate_tpd_release_version()
{
    local tpd_release_version="$1"

    echo -e "$tpd_release_version" | grep "^Release version" | sed -e 's/Release version//g' -e 's/[()]//g' | sort -u | awk '
        {
            if (NF == 1) {
                TAG = "GA";
            } else {
                TAG = $2;
            }

            split($1, t, ".");
            tpd_version = t[1]"."t[2]"."t[3]"."TAG;
            print tpd_version;
        }
    '
}

get_tpd_version()
{
    local partition=$1

    (
        if [[ "$partition" == "root" || "$partition" == "both" ]]; then
            showversion -b
        fi

        if [[ "$partition" == "altroot" || "$partition" == "both" ]]; then
            showversion -b -r
        fi

        if [ "$partition" == "" ]; then
            showversion -b $SHOWVERSION_OPT
        fi
    ) | grep "^Release version" | sed -e 's/Release version//g' -e 's/[()]//g' | sort -u | awk '
        {
            if (NF == 1) {
                TAG = "GA";
            } else {
                TAG = $2;
            }

            split($1, t, ".");
            tpd_version = t[1]"."t[2]"."t[3]"."TAG;
            print tpd_version;
        }
    '
}

# Function to check TPD version
check_tpd_version()
{
    if [[ $# -eq 0 || $# -gt 2 ]]; then
        echo -e "ERROR: Insufficient arguments passed to ${FUNCNAME[0]} function - caller: ${FUNCNAME[1]}"
        exit 1
    fi

    local tpd_versions="$1"
    local partition=""

    if [ $# -ge 2 ]; then
        local partition=$2
    fi

    local tpd=$(get_tpd_version $partition)
    echo -e "$tpd" | egrep -qw "$tpd_versions"

    if [ $? -ne 0 ]; then
        echo -e "$(basename $0 .sh): Script is not applicable for $tpd release or version."
        exit 1
    fi
}

is_sysmgr_up()
{
    showsysmgr | grep -q "System is up and running"
    if [ $? -ne 0 ]; then
        echo -e "$GEN_SCRIPT: sysmgr is not started."
        (set -x; showsysmgr -d) 2>&1
        exit 1
    fi
}

isallnodesintegrated()
{
    eval $(clwait --bash) # It exports mynode, master, online and integrated
    if [ $integrated -ne $online ]; then
        echo -e "$GEN_SCRIPT: Not all nodes integrated. clwait: $(clwait 2>/dev/null)"
        exit 1
    fi
}

isit_dds_setup()
{
  # Check is it dedup setup
  showvv -nohdtot -p -prov dds -showsysobjs | grep -qw dds
  if [ $? -ne 0 ]; then
    echo -e "\nERROR: No dds volume(s) found. This script is not applicable."
    exit 1
  fi
}

usage()
{
    local prog=$(basename $0)

    echo -e "Usage: $prog --verify\n"

    echo -e "--verify: Verify whether any Dirty exceptions not flushed for >= $DIRTY_EXCEPTION_THRESHOLD minutes.\n"

    exit 1
}

# - offsets of mpg_hdr_t structure from 3.2.1.MU3
#crash> struct -o mpg_hdr_t
#typedef struct mpg_hdr {
#    [0] vv_hdr_t *mpg_vhdr;
#    [8] dskblk64_t mpg_dbase;
#   [16] vtte_t mpg_dptr;
#   [24] tpd_u8 mpg_lvl;
#   [25] tpd_u8 mpg_state; <--
#   [26] tpd_u8 mpg_flags;
#   [27] tpd_u8 mpg_dmsk;
#   [28] dskblk32_t mpg_sz;
#   [32] short int mpg_rsv_num;
#   [34] short int mpg_nmpg;
#   [36] int mpg_busy; <--
#   [40] tpd_u64 mpg_sync_tick;
#   [48] log_list_t mpg_log_list;
#   [64] les_t *mpg_lgptbl;
#   [72] excp_async_t *mpg_async;
#   [80] short int mpg_ndchild;
#   [82] short int mpg_dirty_mge;
#   [88] excp_pgin_sync_t mpg_pgin_sync;
#  [120] struct mpg_hdr *mpg_nxt;
#  [128] struct mpg_hdr *mpg_prv; <--
#  [136] ea_dlist_t mpg_dirty_lnk;
#  [152] struct ptbl_dlist mpg_dchild;
#  [168] ptbl_dlist_t *mpg_dlist;
#  [176] struct mpg_hdr *mpg_parent;
#  [184] mpg_sync_cb_t *mpg_scb;
#  [192] tpd_time_t mpg_in_dirty_q_time;
#  [200] tpd_time_t mpg_last_scan_time;
#  [208] tpd_time_t mpg_last_flush_time; <--
#  [216] tpd_time_t mpg_last_reque_time;
#  [224] vtte_t *mpg_ptes;
#} mpg_hdr_t;
#SIZE: 232

check_dirty_exception_data()
{
    local node=$1
    local dlist=$2
    local addr=$3

    echo "$addr" | grep -q "0xff"
    if [ $? -ne 0 ]; then
        return 1
    fi

    local mpg_state_addr=$(echo $((addr+25)) | awk --non-decimal-data '{ printf "%#lx\n", $1 }')
    local mpg_state=$(showmemval kernel$node none 8 1 $mpg_state_addr | awk '{ print $NF }')

    local mpg_busy_addr=$(echo $((addr+36)) | awk --non-decimal-data '{ printf "%#lx\n", $1 }')
    local mpg_busy=$(showmemval kernel$node none 32 1 $mpg_busy_addr | awk '{ print $NF }')

    local mpg_prv_addr=$(echo $((addr+128)) | awk --non-decimal-data '{ printf "%#lx\n", $1 }')
    local mpg_prv=$(showmemval kernel$node none 64 1 $mpg_prv_addr | awk --non-decimal-data '{ printf "%#lx\n", $NF }')
    MPG_PRV=$mpg_prv

    local mpg_last_flush_time_addr=$(echo $((addr+208)) | awk --non-decimal-data '{ printf "%#lx\n", $1 }')
    local mpg_last_flush_time=$(showmemval kernel$node none 64 1 $mpg_last_flush_time_addr | awk '{ print $NF }')

    curr_time=$(date "+%s")
    time_diff=$((curr_time - mpg_last_flush_time))

    if [ $time_diff -ge $((DIRTY_EXCEPTION_THRESHOLD*60)) ] && [[ $mpg_state == $MPG_DIRTY || $mpg_state == $MPG_DIRTY_AGAIN ]]; then
        flush_time=$(date -d @$mpg_last_flush_time "+%Y-%m-%d %H:%M:%S")
        time_diff=$((curr_time - mpg_last_flush_time))
        days=$((time_diff / 86400))
        hours=$(((time_diff / 3600) % 24))
        minutes=$(((time_diff % 3600) / 60))
        seconds=$((time_diff % 60))

        local mpg_state_trans=${MPG_STATE_TRANS[$mpg_state]}

        printf "\tNode %d list #%d %s mpg_busy=%d mpg_state=%d(%s) last flushed: %s or outstanding for %dd:%02dh:%02dm:%02ds\n" \
             $node $dlist $addr $mpg_busy $mpg_state $mpg_state_trans "$flush_time" $days $hours $minutes $seconds
        return 1
    fi

    return 0
}

check_dtable_exception_list()
{
    echo "${FUNCNAME[0]}: Checking integrated nodes dtable exception for list 2 and 3, it can take few minutes."
    $(clwait --bash)
    count=1
    while [ $count -le $MAX_COUNT ]; do
        local dlist_check_flag=0
        for dlist in 2 3; do
            if [ $dlist -eq 2 ]; then
                dlist_flag=(${L2_DLIST_FLAG[*]})
            else
                dlist_flag=(${L3_DLIST_FLAG[*]})
            fi
            for node in {0..7}; do
                if (( (integrated & (1 << node)) == 0 || ${dlist_flag[$node]} >= 0 )); then
                    continue
                fi

                dirty_list_len=$(showmemval kernel$node none 32 1 dirty_ptbls+$((dlist*16 + 8)) | awk '{ print $NF }')
                if [ $dirty_list_len -eq 0 ]; then
                    echo "- node$node:dlist $dlist is empty."
                    dlist_flag[$node]=0 # Skip it from next loop
                    continue
                fi
                dlist_check_flag=1

                MPG_PRV=""
                local list_head=$(showmemval kernel$node none 64 1 dirty_ptbls+$((dlist*16)) | awk --non-decimal-data '{ printf "%#lx\n", $NF }')
                check_dirty_exception_data $node $dlist $list_head
                if [ $? -ne 0 ]; then
                    dlist_flag[$node]=1
                    continue
                fi

                # Analyze mpg_hdr_t.mpg_prv
                if [ $dirty_list_len -gt 1 ]; then
                    check_dirty_exception_data $node $dlist $MPG_PRV
                    if [ $? -ne 0 ] && [[ $mpg_state == $MPG_DIRTY || $mpg_state == $MPG_DIRTY_AGAIN ]]; then
                        dlist_flag[$node]=1
                        continue
                    fi
                fi
            done # End of node loop

             # Update globals
            if [ $dlist -eq 2 ]; then
                L2_DLIST_FLAG=(${dlist_flag[*]})
            else
                L3_DLIST_FLAG=(${dlist_flag[*]})
            fi
        done # End of dlist loop

        if [ $dlist_check_flag -eq 0 ]; then
            break
        fi
        ((count++))
        sleep 1
    done

    local node_list=""

    for node in {0..7}; do
        if [[ ${L2_DLIST_FLAG[$node]} -gt 0 || ${L3_DLIST_FLAG[$node]} -gt 0 ]]; then
            node_list=${node_list:+$node_list","}
            node_list="${node_list}node$node"
        fi
    done

    if [ -n "$node_list" ]; then
        echo -e "\n${FUNCNAME[0]}: Dirty exceptions not flushed for >= $DIRTY_EXCEPTION_THRESHOLD minutes in $node_list - Consult Support."
    else
        echo -e "\n${FUNCNAME[0]}: No Dirty exceptions found in >= $DIRTY_EXCEPTION_THRESHOLD minutes."
    fi

    if [ $count -ge $MAX_COUNT ]; then
        echo -e "\nNote: Before exiting the script, it exhausted max retries."
    fi
}

if [ $# -ne 1 ]; then
    usage
fi

check_tpd_version "$TPD_VERSIONS" root

FS=""
SHOWVERSION_OPT=""

option=$1

case $option in
    "--verify")
        ;;

    *)
        usage
        ;;
esac

is_sysmgr_up

isit_dds_setup

isallnodesintegrated

get_script_version $(basename $0) $*

check_dtable_exception_list
retval=$?

exit $retval
