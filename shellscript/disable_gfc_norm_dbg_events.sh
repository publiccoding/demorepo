#!/bin/bash
# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
#
# disable_gfc_norm_dbg_events.sh: Disable GFC_NORM_DBG to avoid event storm
# - If upgrade is failed then uninstall the script after revert.
#
# Defect(s) it workaround: 175841

Version=1.00

# For EGA specify GA and EMUx specify MUx
TPD_VERSIONS="3.2.1.MU[34]"

SCRIPT=$(basename $0)
LOGFILE="/var/log/tpd/${SCRIPT}.log"
ALPHABET=({a..z} {A..Z})

TMP_FILE=/tmp/$SCRIPT.$$

cleanup()
{
    rm -f $TMP_FILE
    trap "" EXIT
    exit
}

is_sysmgr_up()
{
  showsysmgr | grep -q "System is up and running"
  if [ $? -ne 0 ]; then
    output ERR_SYSMGR_NOT_STARTED $(basename $0 .sh)
    (set -x; showsysmgr -d)
    exit $FAILPERM
  fi
}

isallnodesintegrated()
{
  eval $(clwait --bash) # It exports mynode, master, online and integrated
  if [ $integrated -ne $online ]; then
    output ERR_NOT_ALL_NODES_INTEGRATED $(basename $0 .sh)
    exit $FAILPERM
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

usage()
{
  local PROG=$(basename $0)

  echo -e "Usage: $PROG --install"
  echo -e "       $PROG --uninstall"
  echo -e "       $PROG --verify\n"

  echo "--install   : Installs the workaround to disable GFC_NORM_DBG events"
  echo "--uninstall : Uninstalls the workaround to enable GFC_NORM_DBG events"
  echo "--verify    : Verify the workaround whether it is enabled/disabled"

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

disable_gfc_norm_dbg_events()
{
    local opt=$1
    local tpdvartype=kvar
    local tpdvarname=scsi_debug
    local gfc_norm_dbg_mask=0x100000

    if [ $opt == "--install" ]; then
        GetConfirmation "Would you like to apply the workaround to disable GFC_NORM_DBG events?"
        if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
            return 0
        fi

        echo -e "(${ALPHABET[ALPHCNT++]}) Applying the workaround\n"
        tcli -e  "$tpdvartype show -h -n $tpdvarname" | \
        sed -e "s/$tpdvarname = //g" -e "s/ /\\n/g" -e "s/:/ /g" | while read node value; do
            if [ $((value & gfc_norm_dbg_mask)) != 0 ]; then
                local new_value=$((value - gfc_norm_dbg_mask))
                (set -x; tcli -e  "kvar set -n scsi_debug -v $new_value -nodes $node") 2>&1
            fi
        done
    elif [ $opt == "--uninstall" ]; then
        echo -e "(${ALPHABET[ALPHCNT++]}) Removing the workaround\n"
        tcli -e  "$tpdvartype show -h -n $tpdvarname" | \
        sed -e "s/$tpdvarname = //g" -e "s/ /\\n/g" -e "s/:/ /g" | while read node value; do
            if [ $((value & gfc_norm_dbg_mask)) == 0 ]; then
                local new_value=$((value + gfc_norm_dbg_mask))
                (set -x; tcli -e  "kvar set -n scsi_debug -v $new_value -nodes $node") 2>&1
            fi
        done
    fi

    echo -e "\n(${ALPHABET[ALPHCNT++]}) $tpdvarname $tpdvartype values on each node basis:"
    tcli -e  "$tpdvartype show -h -n $tpdvarname" | \
    sed -e "s/$tpdvarname = //g" -e "s/ /\\n/g" -e "s/:/ /g" | while read node value; do
        if [ $((value & gfc_norm_dbg_mask)) != 0 ]; then
            echo "node$node: $tpdvarname=$value GFC_NORM_DBG Enabled"
        else
            echo "node$node: $tpdvarname=$value GFC_NORM_DBG Disabled"
        fi
    done

    return 0
}

if [ $# -eq 0 ]; then
  usage
fi

OPTION=$1
SHOWVERSION_OPT=""
ALPHCNT=0

case $OPTION in
  "--install")   check_tpd_version "$TPD_VERSIONS" root
                 ;;

  "--uninstall") check_tpd_version "$TPD_VERSIONS" root
                 ;;

  "--verify")
		 ;;

  *)             usage
                 ;;
esac

$(clwait --bash)

trap cleanup 0 1 2 3 4 5 6 7 9 15       # handle signals

(
    get_script_version $0 $*

    is_sysmgr_up

    isallnodesintegrated

    disable_gfc_norm_dbg_events $OPTION
    retval=$?
    echo -e "$SCRIPT exit value = $retval" > $TMP_FILE
) | tee -a $LOGFILE

echo -e "\nLog is at $LOGFILE"
retval=$?
rm -f $TMP_FILE
exit $retval
