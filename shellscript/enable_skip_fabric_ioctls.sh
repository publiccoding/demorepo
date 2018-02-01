#!/bin/bash
# (C) Copyright 2016-2017 Hewlett Packard Enterprise Development LP
#
# enable_skip_fabric_ioctls.sh:  To avoid too many CT calls in the fabric or ct_mgmt_get_port_info events
# - Defect(s) it works around: 103714
# - Reapply the work around, if node rescue takes place on same setup
# - rc script will be automatically removed during TPD upgrade
#   TPD=3.1.3.GA, 3.1.3.MU1, 3.1.3.MU2, 3.2.1.GA, 3.2.1.MU1, 3.2.1.MU2
#
# - In 3.1.3.MU1 it is applicable when fabric_ioctl() hangs as per node crash. It can avoid further ioctls after subsquent reboot.
# - Defect(s) it works around: 115477
#
# - In 3.2.1.MU1 "checkhealth -svc -detail host" hang is noticed. To work around it enabling support for 3.2.1.GA and 3.2.1.MU1.
# - Defect(s) it works around: 120895
#
# - In 3.2.1.MU2 "checkhealth -svc -detail host" or checkupgrade -postcheck hang is noticed.
#   Added altroot option to workaround during upgrade.
# - Defect(s) it works around: 126005

Version=4.04
SCRIPT_NAME=$(basename $0)

# For EGA specify GA and EMUx specify MUx
TPD_VERSIONS="3.1.3.GA|3.1.3.MU[1-3]|3.2.1.GA|3.2.1.MU[1-5]|3.2.2.GA|3.2.2.MU[1-6]|3.3.1.GA|3.3.1.MU1"

# Failure Codes (or) exit values from scripts
PASS=0        # Passed
FAILPERM=1    # Failure, permanent
FAILTEMP=2    # Failure, temporary
FAILWARN=3    # Warning (only allowed during precheck and postupgrade)
FAILNOTRUN=4  # Failed, Not Yet Run
FAILNA=5      # Failed, Not Applicable
FAILOTHER=127 # Failed, other unknown failure

# Script globals
ENVIRONMENT=/etc/environment
INITDIR=/etc/init.d
RCDIR=/etc/rc2.d
TOUCHFILESDIR="/var/opt/tpd/touchfiles"
SYSVARS="sysvars.init"
INFORMATIONAL=5 # To post events
ALPHABET=({a..z} {A..Z})

OUT_CNFWAD_THRU_INIT="%s: Would you like to apply workaround in the init script?"
OUT_USERACCEPTEDWAD="User reply='%s'. User accepted %s workaround. Applying workaround."
OUT_NOT_APPLYINGWAD="User reply='%s'. Not applying %s workaround."
OUT_SUCCESSFULLY_INSTALLED="%s: Successfully installed %s file on %s."
OUT_SUCCESSFULLY_UNINSTALLED="%s: Successfully uninstalled %s file."
OUT_INSTALLED_SUCCESSFULLY="%s: Successfully installed."
OUT_REMOVED_SUCCESSFULLY="%s: Successfully removed."
ERR_FUNC_INSUFF_ARGS="%s: %s() insufficient or more number of arguments passed. Expected: %d, Received: %d"
ERR_SCRIPT_NA="%s: Script is not applicable for %s release or version."
ERR_SYSMGR_NOT_STARTED="%s: sysmgr is not started."
ERR_NOT_ALL_NODES_INTEGRATED="%s: Not all nodes integrated. clwait: $(clwait 2>/dev/null)"
ERR_UNKNOWN_OPTION="%s unknown option specified."

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

  local TPD=$(get_tpd_version $partition)
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
  local FUNC="$2"

  GETCONFIRMATION=""
  if [ $# -eq 2 ]; then
    output $MSG $FUNC
  fi
  while [ "$GETCONFIRMATION" == "" ]; do
    echo -n "select y=yes n=no q=quit : "
    read reply
    if [ "$reply" == "y" ]; then
        output OUT_USERACCEPTEDWAD $reply $FUNC
        GETCONFIRMATION="APPLY-IT"
    elif [[ "$reply" == "q" || "$reply" == "n" ]]; then
        output OUT_NOT_APPLYINGWAD $reply $FUNC
        GETCONFIRMATION="SKIP-IT"
    else
        echo "Unrecognized input '$reply'"
    fi
  done
}

