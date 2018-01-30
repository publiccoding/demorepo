#!/bin/bash
# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
#
# upgrade_cobra_drive_fw.sh: Avoids issue when upgrading Cobra-F drives from firmware version $FW_REV to a higher version.
# Bug(s) Addressed: 161769, 171330
#
# Note:
# - In EKM encryption is enabled system it runs, 'controlencryption checkekm' to validate "EKM settings are correct". If not, script exits.
# - If /tmp/upgrade_cobra_drive_fw.prompt file is present, script waits until user responds before proceeding to next drive.
# - Otherwise it waits for 10 seconds for user response before proceeding automatically.
#
# High level summary on how script works:
#  1) Check any drive chunklet(s) in logging state?
#     If then check every 10 seconds until condition is cleared.
#     - User can abort the script by using <cttl>c.
#  2) Get list of HGST Cobra/King Cobra drive with 3P00 firmware loaded.
#  3) Disable Head of Queue flag
#     tcli -e 'kvar set -n scsi_init_task_attr_hp_sas -v 0'
#
#  4) Select physical drive from the list.
#  5) Check selected drive model listed in showfirmwaredb output? If not, skip it.
#  6) Check selected drive chunklet(s) in logging state?
#     If then check every 10 seconds until condition is cleared.
#     - User can abort the script by using <cttl>c.
#  7) upgradepd <pd>
#  8) Wait for drive to be in normal state. If not, retry every 10 seconds for 90 times before failing the script.
#
#  9) If power-off-on-drive option is selected then perform step 10 to step 16.
# 10) Stop unit before Power-off the drive
# 11) Power-off the drive by using command below:
#    cli cgcmd -tc tty -C cage${cage} -p a|b -c "drivebay bay=${mag} set power=off" - For Chimera
#    cli cgcmd -tc tty -C cage${cage} -p a|b -c "controlmag offloop mag${mag} disk $disk" - For V-Class
#    cli cgcmd -tc tty -C cage${cage} -p a|b -c 'poweroffdrive ${mag}' - For EOS
# 12) Wait for both paths of the drive in offline state. If not, retry every 10 seconds for 90 times before failing the script.
# 13 Power-on the drive
#     cli cgcmd -tc tty -C cage${cage} -p a|b -c "drivebay bay=${mag} set power=on" - For Chimera
#     cli cgcmd -tc tty -C cage${cage} -p a|b -c "controlmag onloop mag${mag} disk $disk" - For V-Class
#     cli cgcmd -tc tty -C cage${cage} -p a|b -c poweroffdrive $mag - For EOS
# 14) Wait for both paths of the drive in online state. If not, retry every 10 seconds for 90 times before failing the script.
# 15) Start unit after Power-on the drive
# 16) Wait for drive to be in normal state. If not, retry every 10 seconds for 90 times before failing the script.
#     - Once drive is in normal state wait upto additional 15 seconds before returning from here.
#
# 17) Check selected drive chunklet(s) in logging state?
#     If then check every 10 seconds until condition is cleared.
#     - User can abort the script by using <cttl>c.
# 18) User will be prompted to quit from the script. If no input comes from user within 10 seconds then it automatically proceeds to next drive.
#
# 19) Enable Head of Queue flag.
#     tcli -e 'kvar set -n scsi_init_task_attr_hp_sas -v 0'
# 20) Log how many drives successfully upgraded and how long it took to complete it.
# 21) Log drive firmware summary.
# 22) Log location of the log file.

Version=2.04

TPD_VERSIONS="3.2.1.MU[35]|3.2.2.MU[2-4]"

# Cobra-F drive model
COBRA_F_NON_FIP="HCBF0600S5xeN010|HCBF0900S5xeN010|HCBF1200S5xeN010|HCBF1800S5xeN010|HKCF0300S5xeN015"
COBRA_F_FIP="HCBF1200S5xeF010"
KING_COBRA_F_NON_FIP="HKCF0600S5xeN015"
KING_COBRA_F_FIP="HKCF0600S5xeF015"

