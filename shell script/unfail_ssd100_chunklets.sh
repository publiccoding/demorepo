#!/bin/bash
# unfail_ssd100_chunklets.sh: Scrub SSD RPM 100 failed chunklets to unfail them.
# - Defect(s) it works around: Bug 196653

# How script works:
# - For --install option it creates /var/opt/tpd/touchfiles/no_ssd_unmap touch file.
# - Get list of failed chunklets for SSD drive with RPM 100.
# - If none of chunklets are failed then logs, "None of the chunklets are in failed media state" and exits from the script.
#
# - Loop on each pd with failed chunkets
#   - Precheck whether any admitted drive in the array in failed/degraded state. If then, exit from the script.
#   - Loop on failed chunklets for given pd
#     - 'controlpd chmederr unset <chunklet number> <PD WWN>' to unfail a chunklet on a PD.
#     - 'checkpd scrub -ch <chunklet number> <pdid> to scrub specific chunklets.
#     - If the PD scrub fails marks chunklet as media failed by running, controlpd chmederr set <chunklet number> <PD WWN>.
#     - If PD scrub failures are > $MAX_FAILED_CHUNKLETS then marks retval=$FAILPERM then breaks from inner loop then moves to next pd.
#
#- If retval marked as FAIL then logs, Error: Unable to unfail failed chunklets. Status: Failed. Consult Support.
#
#- For --uninstall, it removes /var/opt/tpd/touchfiles/no_ssd_unmap touch file.
#
#- For --verify
#  - It checkes whether /var/opt/tpd/touchfiles/no_ssd_unmap touch file is present?
#  - Lists if failed chunklets are present.

Version=1.00

TPD_VERSIONS="3.1.3|3.2.1|3.2.2.GA|3.2.2.MU[123]"

SCRIPT=unfail_ssd100_chunklets.sh
PROMPT_FILE="/tmp/unfail_ssd100_chunklets.prompt"

MAX_FAILED_CHUNKLETS=5 # Max failed chunklets per pd

ALPHABET=({a..z} {A..Z})
MAJOR=2
INFORMATIONAL=5
TOUCHFILESDIR="/var/opt/tpd/touchfiles"
NO_SSD_UNMAP=$TOUCHFILESDIR/no_ssd_unmap

# Failure Codes (or) exit values from scripts
PASS=0        # Passed
FAILPERM=1    # Failure, permanent
FAILTEMP=2    # Failure, temporary
FAILWARN=3    # Warning (only allowed during precheck and postupgrade)
FAILNOTRUN=4  # Failed, Not Yet Run
FAILNA=5      # Failed, Not Applicable
FAILOTHER=127 # Failed, other unknown failure

usage()
{
    local PROG=$(basename $0)

    echo -e "Usage: $PROG --install"
    echo -e "       $PROG --uninstall"
    echo -e "       $PROG --verify\n"

    echo "--install   : Installs $NO_SSD_UNMAP file and unfails 'SSD RPM 100' failed chunklet(s)."
    echo "--uninstall : Removes $NO_SSD_UNMAP file."
    echo "--verify    : Verify whether $NO_SSD_UNMAP installed and check 'SSD RPM 100' failed chunklet(s)."

    echo -e "\nNote:"
    echo " - If upgrade is reverted or successful, --uninstall the work-around to restore back to defaults."

    exit $FAILPERM
}