hex2decimal()
{
  local val=$1

  echo $val | awk --non-decimal-data '{ printf "%d\n", $1 }'
}

# get_xvar_value: Script to get kvar, mvar, dvar, and kernel global values
# Function arguments description:
# 1. TPDVARTYPE: kvar, mvar
# 2. TPDVARNAME: kvar or mvar variable name
# 3. TPDVARSIZE: Size of the TPD variable. It is applicable for kernel globals for rest it should be "NA"
# 4. DEFAULTVAL: Dafault value of the variable used during --uninstall
# 5. NEWVAL    : New value set during --install or added in sysvars.init to make it persistent
# Globals used:
# (1) FS (root file system "" for root or /altroot). (2) OPTION (3) (clwat --bash) variables

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

# set_tpd_variable_during_init: It sets given [kmd]var or kernel global during node boot-up
# Function arguments description:
# 1. OPT        : It can be --install, --uninstall, --verify
# 2. TPDVARTYPE : kvar, mvar
# 3. TPDVARNAME : kvar ot mvar variable name
# 5. DEFAULTVAL : Dafault value of the variable used during --uninstall
# 6. NEWVAL     : New value set during --install or added in sysvars.init to make it persistent
# 7. DEFECTS    : List of defects this workaround is applicable
# 8. DESCRIPTION: Problem description
# Globals used:
# (1) ALPHCNT (2) ALPHABET (3) TOUCHFILESDIR (4) SYSVARS (5) INFORMATIONAL
# System files modified:
# - /var/opt/tpd/touchfiles/sysvars.init set_tpd_variable_thru_sysvars()

