#!/bin/bash
# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
#
# ks_encryption_backup_restore_recover.sh: Local/External KeyStore encryption backup/restore/recover
# Defect(s) covered: 182704,184919
#
# Script Algorithm:
# 1) Script checks whether system is enabled with encryption or not. If not, exits.
#
# 2) Script supports options below:
#     --install backup  : Create current configuration backup for EKM or backup all keys for LKM.
#     --install restore : From earlier backup restore configuration for EKM or restore all keys for LKM.
#     --install recover : Recover EKM certificates from /pr_mnt partition or altroot partition.
#     --uninstall       : Remove recently script created backup.
#     --verify          : Verify the number of Cobra drive(s) by firmware version.
#
# 3) If KeyStore is EKM, script validates 'controlencryption checkekm' status.
#    If it fails during --verify, it suggests to take backup and restore to recover from the problem.
#
# 4) It runs 'controlencryption validate' to make sure we received "Completed .* validating all drives" pattern in the output.
#    If it fails, returns failure in --verify.
#
# 5) If user specifies "--install backup"
#    - It copies files in /etc/3par/certs to /altroot/etc/3par/certs directory in every node, if checkekm Successful for EKM KeyStore.
#    - For EKM, it backup current configuration. For LKM, it back up all keys. By running, controlencryption backup <file> command.
#    - backup file will be saved as /common/support/Keystore_backup.<Model>.<InServ#> and it will be placed on all the nodes.
#
# 6) If user specifies "--install restore"
#    - It checks earlier backup file /common/support/Keystore_backup.<Model>.<InServ#> present or not. If not, exits.
#    - It runs, controlencryption restore <file> to restore configuration for EKM or for LKM to restore all keys.
#    - If restore task shows "Completed .* encrypting all drives with new key" pattern then marks as passed otherwise failed.
#
# 7) If user specifies "--install recover"
#    - If /pr_mnt/certificates file is present it runs commands below to restore EKM ceritificates.
#      cli Tpd::rtpd "updatecert ekm-client" 
#      cli Tpd::rtpd "updatecert ekm-server"
#    - Else
#      onallnodes "cp /altroot/etc/3par/certs/ekm* /etc/3par/certs/"
#
# 8) If user specifies --uninstall in EKM setup, it prechecks the status of 'controlencryption checkekm' before removing KEYSTORE_BACKUP_FILE.

Version=1.01

TPD_VERSIONS="3.2.1|3.2.2.GA|3.2.2.MU[1-3]"

DIR=/common/support
KEYSTORE_BACKUP_FILE=$DIR/Keystore_backup

SCRIPT=ks_encryption_backup_restore.sh
LOGFILE="/var/log/${SCRIPT}.log"
TMP_FILE=/tmp/$SCRIPT.$$

usage()
{
    local prog=$(basename $0)

    echo -e "Usage: $prog --install <Type>"
    echo -e "       $prog --uninstall"
    echo -e "       $prog --verify\n"

    echo -e "--install backup  : Create current configuration backup for EKM or backup all keys for LKM."
    echo -e "--install restore : From earlier backup restore configuration for EKM or restore all keys for LKM."
    echo -e "--install recover : Recover EKM certificates from /pr_mnt partition or altroot partition."
    echo -e "--uninstall       : Remove recently script created backup."
    echo -e "--verify          : Verify the number of Cobra drive(s) by firmware version.\n"

    echo -e "\nWARNING: Make sure customer has encryption backup"
    echo -e "\nNote: Once TPD upgrade is complete, run the script with --uninstall option to remove earlier created backup file."

    exit 1
}

cleanup()
{
    rm -f $TMP_FILE
    trap "" EXIT
    exit
}

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

