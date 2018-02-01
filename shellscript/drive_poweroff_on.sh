#!/bin/bash
# (C) Copyright Hewlett Packard Enterprise Development LP
#
# drive_poweroff_on.sh: Power off/on degraded drives or specified drive list
# Bug(s) Addressed: 175841
#
# High level summary on how script works:
#  1) If user gives --verify option then script gets list of drives in degraded state then
#     it lists each drive details to user.
#  2) If user passes list of drives separated by spaces to --verify option then
#     it lists each drive details to user.
#  3) If user gives --install option then script gets list of drives in degraded state then
#     it performs Power off/on for each drive.
#  4) If user passes list of drives separated by spaces to --install option then
#     it performs Power off/on for each drive.
#
#  5) If user selects --install [drive-list] then it performs step 6 first then
#     step 7 to rest of the steps for each drive.
#  6) Check any drive chunklet(s) in logging state?
#     If then check every 10 seconds until condition is cleared.
#     - User can abort the script by using <cttl>c.
#  7) Stop unit before Power-off the drive.
#  8) Power-off the drive by using command below:
#     cli cgcmd -tc tty -C cage${cage} -p a|b -c "drivebay bay=${mag} set power=off" - For Chimera
#     cli cgcmd -tc tty -C cage${cage} -p a|b -c "controlmag offloop mag${mag} disk $disk" - For V-Class
#     tcli -e "jt tty -n cage${cage} -p a|b -c 'poweroffdrive ${mag}'" - For EOS
#  9) Wait for both paths of the drive in offline state.
#     If not, retry every 10 seconds for 90 times before failing the script.
# 10) Power-on the drive
#     cli cgcmd -tc tty -C cage${cage} -p a|b -c "drivebay bay=${mag} set power=on" - For Chimera
#     cli cgcmd -tc tty -C cage${cage} -p a|b -c "controlmag onloop mag${mag} disk $disk" - For V-Class
#     tcli -e "jt tty -n cage${cage} -p a|b -c 'powerondrive ${mag}'" - For EOS
# 11) Wait for both paths of the drive in online state.
#     If not, retry every 10 seconds for 90 times before failing the script.
# 12) Start unit after Power-on the drive.
# 13) Check selected drive chunklet(s) in logging state?
#     If then check every 10 seconds until condition is cleared.
#     - User can abort the script by using <cttl>c.
# 14) Wait for drive to be in normal state.
#     If not, retry every 10 seconds for 90 times before failing the script.
#     - Once drive is in normal state wait upto additional 10 seconds before returning from here.
# 15) User will be prompted to quit from the script. If no input comes from user within 10 seconds then
#     it automatically proceeds to next drive or goes to step 7

Version=1.03

ALPHABET=({a..z} {A..Z})

usage()
{
    local prog=$(basename $0)

    echo -e "Usage: $prog --install [drive-list]"
    echo -e "       $prog --verify\n"

    echo -e "--install              : Power off/on degraded drives only"
    echo -e "--install [drive-list] : Power off/on specified drives for degraded/normal state drives"
    echo -e "--verify  [drive-list] : Verify any drive in degraded state or get state of the specified drives\n"

    echo "drive-list: Drive pd id numbers"

    exit 1
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
        echo "Unrecognized input '$reply'"
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

get_script_version()
{
    local patches=$(showversion -b | awk '/^Patches/ && $2 != "None" { print "+"$2 }')
    local tpd=$(showversion -b)
    tpd=$(translate_tpd_release_version "$TPD")

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
        (set -x; showsysmgr -d)
        exit 1
    fi
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

drive_poweroff_on()
{
    local opt=$1
    local drive_list=""
    if [ $# -gt 1 ]; then
        shift 1
        local drive_list="$*"
        local showpd_data=$(showpd -nohdtot -showcols Id,State,CagePos,FW_Rev,MFR,Model $drive_list 2>&1 | grep -v "No PDs listed")
        local showpd_data_cnt=$(echo "$showpd_data" | wc -l)
        if [[ -z "$showpd_data" || $showpd_data_cnt -ne $# ]]; then
             echo -e "Error: Not all specified drives found in showpd output. drives specificified: $drive_list.\n"
             echo "$showpd_data"
             exit 1
        fi
        local msg="found from user specified list."
    else
        local showpd_data=$(showpd -nohdtot -showcols Id,State,CagePos,FW_Rev,MFR,Model | grep -w degraded 2>&1 | grep -v "No PDs listed")
        local msg="in degraded state."
    fi

    if [ -z "$showpd_data" ]; then
        echo "No PDs listed in degraded state"
        return 1
    fi

    echo "$showpd_data"
    local showpd_data_cnt=$(echo "$showpd_data" | wc -l)

    if [ "$opt" == "--verify" ]; then
         echo -e "\n- $showpd_data_cnt above drive(s) $msg"
         return 0
    fi

    GetConfirmation "Would you like to poweroff and poweron above $showpd_data_cnt drive(s) $msg?"
    if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
        return 1
    fi

    check_showpdch_log "all"

    IFS=$'\n' showpd_data=($(echo "$showpd_data"))

    local start_time=$(date "+%s")
    local count=0
    while [ $count -lt $showpd_data_cnt ]; do
        pd_id=$(echo "${showpd_data[count]}" | awk '{ print $1 }')
        pd_cage_pos=$(echo "${showpd_data[count]}" | awk '{ print $3 }')

        ((count++))
        echo -e "\n$(date "+%Y-%m-%d %X") ($((count))) Performing drive power off/on for pd $pd_id"
        ALPHCNT=0
        drive_stopunit_poweroff_poweron_startunit $pd_id $pd_cage_pos
        if [ $? -ne 0 ]; then
            echo -e "\nError: Drive power off/on for $pd_id failed. Consult support."
            exit 1
        fi

        check_showpdch_log $pd_id

        if [ $count -lt $showpd_data_cnt ] ;then
            echo -e "\n\n############################################################"
            echo -e -n "# - Power off/on completed for $count out of $showpd_data_cnt drives."
            GetTimedConfirmation 10 2 "# Enter 'n' or 'q' to exit from the script. Otherwise it will proceed."
            if [ "$USER_REPLY" == "No" ]; then
                echo -e "\n*** User requested to quit from the script - exiting now. ***\n"
            break
            fi
            echo -e "\n# - No reply from user, proceeding to next drive."
            echo -e "############################################################"
        fi
    done 2>&1

    local delta_time=$(($(date "+%s") - start_time))
    echo -e "\n$(date "+%Y-%m-%d %X") Power off/on performed on $count out of $showpd_data_cnt drive(s). Total time taken is $delta_time seconds."

    return 0
}

if [ $# -eq 0 ]; then
    usage
fi

option=$1

is_sysmgr_up

get_script_version $0 $*

MODEL=$(showsys -d | grep "^System Model" | awk '{ print $NF }')

case $option in
    "--install")
        ;;

    "--verify")
        ;;

    *)
        usage
        ;;
esac

drive_poweroff_on $*

exit $?