set_tpd_variable_during_init()
{
  local OPT="$1"
  local TPDVARTYPE="$2"
  local TPDVARNAME="$3"
  local TPDVARSIZE="$4"
  local DEFAULTVAL=$(hex2decimal $5)
  local NEWVAL=$(hex2decimal $6)
  local DEFECTS="$7"
  local DESCRIPTION="$8"

  if [ $# -ne 8 ]; then
    echo "ERROR: Insufficient arguments passed to ${FUNCNAME[0]} function - caller: ${FUNCNAME[1]}"
    exit $FAILPERM
  fi

  local INITSCRIPT=tpd_$TPDVARNAME
  ALPHCNT=0

  if [ "$OPT" == "--install" ]; then

    GetConfirmation "OUT_CNFWAD_THRU_INIT" ${FUNCNAME[1]}
    if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
        return
    fi

    generate_initscript_file $TPDVARTYPE $TPDVARNAME $TPDVARSIZE $DEFAULTVAL $NEWVAL "$DEFECTS" "$DESCRIPTION" > $INITSCRIPT.$$
    chmod +x $INITSCRIPT.$$

    node_list=""
    for node in $(seq 0 7); do
      if (( (online & (1 << node)) == 0 )); then # Check whether node is online
        continue
      fi

      if [ "$FS" == "" ]; then # To apply the workaround in live system; NA for "altroot"
        # Terminate earlier pid to install latest bits
        rsh node${node} 'kill $(ps -C'"$INITSCRIPT"' --no-headers -o pid=) 2>/dev/null'
      fi

      node_list=${node_list:+$node_list","}
      node_list="${node_list}node$node"
      rcp ${INITSCRIPT}.$$ node${node}:${FS}${INITDIR}/${INITSCRIPT}
      rsh node${node} "$CHROOT update-rc.d -f ${INITSCRIPT} remove 2>&1 >/dev/null" 2>&1 > /dev/null
      rsh node${node} "$CHROOT update-rc.d ${INITSCRIPT} defaults 2>&1 >/dev/null" 2>&1 >/dev/null
      if [ "$FS" == "" ]; then # To apply the workaround in live system; NA for "altroot"
        echo "Node ${node}:"
        rsh node${node} ${INITDIR}/${INITSCRIPT} start
      fi > /dev/null
    done
    rm -f ${INITSCRIPT}.$$

    message="Successfully installed ${FS}${INITDIR}/${INITSCRIPT} file on $node_list."
    em_test --severity=$INFORMATIONAL --post="$INITSCRIPT: $message" >/dev/null
    output OUT_SUCCESSFULLY_INSTALLED ${FUNCNAME[1]} ${FS}${INITDIR}/${INITSCRIPT} "$node_list"
    output OUT_INSTALLED_SUCCESSFULLY ${FUNCNAME[1]}

  elif [ "$OPT" == "--uninstall" ]; then
        echo "- Terminating $INITSCRIPT process on all the nodes then restoring $TPDVARNAME to default"
        onallnodes "(
          if [ -f $INITDIR/$INITSCRIPT ]; then
             $INITDIR/$INITSCRIPT stop
          fi
        )" > /dev/null

        echo "- Removing $INITSCRIPT script from each node"
        local FILESLIST=$(onallnodes "ls -l ${FS}${INITDIR}/${INITSCRIPT} 2>/dev/null" | grep ${INITSCRIPT})
        onallnodes "$CHROOT update-rc.d -f ${INITSCRIPT} remove > /dev/null" > /dev/null
        onallnodes "rm -f ${FS}${INITDIR}/${INITSCRIPT}" > /dev/null

        if [ "$TPDVARTYPE" != "kernel" ]; then # Setting variables to default values
          tcli -e "$TPDVARTYPE set -n $TPDVARNAME -v $DEFAULTVAL" > /dev/null
        else
          for node in $(seq 0 7); do
            if (( (online & (1 << node)) == 0 )); then # Check whether node is online
              continue
            fi
            setmemval kernel$node write $TPDVARSIZE $TPDVARNAME $DEFAULTVAL > /dev/null
          done
        fi

        if [ "$FILESLIST" != "" ]; then
          message="Removed $INITSCRIPT init script, current $(get_xvar_value $TPDVARTYPE $TPDVARNAME $TPDVARSIZE $DEFAULTVAL $NEWVAL)"
          em_test --severity=$INFORMATIONAL --post="$message" >/dev/null
        fi
        output OUT_SUCCESSFULLY_UNINSTALLED ${FUNCNAME[1]} $INITSCRIPT
        output OUT_REMOVED_SUCCESSFULLY ${FUNCNAME[1]}
  fi # End of - "$OPT" == "--install"

  echo -e "- Verifying $INITSCRIPT init script:\n"

  echo -e "(${ALPHABET[ALPHCNT++]}) $INITSCRIPT init/rc script files list:"
  onallnodes "(ls -l ${INITDIR}/${INITSCRIPT} /altroot${INITDIR}/${INITSCRIPT} \
      ${RCDIR}/S*${INITSCRIPT} /altroot${RCDIR}/S*${INITSCRIPT} 2>/dev/null)"

  if [[ "$TPDVARTYPE" != "kernel" && "$TPDVARTYPE" != "kvar" ]]; then
      echo -e "(${ALPHABET[ALPHCNT++]}) Checking whether ${INITSCRIPT} script process running?"
      onallnodes "ps -f -w -C $INITSCRIPT --no-header"
  fi

  echo -e "(${ALPHABET[ALPHCNT++]}) Current $TPDVARNAME ($TPDVARTYPE) value: (Default: $DEFAULTVAL, Workaround: $NEWVAL)"
  get_xvar_value $TPDVARTYPE $TPDVARNAME $TPDVARSIZE $DEFAULTVAL $NEWVAL

  echo -e "\n(${ALPHABET[ALPHCNT++]}) Event log messages with ${INITSCRIPT} pattern in last one hour:"
  showeventlog -min 60 -debug -oneline -msg "${INITSCRIPT}"
}

