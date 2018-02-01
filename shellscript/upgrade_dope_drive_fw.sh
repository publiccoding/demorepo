#!/bin/bash
# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
#
# upgrade_dope_drive_fw.sh: Upgrade DOPE drives firmware if they are loaded with $FW_REV firmware version or lower than 3P08.
# Bug(s) Addressed: 199754, 212401, 211833
#
# Note:
# - If /tmp/upgrade_dope_drive_fw.prompt file is present, script waits until user responds before proceeding to next drive.
# - Otherwise it waits for 10 seconds for user response before proceeding automatically.
#
# High level summary on how script works:
#  1) If lock file exists then exit otherwise create lock and proceed.
#  2) For each DOPE drive, check recycle stall. If any drive matches with 'VPC mismatch' pattern then add to list drives need to be replaced.
#     - If any drives need to be replaced then exit from the script.
#  3) Create SCSI UNMAP touch file then restart sysmgr to disable SCSI UNMAP during drive firmware upgrade.
#  4) Get list of SanDisk DOPE drives with lower than 3P08 firmware loaded.
#  5) Check any drive chunklet(s) in non-normal state?
#     If then check every 10 seconds until the condition is cleared.
#     - User can abort the script by using <ctrl>c.
#
#  6) Select physical drive from the list.
#  7) Check selected drive model listed in showfirmwaredb output? If not, skip it.
#  8) Check selected drive chunklet(s) in non-normal state?
#     If then check every 10 seconds until condition is cleared.
#     - User can abort the script by using <ctrl>c.
#  9) upgradepd <pd>
#     - If upgradepd fails
#       - controlpd clearerr $pd_node_wwn
#       - Wait for drive is in normal-normal or degraded-old_firmware state. If not, retry every 10 seconds for 12 times.
#       - If above condition fails or TPD_ERROR_CODE is set to TE_INVALID then script runs spindown and spinup
#       - Retry upgradepd until it exhausts 10 retries before failing the script.
#    - If upgradepd is successful then
#      - Wait for the drive in normal/degraded state. If not, retry every 10 seconds for 90 times before failing the script.
# 10) Check selected drive chunklet(s) in non-normal state?
#     If then check every 10 seconds until condition is cleared.
#     - User can abort the script by using <ctrl>c.
# 11) Wait for drive in normal-normal or degraded-old_firmware state. If not, retry every 10 seconds for 90 times before failing the script.
# 12) Check recycle stall <pd>. If 'VPC mismatch' pattern is noticed then log a message and exit from the script.
#
# 13) User will be prompted to quit from the script. If no input comes from user within 10 seconds then it automatically proceeds to next drive.
#
# 14) Log how many drives successfully upgraded and how long it took to complete it.
# 15) Log drive firmware summary.
# 16) Log location of the log file.
#
# - Table below is used while checking DOPE drive VPC mismatch:
# ----------------------------------------------------------------------------------------------
# | DOPE FW  | Max Length | Header check? | VPC Pattern in drive event log                     |
# |----------|------------|---------------|----------------------------------------------------|
# | 3P01     | 0x80000    | NA            | 1) ab 48 46 02 24 00 .. 01 0b  (or)                |
# |          |            |               | 2) ab 4C 46 02 24 02 .. .. .. .. .. 01 0b          |
# | 3P04     | 0x80000    | NA            | ab 02 10 00 00 25 20 .1 .. .. .. .. .. 0b 00 00 00 |
# | 3P07     | 0x80008    | Yes, needed   | ab 02 10 00 00 25 20 .1 .. .. .. .. .. 0b 00 00 00 |
# | 3P08     | 0x80008    | Yes, needed   | ab 02 10 00 00 25 20 .1 .. .. .. .. .. 0b 00 00 00 |
# ----------------------------------------------------------------------------------------------
#
# Note: In corner case if upgradepd repeatedly fails for given drive due to TE_INVALID then
#       user may need to restart sysmgr to recover from the problem.

Version=1.06

# DOPE drives target firmware is 3P08
# - It is applicable for 3.2.1.MU3+P57 3.2.1.MU5+P59 3.2.1.MU2+P62 3.2.2.MU2+P53 3.2.2.MU4+P57 3.2.2.MU3+P61
TPD_VERSIONS="3.2.1.MU[235]|3.2.2.MU[2-9]|3.3.1"

TOUCHFILESDIR="/common/touchfiles"
NO_SSD_UNMAP=$TOUCHFILESDIR/no_ssd_unmap

SCRIPT=upgrade_dope_drive_fw.sh
PROMPT_FILE="/tmp/${SCRIPT%.sh}.prompt"
LOGFILE="/var/log/tpd/${SCRIPT%.sh}.log"
ALPHCNT=0
ALPHABET=({a..z} {A..Z})

TMP_FILE=/tmp/$SCRIPT.$$
LOCK_FILE=/tmp/LCK_${SCRIPT%.sh}

