#!/bin/bash
# (C) Copyright 2016-2017 Hewlett Packard Enterprise Development LP
#
# disable_xcopy_lite.sh: Script adds sdt_xcopy_lite_enable=0 in sysvars.init file, disables xcopy and invalidates outstanding xcopy tokens
# - It works around xcopy_lite or ODX token inconsistency issue during TPD upgrade
# - Defect(s) it works around: 144693, 143339, 197371
# Note:
# - Once upgrade is complete or reverted/failed use '--uninstall' option to restore '$KVAR' value and remove it from sysvars.init file.
#
# - How script works:
# - For --install option:
#   - Sets kvar sdt_xcopy_lite_enable=0 in sysvars.init file
#   - disables xcopy: tcli -e 'kvar set -n sdt_xcopy_lite_enable -v 0'
#   - Invalidates outstanding xcopy tokens.
#     - Disables xcopy token consistency check: tcli -e "scsivar set -n check_token_consistency -v 0"
#     - Increases tokens_log_verbosity level: tcli -e "scsivar set -n tokens_log_verbosity -v 3"
#     - Each volume based on 'showvv -showcols Id,Name,VV_WWN' output
#       - For each online node
#         - For given volume gets token list: tcli -e "token list -node # -wwn (top 8 bytes) -wwnre (bottom 8 bytes)"
#         - If tokens found then invalidates each <token id>.
#           tcli -e "token invalidate -wwnre (bottom 8 bytes) -wwn (top 8 bytes) -id <token id>"
#
#     - Once all volumes events are invalidated in the cluster, it posts event below:
#       invalidate_xcopy_tokens: Successfully invalidated $invalidate_tokens outstanding xcopy tokens.
#     - Enables xcopy token consistency check: tcli -e "scsivar set -n check_token_consistency -v 1"
#     - Setting tokens_log_verbosity to default: tcli -e "scsivar set -n tokens_log_verbosity -v 1"
#
# - For --unistall option:
#   - Removes sdt_xcopy_lite_enable=0 entry from sysvars.init file.
#   - enables xcopy: tcli -e 'kvar set -n sdt_xcopy_lite_enable -v 1'
#
# - For --verify option:
#   - Each volume based on 'showvv -showcols Id,Name,VV_WWN' output
#     - For each online node
#       - For given volume gets token list: tcli -e "token list -node # -wwn (top 8 bytes) -wwnre (bottom 8 bytes)"
#       - Updates token count in tokens[$node] array and max outstanding time in MaxSecs.
#     - For given volume if non-zero tokens are found then logs the output in table format.
#     - Logs <vvid> <vvname> <vvwwn> <tokens[node0]> ... <tokens[node7]> <MaxSecs>.

Version=3.00

TPD_VERSIONS="3.1.2|3.1.3|3.2.1|3.2.2"

ALPHABET=({a..z} {A..Z})
MAJOR=2
INFORMATIONAL=5
TOUCHFILESDIR="/var/opt/tpd/touchfiles"
SYSVARS="sysvars.init"

# Failure Codes (or) exit values from scripts
PASS=0        # Passed
FAILPERM=1    # Failure, permanent
FAILTEMP=2    # Failure, temporary
FAILWARN=3    # Warning (only allowed during precheck and postupgrade)
FAILNOTRUN=4  # Failed, Not Yet Run
FAILNA=5      # Failed, Not Applicable
FAILOTHER=127 # Failed, other unknown failure

ERR_FUNC_INSUFF_ARGS="%s: %s() insufficient or more number of arguments passed. Expected: %s, Received: %s"
ERR_SCRIPT_NA="%s: Script is not applicable for %s release or version."
ERR_SYSMGR_NOT_STARTED="%s: sysmgr is not started."
ERR_NOT_ALL_NODES_INTEGRATED="%s: Not all nodes integrated. clwait: $(clwait 2>/dev/null)"
OUT_CNFWAD_THRU_SYSVARS="%s: Would you like to apply workaround persistent across node reboot and TPD upgrade?"
OUT_INSTALLED_SUCCESSFULLY="%s: Successfully installed."
OUT_REMOVED_SUCCESSFULLY="%s: Successfully removed."