# It creates script to tune [kmd]var during node boot-up
generate_initscript_file()
{
  local TPDVARTYPE="$1"
  local TPDVARNAME="$2"
  local TPDVARSIZE="$3"
  local DEFAULTVAL=$4
  local NEWVAL=$5
  local DEFECTS="$6"
  local DESCRIPTION="$7"

  local INITSCRIPT=tpd_$TPDVARNAME
  local FUNC=set_${TPDVARTYPE}_variable_during_init # It is used in init script
  local TPD=$(showversion -b)
  TPD=$(translate_tpd_release_version "$TPD")

  cat << EOF # Import variables from main script or function to here-document
#!/bin/bash
# $INITDIR/$INITSCRIPT: It sets $TPDVARNAME=$NEWVAL to avoid '$DESCRIPTION'
# - It is applicable in TPD=$TPD
# - Defect(s) it works around: $DEFECTS
# - Script will be automatically removed in next TPD upgrade.

Version=$Version # Version of the script

### BEGIN INIT INFO
# Provides:         $INITSCRIPT
# Required-Start:   tpdinit
# Required-Stop:
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: To avoid '$DESCRIPTION'
### END INIT INFO

# Exporting environment variables
. $ENVIRONMENT

TPDVARTYPE=$TPDVARTYPE
TPDVARNAME=$TPDVARNAME
DEFAULTVAL=$DEFAULTVAL
NEWVAL=$NEWVAL
DESCRIPTION="$DESCRIPTION"

SLEEP_TIME=300
MAJOR=2
INFORMATIONAL=5

$FUNC()
  {
EOF

case $TPDVARTYPE in # Is it kvar, mvar, dvar?
  kvar)
  cat << "KVAR_EOF"
    if [[ $integrated_mask -ne 0 ]]; then # This node is in cluster

        tcli -e "kvar show -n $TPDVARNAME"|grep -q ":$DEFAULTVAL"
        if [ $? -eq 0 ]; then
          tcli -e "kvar set -n $TPDVARNAME -v $NEWVAL"
          message=$(tcli -e "kvar show -n $TPDVARNAME")
          em_test --severity=$INFORMATIONAL --post="$SCRIPT: After setting $TPDVARNAME=$NEWVAL: kvar shows $message"
        fi
        tcli -e "kvar show -n $TPDVARNAME"
        exit
    fi  # End of $integrated_mask
KVAR_EOF
 ;;

  mvar)
  cat << "MVAR_EOF"
    if [[ $integrated_mask -ne 0 ]]; then # This node is in cluster

        pm_pid=$(ps -C pm --no-headers -o pid=)

        pid=$(ps -f -C sysmgr --no-headers | grep -e " $pm_pid .* sysmgr --pmfg" | awk '{ print $2; exit }')

        if [ "$pid" != "" ] && [[ $pid != "$prev_pid" || $master != "$prev_master" ]]; then # Change of sysmgr pid/master node

          Current=$(tcli -e "mvar show -n $TPDVARNAME" 2>/dev/null | awk '{ print $NF }')
          Current=$(hex2decimal $Current)
          if [ "$Current" != "" ]; then # If tcli command works
            prev_pid=$pid
            prev_master=$master
          fi

          if [ "$Current" == "$DEFAULTVAL" ]; then

            tcli -e "mvar set -n $TPDVARNAME -v $NEWVAL"
            message=$(tcli -e "mvar show -n $TPDVARNAME")
            em_test --severity=$INFORMATIONAL --post="$SCRIPT: After setting $TPDVARNAME=$NEWVAL: mvar shows '$message'"

          fi
        fi # End of - Change of sysmgr pid/master node
    fi # end of $integrated_mask