EVENT_LOG=/tmp/event_log

# DOPE drive model
DRIVES_MODEL="DOPE0480S5xnNMRI|DOPE1920S5xnNMRI"
DRIVE_MODEL_LIST="$DRIVES_MODEL"

# List of firmware versions need upgrade to latest
FW_REV="3P01|3P04|3P07"

# Firmware versions covering VPC pattern checking
VPC_CK_FW_REV="3P01|3P04|3P07|3P08"

# Manufacturer
MFR="SanDisk"

cleanup()
{
    rm -f $LOCK_FILE $EVENT_LOG
    enable_ssd_unmap
    trap "" EXIT
    exit
}

# Restart sysmgr then wait for it to get restarted
sysmgr_quiet_restart()
{
    local retval=1

    (set -x; setsysmgr -f quiet_restart)
    echo -e "\n$(date "+%Y-%m-%d %T") Waiting for sysmgr to be restarted. It can take few minutes."

    for i in {1..30}; do
        showsysmgr 2>/dev/null | grep -q "System is up and running"
        if [ $? -eq 0 ]; then
            retval=0
            break
        fi
        sleep 10
    done

    if [ $retval -ne 0 ]; then
        (set -x; showsysmgr)
        echo "Error: Failed to restart sysmgr."
        exit 1
    fi

}

# Create $NO_SSD_UNMAP touch file then quiet restart sysmgr
disable_ssd_unmap()
{
    echo "$(date "+%Y-%m-%d %T") Disabling SCSI UNMAP."
    onallnodes "touch $NO_SSD_UNMAP" > /dev/null

    sysmgr_quiet_restart
    sleep 120
}

# Remove $NO_SSD_UNMAP touch file then quiet restart sysmgr
enable_ssd_unmap()
{
    onallnodes "ls -l $NO_SSD_UNMAP 2>/dev/null" | grep -q $NO_SSD_UNMAP
    if [ $? -ne 0 ]; then
        return
    fi

    echo "$(date "+%Y-%m-%d %T") Enabling SCSI UNMAP."

    onallnodes "rm -f $NO_SSD_UNMAP 2>/dev/null" | grep -q $NO_SSD_UNMAP

    # After removing touch $NO_SSD_UNMAP file for 3.3.1+ sysmgr will resume SCSI UNMAP threads automatically.
    showversion -b | grep -q "Release version 3.2.[12]"
    if [ $? -ne 0 ]; then
        return
    fi

    sysmgr_quiet_restart
}

usage()
{
    local prog=$(basename $0)

    echo -e "Usage: $prog --install"
    echo -e "       $prog --verify\n"

    echo -e "--install : Upgrade DOPE drive(s) from $FW_REV firmware version."
    echo -e "--verify  : Verify the number of DOPE drive(s) by firmware version.\n"

    exit 1
}

