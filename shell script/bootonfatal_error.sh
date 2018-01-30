#!/bin/bash
# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
#
# bootonfatal_error.sh: Script to allow node boot on 'Fatal error: Code 10, sub-code 0x31 or 0x32' errors
# - Defect(s) it works around: 197348
# Note:
# - If all nodes rescue is performed then script may need to be applied.
# - If we install the script in root partition. In subsequent reboot script will be applied or nvram values will be changed.
# - During online upgrade if we install the script in altroot partition then nvram values will be changed during node boot-up.
#
# - How it works?
# --install [altroot] option:
#   - If altroot specified script sets FS="/altroot" otherwise FS=""
#   - Prior to modifying $FS/etc/init.d/tpdinit file it checks workaround is not present. If not present it proceeds.
#     - Before "Only initialize eanet here if this isn.t a fresh net install" pattern it adds
#       'nvramtool --set max_same_fatal 20' in $FS/etc/init.d/tpdinit file for all the nodes.
#     - It updates latest md5sum in $FS/var/lib/dpkg/info/tpd-core.md5sums file.
#
# --uninstall [altroot] option: (optional for the field, so it won't appear in usage)
#   - If altroot specified script sets FS="/altroot" otherwise FS=""
#   - Prior to modifying $FS/etc/init.d/tpdinit file it checks workaround is present? If then it proceeds.
#     - It removes "nvramtool --set max_same_fatal" line from $FS/etc/init.d/tpdinit file for all the nodes.
#     - It updates latest md5sum in $FS/var/lib/dpkg/info/tpd-core.md5sums file.
#
# --verify option:
#   - It verifies workaround in /etc/init.d/tpdinit and /altroot/etc/init.d/tpdinit files.
#   - It gets current nvram max_same_fatal value for each node.

Version=1.01

# For EGA specify GA and EMUx specify MUx
TPD_VERSIONS="3.2.2.GA|3.2.2.MU[1-4]|3.3.1.GA"

STORESERV_MODEL_LIST="20..."

TPDINIT="etc/init.d/tpdinit"
TPD_CORE_MD5SUMS="/var/lib/dpkg/info/tpd-core.md5sums"

ALPHABET=({a..z} {A..Z})

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
OUT_NO_WAD_FOUND="%s: No workaround found%s."
ERR_SCRIPT_NA_MODEL="%s: Script is not applicable for %s StoreServ Model."

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

# Function to check InServ Model
check_StoreServ_model()
{
  if [ $# -eq 0 ]; then
    output ERR_FUNC_INSUFF_ARGS $(basename $0 .sh) ${FUNCNAME[0]} 1 $#
    exit $FAILWARN
  fi

  local STORESERV_MODEL_LIST="$1"

  local MODEL=$(showsys -d | grep "System Model" | awk '{ print $NF }')

  echo "$MODEL" | egrep -qw "$STORESERV_MODEL_LIST"
  if [ $? -ne 0 ]; then
      output ERR_SCRIPT_NA_MODEL $(basename $0 .sh) "$MODEL"
      exit $FAILNA
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

    echo -e "Usage: $PROG --install [altroot]"
    #echo -e "       $PROG --uninstall [altroot]"
    echo -e "       $PROG --verify\n"

    echo "--install   [altroot] : Installs the workaround in root/altroot partition."
    #echo "--uninstall [altroot] : Uninstalls the workaround from root/altroot partition."
    echo "--verify              : Verify the workaround."

    exit $FAILPERM
}

update_md5sums()
{
    local File=$1 # File to compute md5sums without leading "/"
    local FS="$2" # File System. "": For root, "/altroot": For altroot partition
    local md5sumsfile="$FS$3"  # msd5sums file where changes will be applied

    $(clwait --bash)

    echo -e "\n(${ALPHABET[ALPHCNT++]}) Updating md5sums for $FS/$File in $md5sumsfile for all the nodes"
    local new_md5sum_file=$(md5sum $FS/$File | awk '{ print $1 }')
    sed -e "\:$File$:s/^[^ ]*/$new_md5sum_file/" $md5sumsfile > /tmp/tpd-xx.md5sums.$$
    mv -f /tmp/tpd-xx.md5sums.$$ $md5sumsfile
    onothernodes "rcp node$mynode:$md5sumsfile $md5sumsfile" > /dev/null
}

bootonfatal_error()
{
    local option=$1
    local pattern="nvramtool --set max_same_fatal"
    local description="To allow node boot on 'Fatal error: Code 10, sub-code 0x31 or 0x32' errors."

    case $option in
    "--install")
        echo -e "${FUNCNAME[0]}: $description\n"

        GETCONFIRMATION=""
        GetConfirmation "%s: Would you like to allow node boot on fatal errors?" "${FUNCNAME[0]}"
        if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
            return $FAILNOTRUN
        fi
        local string="Only initialize eanet here if this isn.t a fresh net install"
        onallnodes "sed -i -e '/$pattern/d' \
            -e '/$string/ i\        $pattern 20' $FS/etc/init.d/tpdinit" > /dev/null

        update_md5sums "$TPDINIT" "$FS" "$TPD_CORE_MD5SUMS"
        output OUT_SUCCESSFULLY_INSTALLED_WAD ${FUNCNAME[0]}
    ;;

    "--uninstall")
        local result=$(onallnodes "grep '$pattern' $FS/etc/init.d/tpdinit" | grep "$pattern")
        if [ -n "$result" ]; then
            onallnodes "sed -i -e '/$pattern/d' $FS/etc/init.d/tpdinit" > /dev/null

            update_md5sums "$TPDINIT" "$FS" "$TPD_CORE_MD5SUMS"
            output OUT_SUCCESSFULLY_UNINSTALLED_WAD ${FUNCNAME[0]}
        else
            output OUT_NO_WAD_FOUND ${FUNCNAME[0]} " in the specified partition"
            exit 1
        fi
    ;;
    esac

    echo -e "\n(${ALPHABET[ALPHCNT++]}) Verifying workaround in /etc/init.d/tpdinit and /altroot/etc/init.d/tpdinit files"
    onallnodes "grep -H -e '$pattern' /etc/init.d/tpdinit /altroot/etc/init.d/tpdinit"

    echo -e "\n(${ALPHABET[ALPHCNT++]}) Current nvram max_same_fatal value: (Default: 0, Workaround: 20 in hex)"
    onallnodes 'nvramtool --get max_same_fatal'

    return $PASS
}

if [[ $# -lt 1 || $# -eq 2 && $2 != "altroot" ]]; then
    usage
fi

ALPHCNT=0
FS=""

option=$1

case $option in
  "--install")
      if [ "$2" == "altroot" ]; then
          check_tpd_version "$TPD_VERSIONS" altroot
          FS="/altroot"
      else
          check_tpd_version "$TPD_VERSIONS" root
      fi
      ;;

  "--uninstall")
      if [ "$2" == "altroot" ]; then
          FS="/altroot"
      fi
      ;;

  "--verify")
      ;;

  *)  usage
      ;;
esac

$(clwait --bash)

get_script_version $(basename $0) $*

is_sysmgr_up

check_StoreServ_model "$STORESERV_MODEL_LIST"

isallnodesintegrated

bootonfatal_error $option
retval=$?
exit $retval