MVAR_EOF
 ;;

  dvar)
  cat << "DVAR_EOF"
    if [[ $integrated_mask -ne 0 ]]; then # This node is in cluster

        pm_pid=$(ps -C pm --no-headers -o pid=)

        pid=$(ps -f -w -C ddcscan --no-headers | grep " $pm_pid .* ddcscan -b" | awk '{ print $2; exit }')

        if [ "$pid" != "" ] && [[ $pid != "$prev_pid" ]]; then # Change of ddcscan pid

          Current=$(tcli -e "$TPDVARTYPE show -n $TPDVARNAME" 2>/dev/null | grep "Nid $mynode:" | awk '{ print $NF }')
          if [ "$Current" != "" ]; then # If tcli command works
            prev_pid=$pid
          fi

          if [ "$Current" == "$DEFAULTVAL" ]; then

            tcli -e "$TPDVARTYPE set -n $TPDVARNAME -v $NEWVAL"
            message=$(tcli -e "$TPDVARTYPE show -n $TPDVARNAME")
            em_test --severity=$INFORMATIONAL --post="$SCRIPT: After setting $TPDVARNAME=$NEWVAL: $TPDVARTYPE shows '$message'"

          fi
        fi # End of - Change of ddcscan pid
    fi # End of - $integrated
DVAR_EOF
 ;;
esac

  cat << "EOF"
 } # End of set_xvar_variable_during_init

 hex2decimal()
 {
   local val=$1

   echo $val | awk --non-decimal-data '{ printf "%d\n", $1 }'
 }

SCRIPT=$(basename $0)

  case "$1" in
    start)
        echo "Launching $SCRIPT script to work around '$DESCRIPTION' issue by setting $TPDVARNAME=$NEWVAL"
        prev_pid=""
        while true ; do
          eval $(clwait --bash)

          if [[ "$integrated" != "" && "$online" != "" && "$mynode" != "" ]]; then # Is tpd module loaded?

            (( mask=1<<mynode ))
            (( integrated_mask=mask&integrated ))
EOF

  echo -e "\n            $FUNC\n"

  cat << "EOF"
          fi # End of - Is tpd module loaded?
          sleep $SLEEP_TIME
        done < /dev/null >/dev/null 2>&1 & # end of while-loop (close i/p & o/p to follow thru)
        ;;

    stop)
        echo "- Terminating $SCRIPT script pids if any"
        kill $(ps -C $SCRIPT --no-headers -o pid=)
        ;;

    *)
        echo "Usage: $0 start|stop"
        exit 1
        ;;
  esac
EOF
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

  echo -e "Usage: $PROG --install [altroot]"
  echo -e "       $PROG --uninstall [altroot]"
  echo -e "       $PROG --verify\n"

  echo "--install   [altroot] : Installs required init/rc script in root or altroot partitions."
  echo "--uninstall [altroot] : Uninstalls required init/rc script from root or altroot partitions."
  echo "--verify              : Verify whether init/rc script installed."

  exit $FAILPERM
}

enable_skip_fabric_ioctls()
{
  local DESCRIPTION="To avoid too many CT calls or ct_mgmt_get_port_info events"
  local DEFECTS="103714,115477,126005" # No spaces in between
  local TPDVARTYPE=mvar
  local TPDVARNAME=skip_fabric_ioctls
  local DEFAULTVAL=0 # Default value (For ex:- run tcli -e 'kvar show -n skip_fabric_ioctls')
  local NEWVAL=1
  local TPDVARSIZE="NA" # It is applicable for kernel globals. For kvar,mvar,dvar pass "NA"

  echo "${FUNCNAME[0]}: $DESCRIPTION"

  GETCONFIRMATION=""
  set_tpd_variable_during_init $OPT $TPDVARTYPE $TPDVARNAME $TPDVARSIZE $DEFAULTVAL $NEWVAL $DEFECTS "$DESCRIPTION"
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
CHROOT=""
OPT=""
SHOWVERSION_OPT=""

case $OPTION in
  "--install")
                if [[ $# -ge 2 && $2 != "altroot" ]]; then
                    output ERR_UNKNOWN_OPTION $2
                    exit $FAILPERM
                fi

                if [[ $# -ge 2 && "$2" == "altroot" ]]; then
                    FS="/altroot"
                    CHROOT="chroot $FS"
                    SHOWVERSION_OPT="-r"
                fi
                check_tpd_version "$TPD_VERSIONS"
                OPT="--install"
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

enable_skip_fabric_ioctls
rval=$?
rval=${rval:=$PASS}
exit $rval