GetConfirmation()
{
  local MSG="$1"

  unset GETCONFIRMATION
  echo -e "\n$(basename $0 .sh): $MSG"
  while true ; do
    echo -e -n "select y=yes n=no q=quit : "
    read reply
    if [ $reply == "y" ]; then
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

is_controlencryption_enabled()
{
    local status=$(controlencryption -nohdtot status | awk '($2 == "yes")')

    if [ -z "$status" ]; then
        echo "Data Encryption is not enabled"
        exit 1
    fi
}

ks_encryption_validate()
{
    local task_id=$(controlencryption validate | awk '{ print $2 }')
    if [ -z "$task_id" ]; then
        echo -e "\n${FUNCNAME[1]}: Unable to run 'controlencryption validate'. Consult Support"
        return 1
    fi

    echo -e "${FUNCNAME[1]}: Waiting for 'controlencryption validate' task $task_id completion, it can take few minutes."

    local task_status=$(waittask $task_id)
    echo -e "$task_status" | grep -q "Task .* done"
    if [ $? -ne 0 ]; then
        (set -x; showtask -d $task_id) 2>&1
        echo -e "\n${FUNCNAME[1]}: 'controlencryption validate' task execution failed. Consult Support"
        return 1
    fi

    local task_details=$(showtask -d $task_id)
    echo "$task_details"
    echo "$task_details" | grep -q "Completed .* validating all drives"
    if [ $? -ne 0 ]; then
        echo -e "\n${FUNCNAME[1]}: 'controlencryption validate' failed. Consult Support"
        return 1
    fi

    echo -e "\ncontrolencryption validate: Passed.\n"

    return 0
}

ks_encryption_checkekm()
{
    local KeyStore=$1

    if [ "$KeyStore" != "EKM" ]; then
        return 0
    fi

    local cmd="controlencryption checkekm"
    echo "+ $cmd"
    local status=$($cmd 2>&1)

    echo "$status"

    echo "$status" | grep -q "EKM settings are correct"
    if [ $? -ne 0 ]; then
        echo -e "\n${FUNCNAME[0]}: '$cmd' failed."
        return 1
    fi

    echo -e "\n$cmd: Passed."

    return 0
}

ks_encryption_backup_restore()
{
    local opt=$1
    if [ $# -eq 2 ]; then
        local type=$2
    fi

    local KeyStore=$(controlencryption -nohdtot status | awk '{ print $6 }')

    if [[ "$KeyStore" != "EKM" && "$KeyStore" != "LKM" ]]; then

        echo -e "\nError: Unknown KeyStore '$KeyStore' reported"
        return 1
    fi

    if [[ "$KeyStore" != "EKM" && "$type" == "recover" ]]; then
        echo "Error: 'recover' type ption only supported for 'EKM' KeyStore."
        (set -x; controlencryption status) 2>&1
        return 1
    fi

    ks_encryption_checkekm $KeyStore
    local checkekm_retval=$?

    if [[ $checkekm_retval -ne 0 && $opt == "--verify" ]]; then
        echo -e "\nNote: To resolve above error, run commands below. It may resolve the problem. If not, Consult Support."
        echo "$SCRIPT --install backup"
        echo "$SCRIPT --install restore"
        return 1
    fi

    if [ "$opt" == "--uninstall" ]; then
        if [ $checkekm_retval -ne 0 ]; then
            echo -e "\nError: 'controlencryption checkekm' failed. We cannot run $opt option. Consult Support."
            return 1
        fi

        echo "${FUNCNAME[0]}: Removing $KEYSTORE_BACKUP_FILE file"
        onallnodes "rm -f $KEYSTORE_BACKUP_FILE"
        return 0
    fi

    local encr_validate_rval=0
    if [ "$type" != "recover" ]; then
        ks_encryption_validate
        local encr_validate_rval=$?
    fi

    if [ "$opt" == "--verify" ]; then
        return $encr_validate_rval
    fi

    if [ $type == "backup" ]; then
        if [ $checkekm_retval -eq 0 ]; then
            echo -e "\n- Copying /etc/3par/certs directory to altroot partition."
            onallnodes "cp -f /etc/3par/certs/* /altroot/etc/3par/certs/" > /dev/null # Copy certs files from root to altroot
        else
            echo -e "\nWARNING: As 'controlencryption checkekm' failed, skipping in copying /etc/3par/certs directory to altroot partition.\n"
        fi


        if [ "$KeyStore" == "EKM" ]; then
            local message="KeyStore is EKM. Would you like to backup current configuration?"
        else
            local message="KeyStore is LKM. Would you like to backup all keys?"
        fi

        GetConfirmation "$message"
        if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
            return 1
        fi

        onallnodes mkdir -p $DIR > /dev/null
        controlencryption backup -password $EncriptionBackupFilePassword $KEYSTORE_BACKUP_FILE
        $(clwait --bash)
        onothernodes "rcp node$mynode:$KEYSTORE_BACKUP_FILE $DIR" > /dev/null
        echo -e "$KeyStore backup file cksum $(cksum $KEYSTORE_BACKUP_FILE)"
    elif [ $type == "restore" ]; then
        if [ ! -s $KEYSTORE_BACKUP_FILE ]; then
            echo -e "\nError: Unable to open $KEYSTORE_BACKUP_FILE file. Create backup before restoring it."
            return 1
        fi

        local showpd_data=$(showpd -nohdtot -showcols Id,Type,State,Detailed_State,FW_Rev,MFR,Model | grep -e failed -e degraded)
        if [ -n "$showpd_data" ]; then
            echo "$showpd_data"
            GetConfirmation "Above drive(s) in failed/degraded state, it may impact '$type' operation. Would you like to continue?"
            if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
                return 1
            fi
        fi

        if [ "$KeyStore" == "EKM" ]; then
            local message="KeyStore is EKM. Would you like to restore configuration from earlier created backup? It can take few minutes to complete."
        else
            local message="KeyStore is LKM. Would you like to restore all keys from earlier created backup? It can take few minutes to complete."
        fi

        GetConfirmation "$message"
        if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
            return 1
        fi

        local task_id=$(controlencryption restore -password $EncriptionBackupFilePassword $KEYSTORE_BACKUP_FILE | awk '{ print $2 }')
        if [ -z "$task_id" ]; then
            echo -e "\n${FUNCNAME[0]}: Unable to run 'controlencryption restore'. Consult Support"
            return 1
        fi

        echo -e "${FUNCNAME[0]}: Waiting for 'controlencryption restore' task $task_id completion."

        local task_status=$(waittask $task_id)

        echo -e "$task_status" | grep -q "Task .* done"
        if [ $? -ne 0 ]; then
            (set -x; showtask -d $task_id) 2>&1
            echo -e "\n${FUNCNAME[0]}: 'controlencryption restore' task execution failed. Consult Support"
            return 1
        fi

        local task_details=$(showtask -d $task_id)
        echo "$task_details"
        echo "$task_details" | grep -q "Completed .* encrypting all drives with new key"
        if [ $? -ne 0 ]; then
            echo -e "\n${FUNCNAME[1]}: 'controlencryption restore' failed. Consult Support"
            return 1
        fi

        echo -e "\ncontrolencryption restore: Passed."
    elif [ "$KeyStore" == "EKM" ]; then # recover for EKM KeyStore only
        if [ -f /pr_mnt/certificates ]; then
            echo -e "\n- Updating ekm-client certificates."
            cli Tpd::rtpd "updatecert ekm-client"
            echo -e "\n- Updating ekm-server certificates."
            cli Tpd::rtpd "updatecert ekm-server"
        else
            echo -e "\n- Copying /altroot/etc/3par/certs/ekm* files to altroot partition."
            onallnodes "cp /altroot/etc/3par/certs/ekm* /etc/3par/certs/"
        fi
        echo
        (set -x; controlencryption checkekm) 2>&1
    fi

    return 0
}

if [[ $# -eq 0 || $# -gt 2 ]]; then
    usage
fi

option=$1
type=""
SHOWVERSION_OPT=""

is_sysmgr_up

is_controlencryption_enabled

$(clwait --bash)

showsys_data=$(showsys -d | egrep "^System Model|^Serial Number")
if [ -z "$showsys_data" ]; then
    echo "Error: 'showsys -d' failed"
    return 1
fi

model=$(echo "$showsys_data" | grep "^System Model" | awk '{ print $NF }')
inserv_sn=$(echo "$showsys_data" | grep "^Serial Number" | awk '{ print $NF }')
EncriptionBackupFilePassword=${model}_${inserv_sn}

KEYSTORE_BACKUP_FILE=${KEYSTORE_BACKUP_FILE}.${model}.${inserv_sn}

case $option in
    "--install")
        check_tpd_version "$TPD_VERSIONS" root

        if [ $# -ne 2 ]; then
            echo -e "\nError: Type option is not specified."
            exit 1
        fi

        type=$2
        if [[ -z "$type" || $type != "backup" && $type != "restore" && $type != "recover" ]]; then
            echo -e "\nError: Invalid type '$type' option specified."
            exit 1
        fi

        if [[ $type == "restore" && ! -s $KEYSTORE_BACKUP_FILE ]]; then
            echo -e "\nError: Unable to open $KEYSTORE_BACKUP_FILE file from node$mynode. Create backup before restoring it."
            exit 1
        fi
        ;;

    "--uninstall")
        ;&

    "--verify")
        if [ $# -ne 1 ]; then
            echo -e "\nError: Too many arguments specified."
            exit 1
        fi
        ;;

     *) usage
        ;;
esac

trap cleanup EXIT SIGINT SIGQUIT SIGILL SIGTRAP SIGABRT SIGBUS SIGFPE SIGKILL SIGSEGV SIGTERM # handle signals

(
  get_script_version $(basename $0) $*

  ks_encryption_backup_restore $option $type
  retval=$?
  echo -e "$SCRIPT exit value = $retval" > $TMP_FILE
) | tee -a $LOGFILE


echo -e "\nLog is at $LOGFILE"

retval=$(grep "^$SCRIPT exit value = " $TMP_FILE 2>/dev/null | tail -n 1 | awk '{ print $NF }')
retval=${retval:=0}
rm -f $TMP_FILE
exit $retval