DRIVE_MODEL_LIST="$COBRA_F_NON_FIP|$COBRA_F_FIP|$KING_COBRA_F_NON_FIP|$KING_COBRA_F_FIP"

SCRIPT=upgrade_cobra_drive_fw.sh
PROMPT_FILE="/tmp/upgrade_cobra_drive_fw.prompt"
LOGFILE="/var/log/tpd/${SCRIPT}.log"
ALPHABET=({a..z} {A..Z})

TMP_FILE=/tmp/$SCRIPT.$$

# Firmware version
FW_REV="3P00"

# Manufacturer
MFR="HGST"

cleanup()
{
    echo -e "\n- While exiting: Enabling head of Queue flag..."
    tcli -e 'kvar set -n scsi_init_task_attr_hp_sas -v 1' > /dev/null
    rm -f $TMP_FILE
    trap "" EXIT
    exit
}

usage()
{
    local prog=$(basename $0)

    echo -e "Usage: $prog --install [power-off-on-drive]"
    echo -e "       $prog --verify\n"

    echo -e "--install [OPTIONS] : Upgrade Cobra drive(s) from $FW_REV firmware version"
    echo -e "--verify            : Verify the number of Cobra drive(s) by firmware version.\n"

    echo -e "power-off-on-drive  : Once drive firmware is upgraded then power off/on the drive."

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

ks_encryption_checkekm()
{
    local controlencryption_status=$(controlencryption -nohdtot status)
    local status=$(echo "$controlencryption_status" | awk '($2 == "yes")')

    if [ -z "$status" ]; then
        return 0 # Non-Encryption system
    fi

    local KeyStore=$(echo $controlencryption_status | awk '{ print $6 }')

    if [ "$KeyStore" != "EKM" ]; then
        return 0 # Local Encryption system
    fi

    local status=$(controlencryption checkekm 2>&1)

    echo -e "\n$status"

    echo "$status" | grep -q "EKM settings are correct"
    if [ $? -ne 0 ]; then
        echo -e "\n${FUNCNAME[1]}: 'controlencryption checkekm' failed. Consult Support"
        return  1 # EKM failure is noticed
    fi

    echo -e "${FUNCNAME[1]}: controlencryption checkekm: Passed.\n"

    return 0
}

check_showpdch_log()
{
    local pd_id=$1
    local pattern="No chunklet information available."

    [ $pd_id == "all" ] && pd_id=""

    local count=1
    echo -e "\n$(date "+%Y-%m-%d %X") (${ALPHABET[ALPHCNT++]}) Checking any chunklet(s) of pd $pd_id in logging state?"
    while true; do
        local showpdch_log=$(showpdch -nohdtot -log $pd_id 2>&1)

        echo "$showpdch_log" | grep -q "$pattern"

        if [ $? -eq 0 ]; then
            echo -e "- None of the pd $pd_id chunklet in logging state."
            break
        else
            echo "$(date "+%Y-%m-%d %X") - $(echo "$showpdch_log" | wc -l) chunklet(s) reported in logging state."\
            "Waiting for them to be cleared (count=$count). To abort press Ctrl-C"
            #echo "$showpdch_log"
            sleep 10
        fi
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
    elif [[ $reply == "q" || $reply == "n" ]]; then
        echo "- As per user not applying this workaround."
        GETCONFIRMATION="SKIP-IT"
        break
    else
        echo "Unrecognized input \"$reply\""
    fi
  done
}

drive_stop_unit()
{
    local pd_id=$1
    local retval=1

    echo -e "\n$(date "+%Y-%m-%d %X") (${ALPHABET[ALPHCNT++]}) Stop unit pd $pd_id"
    tcli -e "set pdcdb -i "$pd_id" -cdb 0x1b 00 00 00 00 00" > /dev/null # Send stop unit
    for i in {1..90}; do # Make sure drive is in offline state
        echo "$(date "+%Y-%m-%d %X") - Waiting for pd $pd_id Stop unit to complete (count=$i)"
        local tur_data=$(tcli -e "set pdcdb -i "$pd_id" -tur")
        echo "$tur_data" | egrep -q "TE_NOTREADY|No path to pd"
        if [ $? -eq 0 ]; then
            echo -e "$(date "+%Y-%m-%d %X") - Stop unit pd $pd_id Successful.\n"
            retval=0
            break
        fi
        tcli -e "set pdcdb -i "$pd_id" -cdb 0x1b 00 00 00 00 00" > /dev/null # Send stop unit
        sleep 10
    done

    if [ $retval -ne 0 ]; then
        echo -e "\n$(date "+%Y-%m-%d %X") - Stop unit pd $pd_id Failed."
        echo "$tur_data"
        tcli -e "set pdcdb -i "$pd_id" -cdb 0x1b 00 00 00 01 00" >/dev/null # Before exiting send Start unit
    fi

    return $retval
}

drive_start_unit()
{
    local pd_id=$1
    local retval=1

    echo -e "\n$(date "+%Y-%m-%d %X") (${ALPHABET[ALPHCNT++]}) Start unit pd $pd_id"
    for i in {1..90}; do # Make sure drive is in offline state
        tcli -e "set pdcdb -i "$pd_id" -cdb 0x1b 00 00 00 01 00" > /dev/null # Send start unit
        echo "$(date "+%Y-%m-%d %X") - Waiting for pd $pd_id Start unit to complete (count=$i)"
        local tur_data=$(tcli -e "set pdcdb -i "$pd_id" -tur")
        if [ -z "$tur_data" ]; then
            echo -e "$(date "+%Y-%m-%d %X") - Start unit pd $pd_id Successful.\n"
            retval=0
            break
        fi
        sleep 10
    done

    if [ $retval -ne 0 ]; then
        echo -e "\n$(date "+%Y-%m-%d %X") - Start unit pd $pd_id Failed."
        echo "$tur_data"
    fi

    return $retval
}

get_gl_dsks_offsets()
{
  gdb -q -n /opt/tpd/bin/sysmgr <<\EOF 2>/dev/null | sed -e "s/^(gdb) //g"
    printf "sys_gltab=%#x\n", (long)&sys_gltab
    printf "gl_dsks=%#x\n", (long)&((struct gltab *) 0)->gl_dsks
    printf "disk_t=%#x\n", sizeof(disk_t)
    printf "d_devtype=%#x\n", (long)&((disk_t *) 0)->d_devtype
    printf "dmr_mvar_devtype_reset=%d\n", dmr_mvar_devtype_reset
    printf "devtype_unknown=%d\n", devtype_unknown
    q
EOF
}

sync_pd_devtype()
{
    local pd_id=$1

    if [ -z "$PD_DEVTYPE_OFFSETS" ]; then
        PD_DEVTYPE_OFFSETS=$(get_gl_dsks_offsets)

        # Get the offset of gl_fcloops
        sys_gltab=$(echo "$PD_DEVTYPE_OFFSETS" | grep "sys_gltab=" | awk -F "=" '{ print $NF }')
        gl_dsks=$(echo "$PD_DEVTYPE_OFFSETS" | grep "gl_dsks=" | awk -F "=" '{ print $NF }')
        disk_t_size=$(echo "$PD_DEVTYPE_OFFSETS" | grep "disk_t=" | awk -F "=" '{ print $NF }')
        d_devtype=$(echo "$PD_DEVTYPE_OFFSETS" | grep "d_devtype=" | awk -F "=" '{ print $NF }')
        devtype_unknown=$(echo "$PD_DEVTYPE_OFFSETS" | grep "devtype_unknown=" | awk -F "=" '{ print $NF }')
        dmr_mvar_devtype_reset=$(echo "$PD_DEVTYPE_OFFSETS" | grep "dmr_mvar_devtype_reset=" | awk -F "=" '{ print $NF }')

        echo "- sys_gltab=$sys_gltab"
        echo "- gl_dsks=$gl_dsks"
        echo "- disk_t_size=$disk_t_size"
        echo "- d_devtype=$d_devtype"
        echo "- devtype_unknown=$devtype_unknown"
        echo "- dmr_mvar_devtype_reset=$dmr_mvar_devtype_reset"
    fi

    pd_addr=$((sys_gltab + gl_dsks + (pd_id * disk_t_size)))
    echo "- pd_addr=$pd_addr (pd $pd_id)"

    pd_devtype=$(showmemval sysmgr none u8 1 $((pd_addr+d_devtype)) | awk '{ print $2 }')
    echo "- pd_devtype=$pd_devtype"

    if [[ -n "$pd_devtype" && $pd_devtype -ne 0 ]]; then
        FALSE=0
        (set -x; cli startfunc sysmgr write disk_handle_devtype_change $pd_addr $devtype_unknown 0) 2>&1
        (set -x; cli startfunc sysmgr write dskfail_add $pd_addr 1 0 $FALSE $dmr_mvar_devtype_reset) 2>&1
    fi
}

drive_power_off()
{
    local pd_id=$1
    local cage=$2
    local mag=$3
    local disk=$4

    echo -e "\n$(date "+%Y-%m-%d %X") (${ALPHABET[ALPHCNT++]}) Power-off pd $pd_id or cage $cage magazine $mag disk $disk"

    echo "$MODEL" | egrep -qw "20...|CH400"
    if [ $? -eq 0 ]; then # Chimera
        (set -x
         cli cgcmd -tc tty -C cage${cage} -p a -c "drivebay bay=${mag} set power=off"
         cli cgcmd -tc tty -C cage${cage} -p b -c "drivebay bay=${mag} set power=off"
        ) 2>&1
    else
        echo "$MODEL" | grep -qw "V[48]00"
        if [ $? -eq 0 ]; then # V-Class
            (set -x
             cli cgcmd -tc tty -C cage${cage} -p a -c "controlmag offloop mag${mag} disk $disk"
             cli cgcmd -tc tty -C cage${cage} -p b -c "controlmag offloop mag${mag} disk $disk"
            ) 2>&1
        else # EOS
            (set -x
             cli cgcmd -tc tty -C cage${cage} -p a -c poweroffdrive $mag
             cli cgcmd -tc tty -C cage${cage} -p b -c poweroffdrive $mag
            ) 2>&1
            #tcli -e "jt tty -n cage${cage} -p a -c 'poweroffdrive ${mag}'"
            #tcli -e "jt tty -n cage${cage} -p b -c 'poweroffdrive ${mag}'"
        fi
    fi | grep -v "Disk Already .*loop"

    #echo "$(date "+%Y-%m-%d %X") - Updating sysmgr with latest status of pd $pd_id"
    #sync_pd_devtype $pd_id

    local retval=1
    for i in {1..90}; do # Make sure drive is in offline state
        echo "$(date "+%Y-%m-%d %X") - Waiting for pd $pd_id in offline state (count=$i)"
        local pd_state=$(showpd -nohdtot $pd_id | awk '(($5 != "normal") && ($8 == "-----") && ($9 == "-----"))')
        if [ -n "$pd_state" ]; then
            (set -x; showpd -nohdtot $pd_id) 2>&1
            retval=0
            break
        fi
        sleep 10
    done

    return $retval
}

drive_power_on()
{
    local pd_id=$1
    local cage=$2
    local mag=$3
    local disk=$4

    echo -e "\n$(date "+%Y-%m-%d %X") (${ALPHABET[ALPHCNT++]}) Power-on pd $pd_id or cage $cage magazine $mag disk $disk"
    echo "$MODEL" | egrep -qw "20...|CH400"
    if [ $? -eq 0 ]; then # Chimera
        (set -x
         cli cgcmd -tc tty -C cage${cage} -p a -c "drivebay bay=${mag} set power=on"
         cli cgcmd -tc tty -C cage${cage} -p b -c "drivebay bay=${mag} set power=on"
        ) 2>&1
    else
        echo "$MODEL" | grep -qw "V[48]00"
        if [ $? -eq 0 ]; then # V-Class
            (set -x
             cli cgcmd -tc tty -C cage${cage} -p a -c "controlmag onloop mag${mag} disk $disk"
             cli cgcmd -tc tty -C cage${cage} -p b -c "controlmag onloop mag${mag} disk $disk"
            ) 2>&1
        else # EOS
            (set -x
             cli cgcmd -tc tty -C cage${cage} -p a -c powerondrive $mag
             cli cgcmd -tc tty -C cage${cage} -p b -c powerondrive $mag
            ) 2>&1
            #tcli -e "jt tty -n cage${cage} -p a -c 'powerondrive ${mag}'"
            #tcli -e "jt tty -n cage${cage} -p b -c 'powerondrive ${mag}'"
        fi
    fi | grep -v "Disk Already .*loop"

    #echo "$(date "+%Y-%m-%d %X") - Updating sysmgr with latest status of pd $pd_id"
    #sync_pd_devtype $pd_id

    local retval=1
    for i in {1..90}; do # Make sure drive is in online state
        echo "$(date "+%Y-%m-%d %X") - Waiting for pd $pd_id path in online state (count=$i)"
        local pd_state=$(showpd -nohdtot $pd_id | awk '(($8 != "-----") && ($9 != "-----"))')
        if [ -n "$pd_state" ]; then
            (set -x; showpd -nohdtot $pd_id) 2>&1
            retval=0
            break
        fi
        sleep 10
    done

    return $retval
}

drive_stopunit_poweroff_poweron_startunit()
{
    local pd_id=$1
    local pd_cage_pos=$2

    local cage=$(echo $pd_cage_pos | awk -F ":" '{ print $1 }')
    local mag=$(echo $pd_cage_pos | awk -F ":" '{ print $2 }')
    local disk=$(echo $pd_cage_pos | awk -F ":" '{ print $3 }')

    drive_stop_unit $pd_id
    retval=$?
    if [ $retval -ne 0 ]; then
        (set -x; showpd -nohdtot $pd_id) 2>&1
        (set -x; showpd -nohdtot -s $pd_id) 2>&1
        return $retval
    fi

    drive_power_off $pd_id $cage $mag $disk
    retval=$?
    if [ $retval -ne 0 ]; then
        (set -x; showpd -nohdtot $pd_id) 2>&1
        (set -x; showpd -nohdtot -s $pd_id) 2>&1
        return $retval
    fi

    sleep 2

    drive_power_on $pd_id $cage $mag $disk
    retval=$?
    if [ $retval -ne 0 ]; then
        (set -x; showpd -nohdtot $pd_id) 2>&1
        (set -x; showpd -nohdtot -s $pd_id) 2>&1
        return $retval
    fi

    drive_start_unit $pd_id
    retval=$?
    if [ $retval -ne 0 ]; then
        (set -x; showpd -nohdtot $pd_id) 2>&1
        (set -x; showpd -nohdtot -s $pd_id) 2>&1
        return $retval
    fi

    #echo "$(date "+%Y-%m-%d %X") - Updating sysmgr with latest status of pd $pd_id"
    #sync_pd_devtype $pd_id

    # Before returning make sure drive is in normal-normal or degraded-old_firmware state
    for i in {1..90}; do # Make sure drive is in normal or 'degraded and old_firmware' state
        echo "$(date "+%Y-%m-%d %X") - Waiting for pd $pd_id in normal or degraded and old_firmware state (count=$i)"
        showpd_data=$(showpd -nohdtot -s $pd_id)

        pd_state=$(echo "$showpd_data" | \
        awk '(($4 == "normal") && ($5 == "normal") || ($4 == "degraded") && ($5 == "old_firmware"))' | grep -v "?")
        if [ -n "$pd_state" ]; then

            for j in {1..5}; do # Make sure drive type is also set
              echo "$showpd_data" | egrep -qw "FC|SSD|NL"
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
            echo "- pd $pd_id found in 'servicing' state"
            (set -x; servicemag unmark -f $cage $mag) 2>&1
            (set -x; servicemag clearstatus -f $cage $mag) 2>&1
        fi

        if [[ $i -ge 5 && $((i % 5)) -eq 0 ]]; then
            echo "- pd $pd_id current status: $showpd_data"
        fi
        sleep 10
    done

    (set -x; showpd -nohdtot $pd_id) 2>&1
    (set -x; showpd -nohdtot -s $pd_id) 2>&1
    return 1
}

upgrade_pd()
{
    local pd_id=$1

    echo -e "\n$(date "+%Y-%m-%d %X") (${ALPHABET[ALPHCNT++]}) Running upgradepd -f $pd_id"
    upgradepd -f $pd_id

    if [ $? -ne 0 ]; then
        echo "ERROR: pd $pd_id upgrade failed at $(date)"
        return 1
    fi

    for i in {1..90}; do # Make sure drive is in normal state
        echo "$(date "+%Y-%m-%d %X") - Waiting for pd $pd_id in normal state (count=$i)"
        local pd_state=$(showpd -nohdtot $pd_id | awk '(($5 == "normal") && ($8 != "-----") && ($9 != "-----"))' | grep -v "?")
        if [ -n "$pd_state" ]; then
            (set -x; showpd -nohdtot $pd_id) 2>&1
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

# Avoid issue caused by the Head of Queue flag when upgrading Cobra-F drives from
# firmware verion 3P00 to a higher version.
upgrade_cobra_drive_fw()
{
    local opt=$1

    echo -e "- Getting drive list for manufacturer $MFR for drive models below with $FW_REV firmware:\n$(echo "$DRIVE_MODEL_LIST" | sed -e 's/|/\n/g')"

    local cobra_drives_list=$(
       showpd -nohdtot -showcols Id,State,CagePos,FW_Rev,MFR,Model |
       grep -w "$MFR" | egrep -w "$DRIVE_MODEL_LIST" | grep -vw "failed" | grep -w $FW_REV
    )

    if [ -z "$cobra_drives_list" ]; then
        echo -e "\n- No drives were found for Manufacturer $MFR with ${FW_REV} firmware for above drive models."
    fi

    if [[ -n "$cobra_drives_list" && "$opt" == "--install" ]]; then

        ks_encryption_checkekm
        if [ $? -ne 0 ]; then
            exit 1
        fi

        check_showpdch_log "all"

        echo -e "\nNote: A newer firmware version must be available on the system in order for the drive(s) to be upgraded."
        local cobra_drives_cnt=$(echo "$cobra_drives_list" | wc -l)

        echo -e "\n$cobra_drives_list"

        GetConfirmation " $cobra_drives_cnt drive(s) were found with firmware version $FW_REV. Would you like to upgrade${POWER_OFF_ON_DRIVE_MSG}?"
        if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
            exit
        fi

        PD_DEVTYPE_OFFSETS=""

        IFS=$'\n' cobra_drives_list=($(echo "$cobra_drives_list"))
        local current_cnt=0
        local drive_upgraded_cnt=0
        local showfirmwaredb_data=$(showfirmwaredb -nohdtot)
        local start_time=$(date "+%s")

        if [ $HOQ_TOGGLE -eq 0 ]; then
            echo -e "\n$(date "+%Y-%m-%d %X") Disabling Head of Queue flag prior to drive firmware upgrade.\n"
            # Disable Head of Queue flag
            tcli -e 'kvar set -n scsi_init_task_attr_hp_sas -v 0' > /dev/null
        else
            echo -e "\nToggling Head of Queue flag during drive firmware upgrade.\n"
        fi

        while [ $current_cnt -lt $cobra_drives_cnt ]; do
            pd_id=$(echo "${cobra_drives_list[current_cnt]}" | awk '{ print $1 }')
            pd_state=$(echo "${cobra_drives_list[current_cnt]}" | awk '{ print $2 }')
            pd_cage_pos=$(echo "${cobra_drives_list[current_cnt]}" | awk '{ print $3 }')
            pd_fw_rev=$(echo "${cobra_drives_list[current_cnt]}" | awk '{ print $4 }')
            pd_mfr=$(echo "${cobra_drives_list[current_cnt]}" | awk '{ print $5 }')
            pd_model=$(echo "${cobra_drives_list[current_cnt]}" | awk '{ print $6 }')

            ((current_cnt++))
            ALPHCNT=0
            echo -e "\n$(date "+%Y-%m-%d %X") ($current_cnt) Upgrading pd $pd_id"
            echo "$showfirmwaredb_data" | grep -qw $pd_model
            if [ $? -ne 0 ]; then
                echo -e "\nERROR: Drive model $pd_model is not found in current firmware database. Skipping in upgrading pd $pd_id."
                continue
            fi

            check_showpdch_log $pd_id

            if [ $HOQ_TOGGLE -eq 1 ]; then
                # Disable Head of Queue flag
                tcli -e 'kvar set -n scsi_init_task_attr_hp_sas -v 0' > /dev/null
            fi

            upgrade_pd $pd_id
            if [ $? -ne 0 ]; then
                echo -e "\nERROR: upgradepd -f $pd_id failed. Consult support."
                return 1
            fi

            if [ $HOQ_TOGGLE -eq 1 ]; then
                # Enable Head of Queue flag
                tcli -e 'kvar set -n scsi_init_task_attr_hp_sas -v 1' > /dev/null
            fi

            if [ $POWER_OFF_ON_DRIVE -eq 1 ]; then
                trap "" SIGINT # Ignore signals before Power-off-on
                drive_stopunit_poweroff_poweron_startunit $pd_id $pd_cage_pos
                if [ $? -ne 0 ]; then
                    echo -e "\nERROR: Drive power off/on for $pd_id failed. Consult support."
                    exit 1
                fi
                trap - SIGINT # Restore signals
            fi

            check_showpdch_log $pd_id

            [ "$(showpd -nohdtot -showcols FW_Rev)" != $pd_fw_rev ] && ((drive_upgraded_cnt++))

            if [ $current_cnt -lt $cobra_drives_cnt ] ;then
                if [ -f $PROMPT_FILE ]; then
                    GetConfirmation "- upgradpd completed for $current_cnt out of $cobra_drives_cnt drives. Would you like to proceed to next drive?"
                    if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
                        echo -e "\n*** User requested to quit from the script - exiting now. ***\n"
                        break
                    fi
                else
                    echo -e "\n\n############################################################"
                    echo -e -n "# - upgradpd completed for $current_cnt out of $cobra_drives_cnt drives."
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

        if [ $HOQ_TOGGLE -eq 0 ]; then
            echo -e "\n$(date "+%Y-%m-%d %X") Enabling Head of Queue flag on post drive firmware upgrade."
            # Enable Head of Queue flag
            tcli -e 'kvar set -n scsi_init_task_attr_hp_sas -v 1' > /dev/null
        fi

        local delta_time=$(($(date "+%s") - start_time))
        echo -e "\n$(date "+%Y-%m-%d %X") Finished in upgrading $drive_upgraded_cnt out of $cobra_drives_cnt $MFR drive(s) firmware." \
	"Total time taken is $delta_time seconds."
    fi

    cobra_drives_list=$(showpd -nohdtot -showcols Id,State,FW_Rev,MFR,Model | grep -w "$MFR" | egrep -w "$DRIVE_MODEL_LIST")

    if [ -n "$cobra_drives_list" ]; then
        echo -e "\n- Verifying drive firmware:"
        echo -e "\n-FW Rev- -Drive Count- -Model Number-"
        echo "$cobra_drives_list" | awk '{ print $3,$5 }' | sort | uniq -c | awk '{ printf "%-8s %12s  %s\n", $2, $1, $3}'
    fi

    retval=0
    ks_encryption_checkekm
    retval=$?

    drive_unknown_type_cnt=$(echo "$cobra_drives_list" | grep -iw "unknown" | wc -l)
    if [ $drive_unknown_type_cnt -ne 0 ]; then
        echo -e "\nWARNING: $drive_unknown_type_cnt drive(s) reported unknown. Consult Support."
        retval=1
    fi

    if [ $retval -ne 0 ]; then
        return 1
    fi
}

if [[ $# -eq 0 || $# -gt 2 ]]; then
    usage
fi

option=$1

is_sysmgr_up

isallnodesintegrated

# When this is set, the Head of Queue flag will be toggled before and after
# each drive upgrade.  If not, the flag will be disabled before the upgrades,
# and reenabled after they have all been completed.
HOQ_TOGGLE=0

# Post drive upgrade Power off/on the drive. By default, drive power off/on is not ON
POWER_OFF_ON_DRIVE=0

POWER_OFF_ON_DRIVE_MSG=""
MODEL=$(showsys -d | grep "^System Model" | awk '{ print $NF }')

case $option in
    "--install")
        check_tpd_version "$TPD_VERSIONS"
        POWER_OFF_ON_DRIVE_MSG=" **'without Power off/on' each drive after upgradepd**"
        if [ $# -eq 2 ]; then
            if [ "$2" == "power-off-on-drive" ]; then
                POWER_OFF_ON_DRIVE=1
                POWER_OFF_ON_DRIVE_MSG=" 'with Power off/on' each drive after upgradepd"
            else
                echo "ERROR: Invalid option '$2' is specified."
                exit 1
            fi

            # Commenting HOQ_TOGGLE code now. If needed will put them back by enhancing further
            #if [ "$2" == "hoq-toggle" ]; then
            #    HOQ_TOGGLE=1
            #else
            #    echo "ERROR: Invalid option $2 is specified"
            #    exit 1
            #fi
        fi

        if [ $POWER_OFF_ON_DRIVE -eq 0 ]; then
            GetConfirmation "*** WARNING: 'power-off-on-drive' option is not specified. Quit from here and specify it to avoid service timeout issue. ***"
            if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
                exit
            fi
        fi

        trap cleanup 0 1 2 3 4 5 6 7 9 15       # handle signals

        ;;

    "--verify")
        ;;

    *)
        usage
        ;;
esac

(
  get_script_version $0 $*
  upgrade_cobra_drive_fw $option
  retval=$?
  echo -e "$SCRIPT exit value = $retval" > $TMP_FILE
) | tee -a $LOGFILE

echo -e "\nLog is at $LOGFILE"

if [ $option == "--verify" ]; then
    echo -e "\nNote:"
    echo "- If $PROMPT_FILE file is present, script waits until user responds before proceeding to next drive."
    echo "- Otherwise it waits for 10 seconds for user response before proceeding automatically."
fi

retval=$(grep "^$SCRIPT exit value = " $TMP_FILE 2>/dev/null | tail -n 1 | awk '{ print $NF }')
retval=${retval:=0}
rm -f $TMP_FILE
exit $retval
