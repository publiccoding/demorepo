#!/bin/bash
# ignore_hba_type.sh: Ignore HBA type during Host port failover
# - Prior to TPD upgrade or performing conversion, run the script with "--install"
#   option. At the end of the conversion or TPD upgrade, run
#   the script with "--uninstall" option to clean the mvar_fo_ignore_hbatype mvar settings
#
# - Defect(s) it works around: 183883
#
# Script supports --install, --uninstall and --verify options
# (1) --install option
#      - Script adds mvar_fo_ignore_hbatype mvar to sysvars.init file in following format.
#        following format: mvar_fo_ignore_hbatype=1
#
# (2) --uninstall option
#      - Script removes mvar_fo_ignore_hbatype mvar entries from sysvars.init file.
#
# (3) --verify option. It gets data below:
#
#      - Contents of sysvars.init file
#      - Current mvar_fo_ignore_hbatype mvar value. If mvar_fo_ignore_hbatype=1 then workaround is applied
#      - Event log messages with ignore_hba_type.sh pattern in last 8 hours

Version=1.00

# For EGA specify GA; for EMUx specify MUx
TPD_VERSIONS="3.2.1.MU[12345]|3.2.2.GA|3.2.2.MU1"

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

check_hba_model()
{
  # Check for a QLOGIC CNA with model EP8324
  showport -nohdtot -i | grep -w EP8324
  if [ $? -ne 0 ]; then
    echo -e "\nERROR: QLOGIC CNA model EP8324 not found. The script is not applicable for this upgrade"
    exit 1
  fi
}

output()
{
    arg=("${@:2}")
    local message_format="${!1}"
    printf "$message_format\n" "${arg[@]}"
}

usage()
{
  local PROG=$(basename $0)

    echo -e "Usage: $PROG --install"
    echo -e "       $PROG --uninstall"
    echo -e "       $PROG --verify\n"

    echo "--install   : Installs mvar in sysvars.init file to ignore HBA type during failover"
    echo "--uninstall : Uninstalls/Removes mvar from sysvars.init file to not ignore HBA type during failover"
    echo "--verify    : Verify whether workaround is installed"

  exit 1
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
      echo "- Setting $TPDVARNAME=$NEWVAL"
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
    echo "Setting $TPDVARNAME=$DEFAULTVAL (default value)"
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

  echo -e "- Verifying $SYSVARS file for $TPDVARTYPE $TPDVARNAME:\n"

  # Verifying $TPDVARNAME entry in sysvars.init file
  echo -e "(${ALPHABET[ALPHCNT++]}) Verifying $TPDVARNAME entry in $SYSVARS file:"
  onallnodes "grep -w $TPDVARNAME $TOUCHFILESDIR/$SYSVARS 2>/dev/null"

  get_xvar_value $TPDVARTYPE $TPDVARNAME "NA" $DEFAULTVAL $NEWVAL

  echo -e "\n(${ALPHABET[ALPHCNT++]}) Event log messages with '$TPDVARNAME.* $SYSVARS' pattern in last one hour:"
  showeventlog -min 60 -debug -oneline -msg "$TPDVARNAME.* $SYSVARS"
}

ignore_hba_type()
{
  local OPT="$1"
  local DESCRIPTION="Ignore HBA type during port failovers, persistent across node reboot and/or upgrade"
  local DEFECTS="183833"
  local TPDVARTYPE=mvar
  local TPDVARNAME=mvar_fo_ignore_hbatype
  local DEFAULTVAL=0 # Default value (For ex:- run tcli -e 'kvar show -n mvar_fo_ignore_hbatype')
  local NEWVAL=1
  local TPDLIMITER="NA" # It is valid from 3.2.1 for prior use "NA" in the script not in sysvars.init file

  echo "${FUNCNAME[0]}: $DESCRIPTION"

  GETCONFIRMATION=""
  set_tpd_variable_thru_sysvars $OPT $TPDVARTYPE $TPDVARNAME $DEFAULTVAL $NEWVAL "$TPDLIMITER" $DEFECTS "$DESCRIPTION"
  if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
    return $FAILNOTRUN
  fi

  return $PASS
}

if [ $# -eq 0 ]; then
  usage
fi

OPTION=$1
FS=""
SHOWVERSION_OPT=""

case $OPTION in
  "--install")  OPT="--install"
                check_tpd_version "$TPD_VERSIONS"
                check_hba_model
                ;;

  "--uninstall") OPT="--uninstall"
                ;;

  "--verify")  OPT="--verify"
                ;;

  *)            usage
                ;;
esac

$(clwait --bash)

get_script_version $0 $*

is_sysmgr_up

isallnodesintegrated

ignore_hba_type $OPT
rval=$?
rval=${rval:=0}

exit $rval
