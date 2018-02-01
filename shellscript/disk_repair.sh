#!/bin/bash
# disk_repair.sh: Script for repairing failed drives

Version=1.02

INTER_SLEEP_TIME=10

SCRIPT="disk_repair.sh"
SHOWPD_COLS="Id,CagePos,State,Detailed_State,Node_WWN,MFR,Model,FW_Rev,Protocol,MediaType"

usage()
{
    local prog=$(basename $0)

    echo -e "Usage: $prog --install <degraded>|<failed> : Repair drives in 'degraged|failed' state"
    echo -e "       $prog --install list <drive_list>   : Repair specified drives in degraded/failed state."
    echo -e "       For ex:- $SCRIPT --install list 23,45,57,200\n"
    echo -e "       $prog --verify  <degraded>|<failed> : Verify drives in 'degraged|failed' state"
    echo -e "       $prog --verify  list <drive_list>   : Verify specified drives in degraded/failed state."

    exit 1
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

is_sysmgr_up()
{
    showsysmgr | grep -q "System is up and running"
    if [ $? -ne 0 ]; then
        echo "$SCRIPT: sysmgr is not started."
        (set -x; showsysmgr -d) 2>&1
        exit 1
    fi
}

GetConfirmation()
{
  local MSG="$1"

  unset GETCONFIRMATION
  echo -e "\n$(basename $0 .sh): $MSG"
  while true ; do
    echo -e -n "select y=yes n=no q=quit : "
    read reply
    if [ "$reply" == "y" ]; then
        GETCONFIRMATION="APPLY-IT"
        echo
        break
    elif [[ "$reply" == "q" || "$reply" == "n" ]]; then
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

apply_controlpd_spindown()
{
    local pd=$1
    local pd_wwn=$2
    local spindown_sleep_time=15

    (set -x; controlpd spindown -ovrd ${pd_wwn})
    (set -x; sleep $spindown_sleep_time)
}

apply_controlpd_spinup()
{
    local pd=$1
    local pd_wwn=$2

    (set -x; controlpd spinup ${pd_wwn})
}

apply_controlpd_clearerr()
{
    local pd=$1
    local pd_wwn=$2

    (set -x; controlpd clearerr ${pd_wwn})
}

apply_controlmag_offloop()
{
    local pd=$1
    local pd_cage_pos=$2

    local cage=$(echo $pd_cage_pos | awk -F ":" '{ print $1 }')
    local mag=$(echo $pd_cage_pos | awk -F ":" '{ print $2 }')
    local disk=$(echo $pd_cage_pos | awk -F ":" '{ print $3 }')

    # controlmag offloop -disk # cage# <mag#>
    # Ex:- controlmag offloop -disk 0 cage1 2  (for 1:2:0)
    (set -x; controlmag offloop -f -disk $disk cage$cage $mag)
}

apply_controlmag_onloop()
{
    local pd=$1
    local pd_cage_pos=$2

    local cage=$(echo $pd_cage_pos | awk -F ":" '{ print $1 }')
    local mag=$(echo $pd_cage_pos | awk -F ":" '{ print $2 }')
    local disk=$(echo $pd_cage_pos | awk -F ":" '{ print $3 }')

    # controlmag onloop -disk # cage# <mag#>
    # Ex:- controlmag onloop -disk 0 cage1 2  (for 1:2:0)
    (set -x; controlmag onloop -f -disk $disk cage$cage $mag)
}

if [[ $# -lt 2 || $2 == "list" && $# -eq 2 || $# -gt 3 ]]; then
    usage
fi

option=$1
type=$2

is_sysmgr_up

case $option in
    "--install")
        ;&

    "--verify")
        case $type in
        degraded)
            pd_cmd_opt="-degraded"
        ;;

        failed)
            pd_cmd_opt="-failed"
        ;;

        list)
            drive_list=$3
            drive_list=$(echo "$drive_list" | sed -e "s/,/ /g")
            pd_cmd_opt="$drive_list"
        ;;

        *)
            usage
        ;;
        esac

        showpd_data=$(showpd -nohdtot -showcols $SHOWPD_COLS $pd_cmd_opt | awk '($3=="degraded" || $3=="failed")')
        ;;

    *)
        usage
        ;;
esac

get_script_version $(basename $0) $*

showpd_data=$(echo "$showpd_data" | egrep -v "^\---|no_valid_ports|\?|No PDs listed")

if [ -z "$showpd_data" ]; then
    msg=""
    if [ $type == "list" ]; then
       msg=" in degraded/failed state"
    fi
    echo "No drives were found for '$type' type$msg."
    exit
fi

echo -e "\n$showpd_data"

drives_cnt=$(echo "$showpd_data" | wc -l)

if [ $option == "--verify" ]; then
    echo -e "\n- $drives_cnt drive(s) were found for '$type' type."
    exit
fi

GetConfirmation "$drives_cnt drive(s) were found for '$type' type. Would you like to repair them?"
if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
    exit
fi

IFS=$'\n' showpd_data=($(echo "$showpd_data"))

current_cnt=0
pd_list=""

while [ $current_cnt -lt $drives_cnt ]; do
    pd_id=$(echo "${showpd_data[current_cnt]}" | awk '{ print $1 }')
    pd_cage_pos=$(echo "${showpd_data[current_cnt]}" | awk '{ print $2 }')
    pd_wwn=$(echo "${showpd_data[current_cnt]}" | awk '{ print $5 }')

    echo -e "\nWorking on pd: $pd_id"
    #apply_controlmag_offloop $pd_id $pd_cage_pos # Don't uncomment without lab/dev approoval

    apply_controlmag_onloop $pd_id $pd_cage_pos

    #apply_controlpd_spindown $pd_id $pd_wwn # Don't uncomment without lab/dev approoval

    apply_controlpd_spinup $pd_id $pd_wwn

    apply_controlpd_clearerr $pd_id $pd_wwn

    pd_list=${pd_list:+$pd_list" "}
    pd_list=${pd_list}$pd_id
    (set -x; showpd -nohdtot -showcols $SHOWPD_COLS $pd_id)
    ((current_cnt++))

    if [ $current_cnt -lt $drives_cnt ] ;then
        echo -e "\n\n############################################################"
        echo -e -n "# - disk repair completed for $current_cnt out of $drives_cnt drives."
        GetTimedConfirmation $INTER_SLEEP_TIME 2 "# Enter 'n' or 'q' to exit from the script. Otherwise it will proceed."
        if [ "$USER_REPLY" == "No" ]; then
            echo -e "\n*** User requested to quit from the script - exiting now. ***\n"
            break
        fi
        echo -e "\n# - No reply from user, proceeding to next drive."
        echo -e "############################################################"
    fi

done

wait_time=120

echo -e "\n- Wait for $wait_time seconds before getting latest status of the drives."
(set -x; sleep $wait_time)
echo -e "\nCurrent state of the repaired drives:"
echo $pd_list | xargs showpd -nohdtot -showcols $SHOWPD_COLS