get_script_version()
{
    local patches=$(showversion -b | awk '/^Patches/ && $2 != "None" { print "+"$2 }')
    local tpd=$(showversion -b)
    tpd=$(translate_tpd_release_version "$tpd")

    local altroot_tpd=$(showversion -b -r)
    altroot_tpd=$(translate_tpd_release_version "$altrootTPD")

    echo -e "- You are using $SCRIPT script version=$Version, TPD=$tpd$patches and running it on $(date "+%Y-%m-%d %X")"
    echo -e "- clwait: $(clwait)"

    if [ $# -ne 0 ]; then
      echo "- User command line: $*"
    fi

    echo -e "$(showsys -d | grep "^Nodes in Cluster" | sed -e 's/,/,node/g' | awk '{ printf "- Results below are applicable for node%s\n", $NF }')\n\n"
}

translate_tpd_release_version()
{
    local tpd_release_version="$1"

    echo "$tpd_release_version" | grep "^Release version" | sed -e 's/Release version//g' -e 's/[()]//g' | sort -u | awk '
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
        echo "ERROR: Insufficient arguments passed to ${FUNCNAME[0]} function - caller: ${FUNCNAME[1]}"
        exit 1
    fi

    local tpd_versions="$1"
    local partition=""

    if [ $# -ge 2 ]; then
        local partition=$2
    fi

    local tpd=$(get_tpd_version $partition root)
    echo "$tpd" | egrep -qw "$tpd_versions"

    if [ $? -ne 0 ]; then
        echo "$SCRIPT: Script is not applicable for $tpd release or version."
        exit 1
    fi
}

is_sysmgr_up()
{
    showsysmgr | grep -q "System is up and running"
    if [ $? -ne 0 ]; then
        echo "$SCRIPT: sysmgr is not started."
        (set -x; showsysmgr -d) 2>&1
        exit 1
    fi
}

isallnodesintegrated()
{
    eval $(clwait --bash) # It exports mynode, master, online and integrated
    if [ $integrated -ne $online ]; then
        echo "$SCRIPT: Not all nodes integrated. clwait: $(clwait 2>/dev/null)"
        exit 1
    fi
}

GetConfirmation()
{
  local MSG="$1"

  GETCONFIRMATION=""
  echo -e "\n${FUNCNAME[1]}: $MSG"
  while true ; do
    echo -e -n "select y=yes n=no q=quit : "
    read reply
    if [ "$reply" == "y" ]; then
        GETCONFIRMATION="APPLY-IT"
        echo
        break
    elif [[ $reply == "q" || $reply == "n" ]]; then
        echo "- As per user not applying this workaround."
        GETCONFIRMATION="SKIP-IT"
        break
    else
        echo "Unrecognized input \"$reply\""
    fi
  done
}

GetTimedConfirmation()
{
  local max_time=$1
  local inter_delay=$2
  local MSG="$3"

  stty -echo
  while read -e -s -t 0.1 -n 10000; do : ; done # Flush earlier user inputs
  stty echo
  USER_REPLY=""
  time=0
  while [ $time -lt $max_time ]; do
    echo -e -n "\n$MSG Reply within $((max_time - time)) seconds : "
    reply=""
    read -t $inter_delay reply
    if [ -n "$reply" ]; then
        if [ "$reply" == "y" ]; then
            USER_REPLY="Yes"
            echo
            break
        elif [[ "$reply" == "q" || "$reply" == "n" ]]; then
            USER_REPLY="No"
            break
        else
            echo "Unrecognized input '$reply'"
        fi
    fi
    ((time+=inter_delay))
  done
}

check_pd_type_rpm()
{
    local type=$1
    local rpm=$2

    showpd -p -devtype $type -rpm $rpm -nohdtot 2>&1 | grep -q "$type"

    if [ $? -ne 0 ]; then
        echo "$SCRIPT: Script is not applicable for this configuration."
        exit $FAILNA
    fi
}

get_failed_chunklets()
{
    local type=$1
    local rpm=$2

    showpdch -fail -p -devtype $type -rpm $rpm -nohdtot 2>/dev/null | awk '/failed/ {
        chnk_failed[$1]++
        if (chnk_list[$1] == "") { sep=""} else { sep="," }
        chnk_list[$1]=chnk_list[$1]sep$2
    } END {
        for (elem in chnk_failed) {
            if (chnk_failed[elem] > 5) status="Major*"
            else status="Minor"
            printf "%5d  %5d  %-6s  %s\n", elem, chnk_failed[elem], status, chnk_list[elem]
        }
    }' | sort -nk2
}

unfail_ssd100_chunklets()
{
    local option=$1
    local type=$2
    local rpm=$3
    local retval=$PASS

    if [ "$option" == "--install" ]; then
        echo -e "(${ALPHABET[ALPHCNT++]}) Creating $NO_SSD_UNMAP touch file."
        onallnodes "touch $NO_SSD_UNMAP" > /dev/null

        local failed_chunklets=$(get_failed_chunklets SSD 100)

        if [ -z "$failed_chunklets" ]; then
            echo -e "\n(${ALPHABET[ALPHCNT++]}) Verifying $NO_SSD_UNMAP touch file."
            onallnodes "ls -l $NO_SSD_UNMAP 2>/dev/null"
            echo -e "\n${FUNCNAME[0]}: None of the chunklets are in failed media state. Status: Passed."
            return $PASS
        fi

        local failed_chunklets_pd_cnt=$(echo "$failed_chunklets" | wc -l)
        local total_failed_chunklets=$(echo "$failed_chunklets" | awk '{ sum+=$2 } END { print sum }')
        echo -e "\n(${ALPHABET[ALPHCNT++]}) List of failed chunklet(s):"
        echo -e "\nId     Count  Status  Chunklets\n$failed_chunklets"

        GetConfirmation "Would you like to unfail $total_failed_chunklets chunklet(s) in $failed_chunklets_pd_cnt pd(s)?"
        if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
            exit
        fi

        IFS=$'\n' failed_chunklets=($(echo "$failed_chunklets"))

        for ((pd_cnt=0; pd_cnt < ${#failed_chunklets[@]}; pd_cnt++)); do
            pdid=$(echo "${failed_chunklets[pd_cnt]}" | awk '{ print $1 }')
            pd_chnk_failed_count=$(echo "${failed_chunklets[pd_cnt]}" | awk '{ print $2 }')
            #pd_chnk_failed_status=$(echo "${failed_chunklets[pd_cnt]}" | awk '{ print $3 }')
            pd_chnk_failed_list=$(echo "${failed_chunklets[pd_cnt]}" | awk '{ print $4 }')

            local showpd_s_data=$(showpd -s -failed -nohdtot | grep -v -e "No PDs listed" -e "^---")
            if [ -n "$showpd_s_data" ]; then
                echo "Error: Drives are in failed/degraded state."
                echo "$showpd_s_data"
                retval=$FAILPERM
                break
            fi

            echo -e "\n($((pd_cnt+1))) Unfail $pd_chnk_failed_count failed chunket(s) $pd_chnk_failed_list in pd $pdid."

            pd_state_wwn=$(showpd -showcols Id,State,Node_WWN -nohdtot $pdid)

            pdstate=$(echo "$pd_state_wwn" | awk '{ print $2 }')
            if [ "$pdstate" == "failed" ]; then
                echo "${FUNCNAME[0]}: pd $pdid is in failed state. Replace the drive prior to upgrade. Consult Support."
                retval=$FAILPERM
                continue
            fi

            pdwwn=$(echo "$pd_state_wwn" | awk '{ print $3 }')
            if [ -z "$pdwwn" ]; then
                echo "${FUNCNAME[0]}: Unable to fetch WWN of pd $pdid. Consult Support."
                retval=$FAILPERM
                continue
            fi

            local unfail_chnk_failed=0
            local chnk_cnt=1
            max_chnk_cnt=$(echo "$pd_chnk_failed_list" | sed -e "s/,/ /g" | wc -w)
            for chnk in $(echo $pd_chnk_failed_list | tr ',' '\n'); do
                echo -e "\n- unfail chunklet $chnk in pd $pdid or #$chnk_cnt out of $max_chnk_cnt."
                ((chnk_cnt++))
                controlpd chmederr unset $chnk $pdwwn # unfail a chunklet on a PD

                checkpd scrub -ch $chnk $pdid # scrub specific chunklet

                if [ $? -ne 0 ]; then
                    # PD scrub failed, marking chunklet in media failed state
                    echo "- Unable to unfail chunklet $chnk in pd $pdid, marking chunklet as failed."

                    controlpd chmederr set $chnk $pdwwn

                    ((unfail_chnk_failed++))

                    if [ $unfail_chnk_failed -gt $MAX_FAILED_CHUNKLETS ]; then
                        echo -e "\n- Unable to unfail required number of chunklets in pd $pdid. Replace the drive. Consult Support.\n"
                        retval=$FAILPERM
                        break
                    fi
                fi
            done

            if [ $pd_cnt -lt $((failed_chunklets_pd_cnt - 1)) ] ;then
                if [ -f $PROMPT_FILE ]; then
                    GetConfirmation "- unfail chunklets completed for $((pd_cnt+1)) out of $failed_chunklets_pd_cnt pds. Would you like to proceed to next pd?"
                    if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
                        echo -e "\n*** User requested to quit from the script - exiting now. ***\n"
                        break
                    fi
                else
                    echo -e "\n\n############################################################"
                    echo -e -n "# - unfail chunklets completed for $((pd_cnt+1)) out of $failed_chunklets_pd_cnt pds."
                    GetTimedConfirmation 10 2 "# Enter 'n' or 'q' to exit from the script. Otherwise it will proceed."
                    if [ "$USER_REPLY" == "No" ]; then
                        echo -e "\n*** User requested to quit from the script - exiting now. ***\n"
                        break
                    fi
                    echo -e "\n# - No reply from user, proceeding to next drive."
                    echo -e "############################################################"
                fi
            fi

        done
    elif [ "$option" == "--uninstall" ]; then
        echo -e "(${ALPHABET[ALPHCNT++]}) Removing $NO_SSD_UNMAP touch file."
        onallnodes "rm -f $NO_SSD_UNMAP" > /dev/null
    fi

    echo -e "\n(${ALPHABET[ALPHCNT++]}) Verifying $NO_SSD_UNMAP touch file."
    onallnodes "ls -l $NO_SSD_UNMAP 2>/dev/null"

    echo -e "\n(${ALPHABET[ALPHCNT++]}) Chunklets in failed media state?"
    local failed_chunklets=$(get_failed_chunklets SSD 100)

    if [ -z "$failed_chunklets" ]; then
        echo -e "${FUNCNAME[0]}: None of the chunklets are in failed media state. Status: Passed."
    else
        echo -e "- Failed chunklets on each pd basis.\n"
        echo -e "Id     Count  Status  Chunklets\n$failed_chunklets"

        echo "$failed_chunklets" | grep -qw "Major"
        if [ $? -eq 0 ]; then
            echo -e "\nNote: Status is 'Major', replace the drive and/or run with '--install' option to scrub failed chunklets to unfail them."
            retval=$FAILPERM
        fi

    fi

    if [[ "$option" == "--install" && $retval -ne 0 ]]; then
        echo -e "\nError: Unable to unfail failed chunklets. Status: Failed. Consult Support."
    elif [ "$option" == "--install" ]; then
        echo -e "\n${FUNCNAME[0]}: Status Passed."
    fi

   return $retval
}

if [[ $# -eq 0 || $# -gt 2 ]]; then
    usage
fi

ALPHCNT=0

option=$1

is_sysmgr_up

isallnodesintegrated

case $option in
    "--install")
        check_tpd_version "$TPD_VERSIONS"

        check_pd_type_rpm SSD 100
    ;;

    "--uninstall")
    ;;

    "--verify")
        ;;

    *)
        usage
        ;;
esac

get_script_version $(basename $0) $*

unfail_ssd100_chunklets $option SSD 100
retval=$?

exit $retval