get_script_version()
{
    local patches=$(showversion -b | awk '/^Patches/ && $2 != "None" { print "+"$2 }')
    local tpd=$(showversion -b)
    tpd=$(translate_tpd_release_version "$tpd")

    echo -e "- You are using $SCRIPT script version=$Version, TPD=$tpd$patches and running it on $(date "+%Y-%m-%d %T")"
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

    local tpd=$(get_tpd_version $partition)
    echo "$tpd" | egrep -qw "$tpd_versions"

    if [ $? -ne 0 ]; then
        echo "$(basename $0 .sh): Script is not applicable for $tpd release or version."
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

# Function as per bug 212401 comment 29
check_showpdch_non_normal()
{
    local pd_id=$1

    [ $pd_id == "all" ] && pd_id=""

    local count=1
    echo -e "\n$(date "+%Y-%m-%d %T") (${ALPHABET[ALPHCNT++]}) Checking any chunklet(s) of PD $pd_id in non-normal state?"
    while true; do
        local showpdch_log=$(showpdch -nohdtot $pd_id 2>&1 | grep -v -e "normal" -e "No chunklet information available")
        if [ -z "$showpdch_log" ]; then
            echo -e "- All of the PD $pd_id chunklets are in normal state."
            break
        fi

        echo "$(date "+%Y-%m-%d %T") - $(echo "$showpdch_log" | wc -l) chunklet(s) reported in non-normal state." \
            "Waiting for them to be cleared (count=$count). To abort press Ctrl-C"
        sleep 10
        ((count++))
    done
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
    fi

    if [[ $reply == "q" || $reply == "n" ]]; then
        echo "- As per user not applying this workaround."
        GETCONFIRMATION="SKIP-IT"
        break
    fi

    echo "Unrecognized input \"$reply\""
  done
}

drive_spindown()
{
    local pd_id=$1
    local pd_node_wwn=$2
    local retval=1

    echo -e "\n$(date "+%Y-%m-%d %T") (${ALPHABET[ALPHCNT++]}) spindown PD $pd_id"
    for i in {1..90}; do # Make sure drive is in offline state
        if (( i % 5 == 1 )); then
            controlpd spindown -ovrd ${pd_node_wwn} # Send drive spindown every 5th retry for recovery
        fi
        echo "$(date "+%Y-%m-%d %T") - Waiting for PD $pd_id WWN $pd_node_wwn spindown to complete (count=$i)"
        local tur_data=$(tcli -e "set pdcdb -i "$pd_id" -tur")
        echo "$tur_data" | grep -q -e "TE_NOTREADY" -e "No path to pd"
        if [ $? -eq 0 ]; then
            echo -e "$(date "+%Y-%m-%d %T") - spindown PD $pd_id Successful.\n"
            retval=0
            break
        fi
        sleep 10
    done

    if [ $retval -ne 0 ]; then
        echo -e "\n$(date "+%Y-%m-%d %T") - spindown PD $pd_id Failed."
        echo "$tur_data"
        controlpd spinup -ovrd ${pd_node_wwn} # Before exiting send drive spinup
    fi

    return $retval
}

drive_spinup()
{
    local pd_id=$1
    local pd_node_wwn=$2
    local retval=1

    echo -e "\n$(date "+%Y-%m-%d %T") (${ALPHABET[ALPHCNT++]}) spinup PD $pd_id"
    for i in {1..90}; do # Make sure drive is in online state
        if (( i % 5 == 1 )); then
            controlpd spinup -ovrd ${pd_node_wwn} # Send drive spinup every 5th retry for recovery
        fi

        echo "$(date "+%Y-%m-%d %T") - Waiting for PD $pd_id WWN $pd_node_wwn spinup to complete (count=$i)"
        local tur_data=$(tcli -e "set pdcdb -i "$pd_id" -tur")
        if [ -z "$tur_data" ]; then
            echo -e "$(date "+%Y-%m-%d %T") - spinup PD $pd_id Successful.\n"
            retval=0
            controlpd clearerr $pd_node_wwn
            break
        fi
        sleep 10
    done

    if [ $retval -ne 0 ]; then
        echo -e "\n$(date "+%Y-%m-%d %T") - spinup PD $pd_id Failed."
        echo "$tur_data"
    fi

    sleep 10
    return $retval
}


drive_spindown_spinup()
{
    drive_spindown $pd_id $pd_node_wwn
    local retval=$?
    if [ $retval -ne 0 ]; then
        (set -x; showpd -nohdtot $pd_id) 2>&1
        (set -x; showpd -nohdtot -s $pd_id) 2>&1
        return $retval
    fi

    sleep 10

    drive_spinup $pd_id $pd_node_wwn
    local retval=$?
    if [ $retval -ne 0 ]; then
        (set -x; showpd -nohdtot $pd_id) 2>&1
        (set -x; showpd -nohdtot -s $pd_id) 2>&1
        return $retval
    fi

    # Make sure drive is in ready state from sysmgr perspective before returning from here
    for i in {1..90}; do # Make sure drive is in normal or 'degraded and old_firmware' state
        echo "$(date "+%Y-%m-%d %T") - Waiting for PD $pd_id is ready from sysmgr perspective (count=$i)"
        local showpd_data=$(showpd -nohdtot -s $pd_id)

        local pd_state=$(echo "$showpd_data" | awk '(($4 == "normal") && ($5 == "normal") || ($4 == "degraded") && \
            (($5 == "spinup") || ($5 == "old_firmware")) \
        )' | grep -v "?")

        if [ -n "$pd_state" ]; then
            echo "$showpd_data"
            echo "$(date "+%Y-%m-%d %T") - PD $pd_id ready from sysmgr perspective."
            return 0
        fi

        echo "$showpd_data" | egrep "normal .*servicing|degraded .*servicing"
        if [ $? -eq 0 ]; then
            echo "- PD $pd_id found in 'servicing' state"
            (set -x; servicemag unmark -f $cage $mag) 2>&1
            (set -x; servicemag clearstatus -f $cage $mag) 2>&1
        fi

        if [[ $i -ge 5 && $((i % 5)) -eq 0 ]]; then
            echo "- PD $pd_id current status: $showpd_data"
            (set -x; controlpd spinup -ovrd ${pd_node_wwn}) 2>&1 # Send drive spinup for recovery
            (set -x; controlpd clearerr ${pd_node_wwn}) 2>&1 # Send drive clearerr for recovery
        fi
        sleep 10
    done

    (set -x; showpd -nohdtot $pd_id) 2>&1
    (set -x; showpd -nohdtot -s $pd_id) 2>&1
    return 1
}

parse_upgrade_pd_error()
{
    local err_buf="$1"

    local pd_error=$( echo "$err_buf" | awk '
        BEGIN { opcod="x"; Node="x"; Tpd_error_code="x"; Tpd_error_info="x"}
        /Opcode / { opcode=$NF }
        / Node /  { Node= $3 }
        /Tpd error code / { Tpd_error_code=$5 }
            /Tpd error info / { gsub(/.* = /, ""); gsub(/ /, "."); Tpd_error_info=$0 }
        END {
            print opcode, Node, Tpd_error_code, Tpd_error_info
        }
        '
    )

    OPCODE=$(echo "$pd_error" | awk '{ print $1 }')
    NODE=$(echo "$pd_error" | awk '{ print $2 }')
    TPD_ERROR_CODE=$(echo "$pd_error" | awk '{ print $3 }')
    TPD_ERROR_INFO=$(echo "$pd_error" | awk '{ print $4 }')
}

upgrade_pd()
{
    local pd_id=$1
    local pd_cage_pos=$2
    local pd_node_wwn=$3
    local max_retry=10
    local retry=0

    local cage=$(echo $pd_cage_pos | awk -F ":" '{ print $1 }')
    local mag=$(echo $pd_cage_pos | awk -F ":" '{ print $2 }')
    local disk=$(echo $pd_cage_pos | awk -F ":" '{ print $3 }')

    # Upgrade PD for max_retry times
    while true; do
        echo -e "\n$(date "+%Y-%m-%d %T") (${ALPHABET[ALPHCNT++]}) Running upgradepd -f $pd_id"
        local upgradepd_error=$(upgradepd -f $pd_id 2>&1; echo upgradepd_exit_value=$?)

        upgradepd_exit_value=$(echo "$upgradepd_error" | grep -w "^upgradepd_exit_value" | awk -F "upgradepd_exit_value=" '{ print $NF }')
        upgradepd_error=$(echo "$upgradepd_error" | grep -v "^upgradepd_exit_value")

        if [ -n "$upgradepd_error" ]; then
            echo -e "$upgradepd_error\n"
        fi

        if [ $upgradepd_exit_value -ne 0 ]; then
            (set -x; controlpd clearerr $pd_node_wwn) 2>&1
            sleep 10
            check_drive_normal 12 $pd_id $pd_cage_pos $pd_node_wwn
            local ret_val=$?

            parse_upgrade_pd_error "$upgradepd_error"
            if [[ $ret_val -ne 0 || $TPD_ERROR_CODE == "TE_INVALID" ]]; then
                #(set -x; tcli -e "mvar set -v 1 -n devtype_resetall")
                drive_spindown_spinup  $pd_id $pd_cage_pos $pd_node_wwn
                sleep 60
            fi
        fi

        ((retry++))

        if [[ $upgradepd_exit_value -eq 0 || $retry -ge $max_retry ]]; then
            break
        fi
    done

    if [ $upgradepd_exit_value -ne 0 ]; then
        echo -e "ERROR: PD $pd_id upgrade failed at $(date)\n"
        return 1
    fi

    for i in {1..90}; do # Make sure drive is in normal state
        echo "$(date "+%Y-%m-%d %T") - Waiting for PD $pd_id in normal/degraded state (count=$i)"
        local pd_state=$(showpd -nohdtot $pd_id | awk '((($5 == "normal") || ($5 == "degraded")) && ($8 != "-----") && ($9 != "-----"))' | grep -v "?")
        if [ -n "$pd_state" ]; then
            showpd -nohdtot -i $pd_id
            return 0
        fi
        sleep 10
    done

    (set -x; showpd -nohdtot $pd_id) 2>&1
    (set -x; showpd -nohdtot -s $pd_id) 2>&1
    return 1
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

# check_drive_normal(): Checks for drive is in normal-normal or degraded-old_firmware
# If max_retry is >=90 failure cases script can exit
# If max_retry is <90 failure cases function returns 1
# If drive is in normal-normal or degraded-old_firmware then function returns 0
check_drive_normal()
{
    local max_retry=$1
    local pd_id=$2
    local pd_cage_pos=$3
    local pd_node_wwn=$4
    local retval=1

    local cage=$(echo $pd_cage_pos | awk -F ":" '{ print $1 }')
    local mag=$(echo $pd_cage_pos | awk -F ":" '{ print $2 }')
    local disk=$(echo $pd_cage_pos | awk -F ":" '{ print $3 }')

    # Check drive is in normal-normal or degraded-old_firmware state
    for i in $(seq 1 $max_retry); do # Make sure drive is in normal or 'degraded and old_firmware' state
        echo "$(date "+%Y-%m-%d %T") - Waiting for PD $pd_id in normal-normal or degraded-old_firmware state (count=$i)"
        local showpd_data=$(showpd -nohdtot -s $pd_id)

        local pd_state=$(echo "$showpd_data" | awk '(($4 == "normal") && ($5 == "normal") || ($4 == "degraded") && ($5 == "old_firmware"))' | grep -v "?")
        if [ -n "$pd_state" ]; then

            for j in {1..5}; do # Make sure drive type is also set
              echo "$showpd_data" | grep -qw -e FC -e SSD -e NL
              if [ $? -eq 0 ]; then
                  break
              fi
              sleep 3 # Adding additional sleep time before returning from here
              showpd_data=$(showpd -nohdtot -s $pd_id)
            done

            echo "$showpd_data"
            return 0
        fi

        echo "$showpd_data" | egrep "normal .*servicing|degraded .*servicing"
        if [ $? -eq 0 ]; then
            echo "- PD $pd_id found in 'servicing' state"
            (set -x; servicemag unmark -f $cage $mag) 2>&1
            (set -x; servicemag clearstatus -f $cage $mag) 2>&1
        fi

        if (( i >= 5 && i % 5 == 0 )); then
            echo "- PD $pd_id current status: $showpd_data"
            if ( echo "$showpd_data" | grep -q missing ); then
                #(set -x; controlmag offloop -f -disk $disk cage$cage $mag) 2>&1 # offloop for recovery
                (set -x; controlmag onloop -f -disk $disk cage$cage $mag) 2>&1 # onloop both ports for recovery
            fi

            (set -x; controlpd clearerr ${pd_node_wwn}) 2>&1 # Send drive clearerr for recovery
        fi
        sleep 10
    done

    if [ $max_retry -ge 90 ]; then
        (set -x; showpd -nohdtot $pd_id) 2>&1
        (set -x; showpd -nohdtot -s $pd_id) 2>&1
        echo "ERROR: Exhausted retries for PD $pd_id. Consult Support."
        exit 1
    else
        return 1
    fi
}

# Upgrade each DOPE drive, if FW version is $FW_REV
upgrade_dope_drive_fw()
{
    local opt=$1
    local retval=0

    check_recycle_stall "all"
    retval=$?

    if [[ $retval -ne 0 && "$opt" == "--install" ]]; then
        return $retval
    fi

    echo -e "- Getting drive list for $MFR manufacturer drive models below with ${FW_REV//|/,} firmware:\n$(echo "$DRIVE_MODEL_LIST" | sed -e 's/|/\n/g')"

    local drives_list=$(
        showpd -nohdtot -showcols Id,State,CagePos,FW_Rev,MFR,Model,Node_WWN,Detailed_State | grep old_firmware |
        grep -w "$MFR" | egrep -w "$DRIVE_MODEL_LIST" | grep -vw -e "failed" | egrep -w "$FW_REV" | awk '$1 != "---"'
    )

    if [ -z "$drives_list" ]; then
        echo -e "\n- PD firmware upgrades not required on any of $MFR Manufacturer's drive(s) for above models."
    fi

    if [[ -n "$drives_list" && "$opt" == "--install" ]]; then

        check_showpdch_non_normal "all"

        echo -e "\nNote: A newer firmware version must be available on the system in order for the drive(s) to be upgraded."
        local drives_cnt=$(echo "$drives_list" | wc -l)

        echo -e "\n$drives_list"

        echo -e "\n===== Note: To disable SCSI UNMAP, sysmgr will be restarted once in the beginning then in the end. ====="

        GetConfirmation " $drives_cnt drive(s) were found with lower firmware version. Would you like to upgrade them?"
        if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
            exit
        fi

        disable_ssd_unmap

        PD_DEVTYPE_OFFSETS=""

        IFS=$'\n' drives_list=($(echo "$drives_list"))
        local current_cnt=0
        local drive_upgraded_cnt=0
        local showfirmwaredb_data=$(showfirmwaredb -nohdtot)
        local start_time=$(date "+%s")

        while [ $current_cnt -lt $drives_cnt ]; do
            pd_id=$(echo "${drives_list[current_cnt]}" | awk '{ print $1 }')
            pd_state=$(echo "${drives_list[current_cnt]}" | awk '{ print $2 }')
            pd_cage_pos=$(echo "${drives_list[current_cnt]}" | awk '{ print $3 }')
            pd_fw_rev=$(echo "${drives_list[current_cnt]}" | awk '{ print $4 }')
            pd_mfr=$(echo "${drives_list[current_cnt]}" | awk '{ print $5 }')
            pd_model=$(echo "${drives_list[current_cnt]}" | awk '{ print $6 }')
            pd_node_wwn=$(echo "${drives_list[current_cnt]}" | awk '{ print $7 }')

            ((current_cnt++))
            ALPHCNT=0
            echo -e "\n$(date "+%Y-%m-%d %T") ($current_cnt) Upgrading PD $pd_id"
            echo "$showfirmwaredb_data" | grep -qw $pd_model
            if [ $? -ne 0 ]; then
                echo -e "\nERROR: Drive model $pd_model is not found in current firmware database. Skipping in upgrading PD $pd_id."
                continue
            fi

            check_showpdch_non_normal $pd_id

            upgrade_pd $pd_id $pd_cage_pos $pd_node_wwn
            if [ $? -ne 0 ]; then
                echo -e "\nERROR: upgradepd -f $pd_id failed. Consult support."
                return 1
            fi

            check_showpdch_non_normal $pd_id

            check_drive_normal 90 $pd_id $pd_cage_pos $pd_node_wwn

            check_recycle_stall $pd_id
            retval=$?
            if [ $retval -ne 0 ]; then
                return $retval
            fi

            [ "$(showpd -nohdtot -showcols FW_Rev)" != $pd_fw_rev ] && ((drive_upgraded_cnt++))

            if [ $current_cnt -lt $drives_cnt ] ;then
                if [ -f $PROMPT_FILE ]; then
                    GetConfirmation "- upgradepd completed for $current_cnt out of $drives_cnt drives. Would you like to proceed to next drive?"
                    if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
                        echo -e "\n*** User requested to quit from the script - exiting now. ***\n"
                        break
                    fi
                else
                    echo -e "\n\n############################################################"
                    echo -e -n "# - upgradepd completed for $current_cnt out of $drives_cnt drives."
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

        local delta_time=$(($(date "+%s") - start_time))
        echo -e "\n$(date "+%Y-%m-%d %T") Finished in upgrading $drive_upgraded_cnt out of $drives_cnt $MFR drive(s) firmware." \
            "Total time taken is $delta_time seconds."
    fi

    drives_list=$(showpd -nohdtot -showcols Id,State,FW_Rev,MFR,Model,Detailed_State | grep -w "$MFR" | egrep -w "$DRIVE_MODEL_LIST")

    if [ -n "$drives_list" ]; then
        echo -e "\n- Verifying drive firmware:"
        echo -e "\nFW_Rev Count Model_Number     Detailed_State"
        echo "$drives_list" | awk '{ print $3, $5, $6 }' | sort | uniq -c | awk '{ printf "%-6s %5s %-16s %s\n", $2, $1, $3, $4}'
    fi

    drive_unknown_type_cnt=$(echo "$drives_list" | grep -iw "unknown" | wc -l)
    if [ $drive_unknown_type_cnt -ne 0 ]; then
        echo -e "\nWARNING: $drive_unknown_type_cnt drive(s) reported unknown. Consult Support."
        retval=1
    fi

    if [ $retval -ne 0 ]; then
        return 1
    fi
}

# check whether given DOPE drive has VPC mismatch pattern in drive event logs
# Return values: 0: If no VPC pattern found. 1: If VPC pattern found.
is_it_vpc_mismatch_dope_pd()
{
    local pd_id=$1
    local pd_wwn=$2
    local pd_serial=$3
    local pd_fw=$4

    # vpc_pattern is custom if DOPE drive FW is 3P01 for rest it is common
    local vpc_pattern="ab 02 10 00 00 25 20 .1 .. .. .. .. .. 0b 00 00 00"

    local tcli_cmd="tcli -e \"set pdcdb -w $pd_wwn -cdb 0x3C 0x1C 0x00 0x00 0x00 0x00 0x00 0x02 0x00 0x00 -inlen 130560\""
    local data=$(eval "$tcli_cmd" | grep -v "bytes data received")
    local retval=$?

    echo $data | grep -q Failed
    if [[ $? -eq 0 || $retval -ne 0 ]]; then
        echo -e "\nError while running tcli coomand below for PD $pd_id, WWN $pd_node_wwn\n"
        echo "$tcli_cmd"
        echo "$data"
        exit 1
    fi
    # Keeping hex dump and discarding ASCII data then joining all lines and tagging 0x for each hex value
    data=$(echo "$data" | cut -c 1-47 | tr '\n' ' ' | sed -e "s/^/0x/g" -e "s/ / 0x/g")

    local event_log=$(
        echo "$data" | awk --non-decimal-data -v pd_wwn=$pd_wwn '{
            printf "T10 Vendor Identification..........: "
            for (i=1; i<=8; i++) {
                printf "%c", $i
            }
            printf "\n"

            len = $31 * 256 + $32
            printf "Directory Length...................: %d\n", len
            sub_page_cnt = len / 8
            printf "total logs.........................: %d\n", sub_page_cnt

            for (p=0; p<sub_page_cnt; p++) {
                buf_id=$(33 + p * 8)

                k=0
                max_len=0
                for (ml = 40 + p * 8; ml >= 36 + p * 8; ml--) {
                    max_len += $(ml) * 256 ** k
                    k++
                }

                if (buf_id != 0x10 || max_len == 0) continue
                printf "Buffer Id..........................: %#x\n", buf_id
                printf "Max Length.........................: %#x\n", max_len

                tran_size = 0x20000
                offset = 0
                while (offset < max_len) {
                    if (tran_size > (max_len - offset)) {
                        tran_size = (max_len - offset)
                    }
                    t0 = and(tran_size, 0xff)
                    t1 = and(rshift(tran_size, 8), 0xff)
                    t2 = and(rshift(tran_size, 16), 0xff)

                    b0 = and(offset, 0xff)
                    b1 = and(rshift(offset, 8), 0xff)
                    b2 = and(rshift(offset, 16), 0xff)
                    printf "tcli -e \"set pdcdb -w %s -cdb 0x3C 0x1C %s 0x%02X 0x%02X 0x%02X 0x%02X 0x%02X 0x%02X 0x00 -inlen %d\"\n",
                        pd_wwn, buf_id, b2, b1, b0, t2, t1, t0, tran_size

                    offset += tran_size
                }
            }
        }'
    )

    # Buffer Id should be 0x10
    echo "$event_log" | grep -q "Buffer Id.* 0x10$"
    if [ $? -ne 0 ]; then
        echo "$event_log"
        echo -e "\nError: Buffer Id = 0x10 not found. Retry again or Consult Support."
        exit 1
    fi

    # Event log Max Length on each DOPE drive FW basis 3P01,3P04:0x80000; 3P07,3P08: 0x80008
    if [[ "$pd_fw" == "3P01" || "$pd_fw" == "3P04" ]]; then
        local max_length=0x80000
    else
        local max_length=0x80008
    fi

    echo "$event_log" | grep -q "Max Length.* ${max_length}$"
    if [ $? -ne 0 ]; then
        echo "$event_log"
        echo -e "\nError: 'Max Length = ${max_length}' not found. Retry again or Consult Support."
        exit 1
    fi

    local tcli_cmd=$(echo "$event_log" | grep tcli)
    if [ -z "$tcli_cmd" ]; then
        echo -e "\nWarning no tcli command to fetch data for PD $pd_id, WWN $pd_node_wwn\n"
        echo "$event_log"
        return 1
    fi

    # Keeping hex dump and discarding ASCII data then joining all lines for pattern search
    eval "$tcli_cmd" | grep -v "bytes data received:"  | cut -c 1-47 | tr '\n' ' ' > $EVENT_LOG
    grep -q Failed $EVENT_LOG
    if [ $? -eq 0 ]; then
        echo -e "\nWarning tcli commands below failed for PD $pd_id, WWN $pd_node_wwn\n"
        echo "$tcli_cmd"
        rm -f $EVENT_LOG
        exit 1
    fi

    match_dope_drive_header_serialnum $pd_id $pd_node_wwn $pd_serial $pd_fw

    # If DOPE FW is 3P01 then it is custom pattern, for rest it is common pattern
    if [ "$pd_fw" == "3P01" ]; then
        grep -q -e "ab 48 46 02 24 00 .. 01 0b" -e "ab 4c 46 02 24 02 .. .. .. .. .. 01 0b" $EVENT_LOG
        (( retval = $? == 0 ))
    else
        # For rest of the drive FW versions it is common pattern
        grep -q "$vpc_pattern" $EVENT_LOG
        (( retval = $? == 0 ))
    fi

    rm -f $EVENT_LOG
    return $retval
}

# Event logs should start with 'EVNT' then cross match log based drive serial with physical drive
match_dope_drive_header_serialnum()
{
    local pd_id=$1
    local pd_wwn=$2
    local pd_serial=$3
    local pd_fw=$4

    local serial_begin=517
    local serial_end=539
    local eventlog_header_pattern="45 56 4e 54"
    local hdr_len=11 # Length "EVNT" pattern

    # Header or Serial# checking is NA if DOPE drive FW is 3P01 or 3P04 for rest needs checking
    if [[ "$pd_fw" == "3P01" || "$pd_fw" == "3P04" ]]; then
        return
    fi

    # Match received and required header
    local header=$(head -c $hdr_len $EVENT_LOG)
    if [ "$header" != "$eventlog_header_pattern" ]; then
        echo "In event logs Header Required: '$eventlog_header_pattern', Header Received: '$header'"
        echo -e "\nError: Unable parse PD $pd_id, WWN $pd_node_wwn event logs due to event log header mismatch. Retry again or Consult Support."
        exit 1
    fi

    # Match drive Serial#
    local serial=$(dd if=$EVENT_LOG bs=1 skip=$((serial_begin-1)) count=$((serial_end-serial_begin+1)) status=noxfer 2>/dev/null |
         sed -e "s/^/0x/g" -e "s/ / 0x/g" | awk --non-decimal-data '{
        for (i=1; i<=NF; i++) {
            printf "%c", $i
        }
    } END {
        printf "\n"
    }')

    if [ -z "$serial" ]; then
        echo -e "\nError: Unable fetch PD $pd_id, WWN $pd_node_wwn serial number from event logs. Retry again or Consult Support."
        exit 1
    fi

    if [ "$serial" != "$pd_serial" ]; then
        echo "In event logs serial number Received: $serial, serial number Required: $pd_serial"
        echo -e "\nError: PD $pd_id, WWN $pd_node_wwn serial number mismatch is noticed in event logs. Retry again or Consult Support."
        exit 1
    fi
}

# check recycle stall for given drive or all $DRIVE_MODEL_LIST model drives
check_recycle_stall()
{
    local pd_id_arg=$1
    local retval=0

    if [ "$pd_id_arg" == "all" ]; then
        echo "$(date "+%Y-%m-%d %T") Verifying VPC for all drives with ${VPC_CK_FW_REV//|/,} firmware. It can take several minutes."
        pd_id_arg=""
    else
        echo "$(date "+%Y-%m-%d %T") Verifying VPC for PD $pd_id_arg."
    fi

    local drive_list=$(
        showpd -nohdtot -showcols Id,State,CagePos,FW_Rev,MFR,Model,Node_WWN,Serial $pd_id_arg |
        grep -w "$MFR" | egrep -w "$DRIVE_MODEL_LIST" | grep -vw "failed" |  egrep -w "$VPC_CK_FW_REV" | awk '$1 != "---"'
    )

    if [ -z "$drive_list" ]; then
        return
    fi

    local drive_count=$(echo "$drive_list" | wc -l)
    IFS=$'\n' drive_list=($(echo "$drive_list"))
    local current_cnt=0

    local pd_list=""
    local vpc_passed=0
    local vpc_failed=0
    while [ $current_cnt -lt $drive_count ]; do
        pd_id=$(echo "${drive_list[current_cnt]}" | awk '{ print $1 }')
        pd_fw_rev=$(echo "${drive_list[current_cnt]}" | awk '{ print $4 }')
        pd_model=$(echo "${drive_list[current_cnt]}" | awk '{ print $6 }')
        pd_node_wwn=$(echo "${drive_list[current_cnt]}" | awk '{ print $7 }')
        pd_serial=$(echo "${drive_list[current_cnt]}" | awk '{ print $8 }')
        ((current_cnt++))

        if [ "$pd_id_arg" == "" ]; then
            # While logging $vpc_status it logs new line
            printf "\tVerifying VPC for pd %5d, FW $pd_fw_rev, Model $pd_model (Drive $current_cnt out of $drive_count): " $pd_id
        fi

        is_it_vpc_mismatch_dope_pd $pd_id $pd_node_wwn $pd_serial $pd_fw_rev
        retval=$?
        if [ $retval -ne 0 ]; then
            retval=1
            pd_list=${pd_list:+$pd_list","}
            pd_list="${pd_list}$pd_id"
            ((vpc_failed++))
            local vpc_status="Failed"
        else
            ((vpc_passed++))
            local vpc_status="Passed"
        fi

        if [ "$pd_id_arg" == "" ]; then
            echo "$vpc_status"
        fi
    done

    if [ "$pd_id_arg" == "" ]; then
        echo -e "\n$(date "+%Y-%m-%d %T") VPC verification complete for $current_cnt out of $drive_count drives. Passed: $vpc_passed, Failed: $vpc_failed."
    fi

    if [ -n "$pd_list" ]; then
        echo -e "\nError: PD $pd_list reported with VPC mismatch. Consult Support.\n"
        retval=1
    else
        pd_id_arg=${pd_id_arg:="all"}
        echo -e "- VPC verification Passed for PD $pd_id_arg.\n"
        retval=0
    fi

    return $retval
}

check_lock_file()
{
    # Lock check should be prior to trap call
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

get_lock_file()
{
    check_lock_file
    eval $(clwait --bash)
    echo "Pid=$$, Script=$0, Node$mynode StartDate=\"$(date "+%x %T")\"" > $LOCK_FILE
}

if [ $# -eq 0 ]; then
    usage
fi

option=$1

is_sysmgr_up

isallnodesintegrated

case $option in
    "--install")
        check_tpd_version "$TPD_VERSIONS" root
        ;;

    "--verify")
        ;;

    *)
        usage
        ;;
esac

check_lock_file
(
    trap cleanup EXIT SIGINT SIGQUIT SIGILL SIGTRAP SIGABRT SIGBUS SIGFPE SIGKILL SIGSEGV SIGTERM # handle signals
    get_lock_file
    get_script_version ${0##*/} "$@"
    upgrade_dope_drive_fw $option
    retval=$?
    echo -e "$SCRIPT exit value = $retval" > $TMP_FILE
    enable_ssd_unmap
) | tee -a $LOGFILE

echo -e "\nLog is at $LOGFILE"

if [ $option == "--verify" ]; then
    echo -e "\nNote:"
    echo "- If $PROMPT_FILE file is present, script waits until user responds before proceeding to next drive."
    echo "- Otherwise it waits for 10 seconds for user response before proceeding automatically."
fi

retval=$(grep "^$SCRIPT exit value = " $TMP_FILE 2>/dev/null | tail -n 1 | awk '{ print $NF }')
rm -f $TMP_FILE $LOCK_FILE
exit $retval