usage()
{
    local PROG=$(basename $0)

    echo -e "Usage: $PROG --install"
    echo -e "       $PROG --uninstall"
    echo -e "       $PROG --verify\n"

    echo "--install   : Installs kvar in sysvars.init file, disables xcopy and invalidates outstanding xcopy tokens."
    echo "--uninstall : Uninstalls/Removes kvar from sysvars.init file, enables xcopy."
    echo "--verify    : Verify whether init/rc script installed and checks outstanding xcopy tokens if any."

    echo -e "\nNote:"
    echo " - If upgrade is reverted, --uninstall the work-around to restore back to defaults."

    exit $FAILPERM
}

cleanup()
{
    # Enabling xcopy token consistency check or setting to default value
    tcli -e "scsivar set -n check_token_consistency -v 1"

    # Setting tokens_log_verbosity to default
    tcli -e "scsivar set -n tokens_log_verbosity -v 1"

    exit
}

GetConfirmation()
{
  local MSG="$1"
  local FUNC="$2"

  GETCONFIRMATION=""
  if [ $# -eq 2 ]; then
    output $MSG $FUNC
  fi
  while [ "$GETCONFIRMATION" == "" ]; do
    echo -n "select y=yes n=no q=quit : "
    read reply
    if [ "$reply" == "y" ]; then
        printf "User reply='%s'. User accepted %s workaround. Applying workaround.\n" $reply $FUNC
        GETCONFIRMATION="APPLY-IT"
    elif [[ "$reply" == "q" || "$reply" == "n" ]]; then
        printf "User reply='%s'. Not applying %s workaround.\n" $reply $FUNC
        GETCONFIRMATION="SKIP-IT"
    else
        echo "Unrecognized input '$reply'"
    fi
  done
}

get_script_version()
{
  local PATCHES=$(showversion -b | awk '/^Patches/ && $2 != "None" { print "+"$2 }')
  local TPD=$(showversion -b)
  TPD=$(translate_tpd_release_version "$TPD")

  local altrootTPD=$(showversion -b -r)
  altrootTPD=$(translate_tpd_release_version "$altrootTPD")

  echo "- You are using $(basename $0) script version=$Version, TPD=$TPD$PATCHES and running it on $(date "+%Y-%m-%d %X")"
  echo -e "- clwait: $(clwait)"
  if [ $# -ne 0 ]; then
      echo "- User command line: $*"
  fi
  echo -e "$(showsys -d | grep "^Nodes in Cluster" | sed -e 's/,/,node/g' | awk '{ printf "- Results below are applicable for node%s\n", $NF }')\n \n"
}

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

get_tpd_version()
{
  local partition=$1

  (if [[ "$partition" == "root" || "$partition" == "both" ]]; then
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
    if (NF==1) TAG="GA"
    else TAG=$2

    split($1, t, ".");
    tpd_version=t[1]"."t[2]"."t[3]"."TAG
    print tpd_version
  }'
}

# Function to check TPD version
check_tpd_version()
{
  if [[ $# -eq 0 || $# -gt 2 ]]; then
    output ERR_FUNC_INSUFF_ARGS $(basename $0 .sh) ${FUNCNAME[0]} "1 or 2" $#
    exit $FAILWARN
  fi

  local TPD_VERSIONS="$1"
  if [ $# -ge 2 ]; then
    local partition=$2
  else
    local partition=""
  fi

  local TPD=$(get_tpd_version "$partition")
  echo "$TPD" | egrep -qw "$TPD_VERSIONS"
  if [ $? -ne 0 ]; then
      output ERR_SCRIPT_NA $(basename $0 .sh) "$TPD"
      exit $FAILNA
  fi
}

is_sysmgr_up()
{
  showsysmgr | grep -q "System is up and running"
  if [ $? -ne 0 ]; then
    output ERR_SYSMGR_NOT_STARTED $(basename $0 .sh)
    (set -x; showsysmgr -d)
    exit 1
  fi
}

output()
{
    arg=("${@:2}")
    local message_format="${!1}"
    printf "$message_format\n" "${arg[@]}"
}

isallnodesintegrated()
{
  eval $(clwait --bash) # It exports mynode, master, online and integrated
  if [ $integrated -ne $online ]; then
    output ERR_NOT_ALL_NODES_INTEGRATED $(basename $0 .sh)
    exit $FAILPERM
  fi
}

hex2decimal()
{
  local val=$1

  echo $val | awk --non-decimal-data '{ printf "%d\n", $1 }'
}

get_xvar_value()
{
  local TPDVARTYPE=$1
  local TPDVARNAME=$2
  local TPDVARSIZE=$3
  local DEFAULTVAL=$4
  local NEWVAL=$5

  if [[ "$FS" != "" && "$OPTION" != "--uninstall" ]]; then # It is applicable when altroot option is not specified or for live setup only
    return
  fi

  echo -e "\n(${ALPHABET[ALPHCNT++]}) Current $TPDVARNAME ($TPDVARTYPE) value: (Default: $DEFAULTVAL, Workaround: $NEWVAL)"

  if [ "$TPDVARTYPE" != "kernel" ]; then
    tcli -e "$TPDVARTYPE list" | grep -qw $TPDVARNAME
    if [ $? -eq 0 ]; then # Checking tpd variable exists in current running TPD?
       tcli -e "$TPDVARTYPE show -n $TPDVARNAME"
    fi
  else
    echo -n "$TPDVARNAME = "
    for node in $(seq 0 7); do
      if (( (online & (1 << node)) == 0 )); then # Check whether node is online
        continue
      fi
      echo -n "kernel$node:$(showmemval kernel$node none $TPDVARSIZE 1 $TPDVARNAME | awk '{ print $NF }') "
    done
    echo
  fi
}

# set_tpd_variable_thru_sysvars: It updates sysvars.init file to make [km]var persistent across boot and upgrade
# Function arguments description:
# 1. OPT        : It can be --install, --uninstall, --verify
# 2. TPDVARTYPE : kvar, mvar
# 3. TPDVARNAME : kvar or mvar variable name
# 4. DEFAULTVAL : Dafault value of the variable used during --uninstall
# 5. NEWVAL     : New value set during --install or added in sysvars.init to make it persistent
# 6. TPDLIMITER : It is applicable from 3.2.1.x. If is used to limit the variable for certain TPD only.
#                For other cases user cases user should pass "NA" or "None"
# 7. DEFECTS    : List of defects this workaround is applicable
# 8. DESCRIPTION: Problem description
# Globals used:
# (1) ALPHCNT (2) ALPHABET (3) TOUCHFILESDIR (4) SYSVARS (5) INFORMATIONAL
# System files modified:
# - /var/opt/tpd/touchfiles/sysvars.init

set_tpd_variable_thru_sysvars()
{
  local OPT="$1"
  local TPDVARTYPE="$2"
  local TPDVARNAME="$3"
  local DEFAULTVAL=$(hex2decimal $4)
  local NEWVAL=$(hex2decimal $5)
  local TPDLIMITER="$6"
  local DEFECTS="$7"
  local DESCRIPTION="$8"

  if [ $# -ne 8 ]; then
    echo "ERROR: Insufficient arguments passed"
    exit $FAILPERM
  fi

  ALPHCNT=0

  if [ "$OPT" == "--install" ]; then

    GetConfirmation "OUT_CNFWAD_THRU_SYSVARS" ${FUNCNAME[1]}
    if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
        return
    fi

    tcli -e "$TPDVARTYPE list" | grep -qw $TPDVARNAME
    if [ $? -eq 0 ]; then # If variable exists in current running TPD then apply NEWVAL
      echo -e "\n- Setting $TPDVARNAME=$NEWVAL"
      tcli -e "$TPDVARTYPE set -n $TPDVARNAME -v $NEWVAL"
    fi

    echo "$TPDLIMITER" | egrep -qiw "NA|None"
    if [ $? -eq 0 ]; then
      TPDLIMITER=""
    fi

    # Adding '${TPDVARNAME}=${NEWVAL}' entry in sysvars.init file
    grep -vw $TPDVARNAME $TOUCHFILESDIR/$SYSVARS > /tmp/$SYSVARS.$$ 2> /dev/null
    echo "$TPDVARNAME=$NEWVAL $TPDLIMITER" >> /tmp/$SYSVARS.$$
    message="Added $TPDVARNAME=$NEWVAL entry in $SYSVARS file"
    uc_message=OUT_INSTALLED_SUCCESSFULLY

  elif [ "$OPT" == "--uninstall" ]; then
    echo -e "\n- Setting $TPDVARNAME=$DEFAULTVAL (default value)"
    tcli -e "$TPDVARTYPE set -n $TPDVARNAME -v $DEFAULTVAL"

    # Removing '${TPDVARNAME}' entry from sysvars.init file
    grep -vw $TPDVARNAME $TOUCHFILESDIR/$SYSVARS > /tmp/$SYSVARS.$$ 2> /dev/null
    message="Removed $TPDVARNAME=$NEWVAL entry from $SYSVARS file"
    uc_message=OUT_REMOVED_SUCCESSFULLY
  fi

  if [[ "$OPT" == "--install" || "$OPT" == "--uninstall" ]]; then
    node_list=""
    for node in $(seq 0 7); do
      if (( (online & (1 << node)) == 0 )); then # Check whether node is online
        continue
      fi

      #echo -e "\nNode $node:"
      node_list=${node_list:+$node_list","}
      node_list="${node_list}node$node"
      if [ -s /tmp/$SYSVARS.$$ ]; then
        rcp /tmp/$SYSVARS.$$ node${node}:$TOUCHFILESDIR/$SYSVARS
      else
        rsh node${node} "rm -f $TOUCHFILESDIR/$SYSVARS"
      fi
    done
    rm -f /tmp/$SYSVARS.$$

    message="$message in $node_list."
    em_test --severity=$INFORMATIONAL --post="${FUNCNAME[1]}: $message" > /dev/null
    output $uc_message "${FUNCNAME[1]}"
  fi
  rm -f /tmp/$SYSVARS.$$

  echo -e "\n- Verifying $SYSVARS file for $TPDVARTYPE $TPDVARNAME:\n"

  # Verifying $TPDVARNAME entry in sysvars.init file
  echo -e "(${ALPHABET[ALPHCNT++]}) Verifying $TPDVARNAME entry in $SYSVARS file:"
  onallnodes "grep -w $TPDVARNAME $TOUCHFILESDIR/$SYSVARS 2>/dev/null"

  get_xvar_value $TPDVARTYPE $TPDVARNAME "NA" $DEFAULTVAL $NEWVAL

  echo -e "\n(${ALPHABET[ALPHCNT++]}) Event log messages with '$TPDVARNAME.* $SYSVARS' pattern in last one hour:"
  showeventlog -min 60 -debug -oneline -msg "$TPDVARNAME.* $SYSVARS"
}

disable_xcopy_lite()
{
  local option=$1
  local DESCRIPTION="During upgrade xcopy activity causing token inconsistency issue"
  local DEFECTS="144693,143339" # No spaces in between
  local TPDVARTYPE=kvar
  local TPDVARNAME=sdt_xcopy_lite_enable
  local DEFAULTVAL=1 # Default value (For ex:- run tcli -e 'kvar show -n sdt_xcopy_lite_enable')
  local NEWVAL=0
  local TPDLIMITER="NA" # It is valid from 3.2.1 for prior use "NA" in the script not in sysvars.init file

  echo "${FUNCNAME[0]}: $DESCRIPTION"

  GETCONFIRMATION=""
  set_tpd_variable_thru_sysvars $option $TPDVARTYPE $TPDVARNAME $DEFAULTVAL $NEWVAL "$TPDLIMITER" $DEFECTS "$DESCRIPTION"
  if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
    return $FAILNOTRUN
  fi

  return $PASS
}

# xcopy_tokens: Get xcopy token list for each volume
# --install: Invalidate outstanding xcopy tokens.
# --verify : Look for outstanding xcopy tokens and genrate table on each volume basis.
#
# Return value:
# --install : Return total number of xcopy tokens invalidated.
# --verify  : Return outstanding xcopy tokens.

xcopy_tokens()
{
    local option=$1
    local retval=0
    local invalidate_tokens=0
    local xcopy_tokens_outstanding=0

    while read vvid vvname vvwwn; do
        wwnre=$(echo "$vvwwn" | cut -c 1-16)
        wwn=$(echo "$vvwwn" | cut -c 17-32)

        local vv_xcopy_tokens_outstanding=0
        local MaxSecs=0
        for node in {0..7}; do
            tokens[$node]=-999
            if (( (online & (1 << node)) == 0 )); then # Check whether node is online
                continue
            fi

            tokens_found=$(tcli -e "token list -node $node -wwnre $wwnre -wwn $wwn" 2>/dev/null)
            tokens[$node]=$(echo "$tokens_found" | awk '/== .* tokens found ==/ { print $2 }')
            tokens[$node]=${tokens[$node]:=0}

            if [ ${tokens[$node]} -gt 0 ]; then
                if [ "$option" == "--install" ]; then
                    for token_id in $(echo "$tokens_found" | awk '/: .*, .*seconds/ { gsub(/,/, "", $2); print $2 }'); do
                        echo "- Invalidate xcopy token for volume=$vvname vvid=$vvid vvwwn=$vvwwn token=$token_id in node$node"
                        tcli -e "token invalidate -wwnre $wwnre -wwn $wwn -id $token_id" > /dev/null
                        ((invalidate_tokens++))
                    done
                else
                    MaxSecs=$(echo "$tokens_found" | awk '/: .*, .*seconds/ { if ($4>max) max=$4 } END { print max }')
                    vv_xcopy_tokens_outstanding=1
                fi
            fi
        done

        if [[ "$option" == "--verify" && $vv_xcopy_tokens_outstanding -ne 0 ]]; then
            if [ $xcopy_tokens_outstanding -eq 0 ]; then
                echo -e "\n(${ALPHABET[ALPHCNT++]}) Outstanding xcopy tokens"
                echo -e "\n   Id VVName                           VVWWN                            node0 node1 node2 node3 node4 node5 node6 node7   MaxSecs"
            fi
            xcopy_tokens_outstanding=1
            printf "%5d %-32s %-32s " $vvid $vvname $vvwwn
            for node in {0..7}; do
                if [ ${tokens[$node]} -eq -999 ]; then
                    printf "%5s " "x"
                else
                    printf "%5d " ${tokens[$node]}
                fi
            done
            printf "%9d\n" $MaxSecs
        fi
    done < <(showvv -showcols Id,Name,VV_WWN -nohdtot)

    if [ "$option" == "--install" ]; then
        if [ $invalidate_tokens -ne 0 ]; then
            message="Successfully invalidated $invalidate_tokens outstanding xcopy tokens."
            em_test --severity=$INFORMATIONAL --post="${FUNCNAME[1]}: $message" > /dev/null
            echo -e "\n- $message"
        fi
        retval=$invalidate_tokens
    else
        retval=$xcopy_tokens_outstanding
    fi

   return $retval
}

invalidate_xcopy_tokens()
{
    local option=$1
    local retval=$PASS

    if [ "$option" == "--install" ]; then
        xcopy_tokens "--verify"

        echo -e "\n(${ALPHABET[ALPHCNT++]}) invalidate xcopy tokens (if any)."
        # Disabling xcopy token consistency check
        tcli -e "scsivar set -n check_token_consistency -v 0"

        # Increasing tokens_log_verbosity to get token ids
        tcli -e "scsivar set -n tokens_log_verbosity -v 3"

        xcopy_tokens $option # Invalidate xcopy tokens

        # Enabling xcopy token consistency check or setting to default value
        tcli -e "scsivar set -n check_token_consistency -v 1"

        # Setting tokens_log_verbosity to default
        tcli -e "scsivar set -n tokens_log_verbosity -v 1"

        option="--verify"

    fi

    xcopy_tokens $option
    retval=$?

    if [[ $retval -ne 0 && "$option" == "--install" ]]; then
        echo -e "\nError: Failed to invalidate all xcopy tokens. Status: Failed. Consult Support."
    fi

    if [ $retval -eq 0 ]; then
        echo -e "\n(${ALPHABET[ALPHCNT++]}) None of the xcopy tokens are outstanding."
    fi

    return $retval
}

if [ $# -ne 1 ]; then
    usage
fi

OPTION=$1
FS=""
SHOWVERSION_OPT=""

case $OPTION in
  "--install")   check_tpd_version "$TPD_VERSIONS"
                 trap "cleanup" EXIT SIGINT SIGQUIT SIGILL SIGTRAP SIGABRT SIGBUS SIGFPE SIGKILL SIGSEGV SIGTERM # handle signals
                 ;;

  "--uninstall")
		 ;;

  "--verify")
		 ;;

  *)             usage
                 ;;
esac

$(clwait --bash)

get_script_version $(basename $0) $*

is_sysmgr_up

disable_xcopy_lite $OPTION
retval=$?

if [ $retval -eq $PASS ]; then
    invalidate_xcopy_tokens $OPTION
    retval=$?
fi

exit $retval
