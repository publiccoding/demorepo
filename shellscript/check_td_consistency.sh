#!/bin/bash
# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
#
# check_td_consistency.sh
#
# Advises if there are inconsistent backup phandles and specifies node(s) to reboot.
# The script requires patch 3.2.1.MU3 P52 or 3.2.1.MU5 P53 to be in place since the script runs a special
# kernel function and reads a special kernel variable installed only by the patch.
#
#   Kernel function:   ipc_dump_bkup_td_status()
#   Kernel variable:   has_bkup_td
#
# The kernel function ipc_dump_bkup_td_status() must be run BEFORE the kernel variable has_bkup_td is checked.
#
#   has_bkup_td == 0 - Bad.     The node's kernel does not have the required ticket dispenser phandler backup which
#                               is grounds for reboot.
#                               or there is no ticket dispenser thread because rcopy is not started.
#   has_bkup_td == 1 - Good.    The associated backup handle has been found.
#
# Defect(s) covered: 187216/184107/100066/123692
#

Version=1.01

TPD_VERSIONS="3.2.1.MU3|3.2.1.MU5"

SCRIPT=$(basename $0)

usage()
{
    local prog=$(basename $0)

    echo -e "Usage: $prog --verify  : Check ticket dispenser consistency and specify any nodes to reboot."

    exit 1
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
      echo "- User command line: $@"
  fi
  echo -e "$(showsys -d -nohdtot | grep "^Nodes in Cluster" | sed -e 's/,/,node/g' | awk '{ printf "- Results below are applicable for node%s\n", $NF }')\n"
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
    ERR_FUNC_INSUFF_ARGS="%s: %s() insufficient or more number of arguments passed. Expected: %s, Received: %s"
    output ERR_FUNC_INSUFF_ARGS $(basename $0 .sh) ${FUNCNAME[0]} "1 or 2" $#
    exit 1
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
      ERR_SCRIPT_NA="%s: Script is not applicable for %s release or version."
      output ERR_SCRIPT_NA $(basename $0 .sh) "$TPD"
      exit 1
  fi
}

output()
{
    arg=("${@:2}")
    local message_format="${!1}"
    printf "$message_format\n" "${arg[@]}"
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

isitrcsetup()
{
    showrcopy | grep -q "Remote Copy System Information"
    if [ $? -ne 0 ]; then
      echo -e "Script is applicable for remote copy setup only.\n" >&2
      (set -x; showrcopy -d)
      exit
    fi
}

check_td_consistency()
{
    # Check each node in turn
    local node
    local retval=0

    is_kernel_patched

    $(clwait --bash)
    for node in {0..7}; do
        if (( (online & (1 << node)) == 0 )); then # Check whether node is online
          continue
        fi
        echo "Checking node$node"

        # Set has_bkup_td=1 before running ipc_dump_bkup_td_status()
        setmemval kernel$node none u8 has_bkup_td 1 > /dev/null

        # Execute kernel function ipc_dump_bkup_td_status() to populate 'has_bkup_td'
        startfunc kernel$node none ipc_dump_bkup_td_status >/dev/null

        # Read back result from kernel variable 'has_bkup_td'
        local result=$(showmemval kernel$node none u8 1 has_bkup_td | awk '{print $2}' )
        if [ $result -eq 0 ]; then
            ERR_TDCHECK_INCONSISTENT="Node%s WARNING: ticket dispenser is inconsistent. Reboot node%s before upgrade."
            output ERR_TDCHECK_INCONSISTENT $node $node
            retval=1
        else
            OUT_TDCHECK_OK="Node%s is consistent."
            output OUT_TDCHECK_OK $node
        fi
    done

    # Return failure code if ANY node requires a reboot
    return $retval
}

# Ensure kernel has been patched by checking for the variable has_bkup_td the patch should introduce
is_kernel_patched()
{
    grep -q has_bkup_td /proc/kallsyms
    if [ $? -ne 0 ]; then
        ERR_TDCHECK_NOTPATCHED="%s: Check cannot be performed because the required kernel patch has not been installed."
        output ERR_TDCHECK_NOTPATCHED $SCRIPT
        exit 1
    fi

    return 0
}

if [ $# -ne 1 ]; then
    usage
fi

get_script_version $(basename $0) "$@"

option=$1
case $option in
    "--verify")
        ;;

    *)
        usage
        ;;
esac

check_tpd_version "$TPD_VERSIONS" root
isitrcsetup
isallnodesintegrated
is_sysmgr_up

check_td_consistency
retval=$?
exit $retval
