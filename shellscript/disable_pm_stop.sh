#!/bin/bash
# disable_pm_stop.sh: Disable pm --stop in tpdinit script by commenting pids=`pidof pm` line
# - Script automatically applies workaround in root and altroot partitions
# - It works around Suicide Pact Panic on Master Node during TPD upgrade to 3.2.2 EMU2
# - Defect(s) it works around: 155908, 165757, 167128
# Note:
# - Once upgrade is complete use '--uninstall' option to restore tpdinit as earlier

Version=1.00

# For EGA specify GA and EMUx specify MUx
TGT_TPD_VERSIONS="3.2.2.GA|3.2.2.MU[12]"

# Failure Codes (or) exit values from scripts
PASS=0        # Passed
FAILPERM=1    # Failure, permanent
FAILTEMP=2    # Failure, temporary
FAILWARN=3    # Warning (only allowed during precheck and postupgrade)
FAILNOTRUN=4  # Failed, Not Yet Run
FAILNA=5      # Failed, Not Applicable
FAILOTHER=127 # Failed, other unknown failure

OUT_USERACCEPTEDWAD="User reply='%s'. User accepted %s workaround. Applying workaround."
OUT_NOT_APPLYINGWAD="User reply='%s'. Not applying %s workaround."
ERR_FUNC_INSUFF_ARGS="%s: %s() insufficient or more number of arguments passed. Expected: %s, Received: %s"
ERR_SCRIPT_NA="%s: Script is not applicable for %s release or version."
ERR_SYSMGR_NOT_STARTED="%s: sysmgr is not started."
ERR_NOT_ALL_NODES_INTEGRATED="%s: Not all nodes integrated. clwait: $(clwait 2>/dev/null)"
ERR_UNKNOWN_OPTION="%s unknown option specified."
OUT_SUCCESSFULLY_INSTALLED_WAD="%s: Successfully installed the workaround."
OUT_SUCCESSFULLY_UNINSTALLED_WAD="%s: Successfully uninstalled the workaround."

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
    output MSG $FUNC
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

  echo "--install   : Installs the workaround"
  echo "--uninstall : Uninstalls the workaround from root partition"
  echo "--verify    : Verify the workaround"

  echo -e "\nNote: Uninstall the workaround, once upgrade is complete or aborted"

  exit $FAILPERM
}

disable_pm_stop()
{
  local OPT=$1

  local DESCRIPTION="To avoid Master node panic during TPD upgrade"

  echo "${FUNCNAME[0]}: $DESCRIPTION"

  case $OPT in
    "--install")
       grep -q '`pidof pm`' /altroot/etc/init.d/tpdinit
       if [ $? -eq 0 ]; then
         GETCONFIRMATION=""
         GetConfirmation "%s: Would you like to disable pm --stop in tpdinit?" "${FUNCNAME[0]}"
         if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
           return $FAILNOTRUN
         fi
	 onallnodes "sed -i -e 's/  if pids=.pidof pm.; then/  if false; then #if pids=\`pidof pm\`; then/'" /etc/init.d/tpdinit /altroot/etc/init.d/tpdinit > /dev/null
         output OUT_SUCCESSFULLY_INSTALLED_WAD ${FUNCNAME[0]}
       fi
       ;;

    "--uninstall")
       onallnodes "sed -i -e 's/if false; then #if pids=\`pidof pm/if pids=\`pidof pm/' /etc/init.d/tpdinit /altroot/etc/init.d/tpdinit" > /dev/null
       output OUT_SUCCESSFULLY_UNINSTALLED_WAD ${FUNCNAME[0]}
       ;;
  esac

 echo -e "\n- Verifying the workaround: If you find, '#' in the output then workaround is applied\n"
 onallnodes "grep -H -e '\`pidof pm' -e '\`#pidof pm' /etc/init.d/tpdinit /altroot/etc/init.d/tpdinit"

  return $PASS
}

if [ $# -eq 0 ]; then
  output ERR_FUNC_INSUFF_ARGS $(basename $0 .sh) main "1" $#
  usage
fi

OPTION=$1

OPT=""

case $OPTION in
  "--install")
                check_tpd_version "$TGT_TPD_VERSIONS" altroot
                OPT="--install"
                ;;

  "--uninstall")
                if [ $# -ne 1 ]; then
                    output ERR_FUNC_INSUFF_ARGS $(basename $0 .sh) main 1 $#
                    usage
                fi
                OPT="--uninstall"
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

disable_pm_stop $OPT
rval=$?
rval=${rval:=$PASS}
exit $rval
