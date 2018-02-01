#!/bin/bash
# rewrite_pd_label.sh: Script to rewrite PD label when too many CRC errors are in the label region of the disk
# Defect(s) addressed: SIE84066/138946/140546,195810
# Version 2.00:
#   - In case the system id is 0, script treats last 5 digits of system serial number as new system id then updates PD label.
#   - Added error checks for the input PD list as well.

Version=2.02

# For EGA specify GA and EMUx specify MUx
TPD_VERSIONS="3.1.2.MU3|3.1.3.GA|3.1.3.MU[12]|3.2.1.GA|3.2.1.MU[123]"

# Failure Codes (or) exit values from scripts
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

get_script_version()
{
  local PATCHES=$(showversion -b | awk '/^Patches/ && $2 != "None" { print "+"$2 }')
  local TPD=$(showversion -b)
  TPD=$(translate_tpd_release_version "$TPD")

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

  GETCONFIRMATION=""
  echo -e "$MSG"
  while [ "$GETCONFIRMATION" == "" ]; do
    echo -n "select y=yes n=no q=quit : "
    read reply
    if [ "$reply" == "y" ]; then
        output OUT_USERACCEPTEDWAD $reply
        GETCONFIRMATION="APPLY-IT"
        break
    elif [[ "$reply" == "q" || "$reply" == "n" ]]; then
        output OUT_NOT_APPLYINGWAD $reply
        GETCONFIRMATION="SKIP-IT"
        exit $FAILNOTRUN
    else
        echo "Unrecognized input '$reply'"
        exit $FAILNOTRUN
    fi
  done
}

output()
{
    arg=("${@:2}")
    local message_format="${!1}"
    printf "$message_format\n" "${arg[@]}"
}

get_sysmgr_structure_sizes_offsets()
{
    gdb -q -n /opt/tpd/bin/sysmgr <<\EOF | grep -e "size=" -e "offset=" -e "sys_name="
    printf "disk_t size=%d\n", sizeof(disk_t)
    printf "gl_dsks offset=%d\n", &((gltab_t *) 0)->gl_dsks
    printf "sys_info.sys_name=%u\n", &(sys_info.sys_name)
    q
EOF
}

usage()
{
    echo -e "Usage: $0 -p <pd id>"
    echo -e "  <pd id> : PD id or comma separated PD id list"
    echo -e "       For example:- $0 -p 23,45,57,200\n"
    exit $FAILPERM
}

echo -e "Executing $0: Script to rewrite PD label"
PDLIST=""
while getopts p:h arg; do
    case "$arg" in
    p)   PDLIST="$OPTARG";;
    h)   usage;;
    [?]) usage;;
    esac
done

if [ -z "$PDLIST" ]; then
    usage
fi

isallnodesintegrated

is_sysmgr_up

check_tpd_version "$TPD_VERSIONS" root

if [ "$PDLIST" == "all" ]; then
    USER_PDLIST=($(showpd -nohdtot -showcols Id))
else
    USER_PDLIST=($(echo "$PDLIST" | sed -e "s/,/ /g"))
    SYS_PDLIST=($(showpd -nohdtot -showcols Id))
    #valideate all the user provided PD ID
    for pd_id in "${USER_PDLIST[@]}"; do

        status=$(echo "${SYS_PDLIST[@]}"|sed -e "s/ /\n/g"|grep -w $pd_id)
        if [ -z "$status" ]; then
            echo -e "pd $pd_id not found in the system\n"
            exit $FAILTEMP
        fi

        dupe=$(echo "${USER_PDLIST[@]}"|sed -e "s/ /\n/g"|grep -w $pd_id|wc -l)

        if [ $dupe -gt 1 ]; then
            echo -e "PD $pd_id entered more than once in the input PD list\n"
            exit $FAILTEMP
        fi

    done
fi

sys_id_mod=0
SystemID=$(showsys -d | awk '/^System ID/ { print $NF }')
if [ $SystemID -eq 0 ]; then
    echo "Error: 'showsys -d' returning System ID as '0'."
    SerialNumber=$(showsys -d|grep "^Serial Number" |awk '{print $NF}')

    #system id is the last 5 digits of te serial number
    SystemID=$(echo ${SerialNumber:${#SerialNumber} - 5})
    GetConfirmation "Would you like to rewrite the system Id with $SystemID, it is obtained from Array Serial Number $SerialNumber?"
    sys_id_mod=1
fi

SYS_GLTAB=$(cli showmemval sysmgr none addr 1 sys_gltab | awk '{ print $2 }')

WRITE_TO_DISK=$(cli showmemval sysmgr none addr 1 write_to_disk | awk '{ print $2 }')

OFFSETS=$(get_sysmgr_structure_sizes_offsets)

DISK_T_SIZE=$(echo "$OFFSETS" | grep "disk_t size" | awk -F "=" '{ print $NF }')

GL_DSKS_OFFSET=$(echo "$OFFSETS" | grep "gl_dsks offset" | awk -F "=" '{ print $NF }')

SYS_NAME=$(echo "$OFFSETS" | grep sys_name | awk -F "=" '{ print $NF }')

echo "- SYS_NAME=$SYS_NAME"
echo "- SystemID=$SystemID"
echo "- SYS_GLTAB=$SYS_GLTAB"
echo "- GL_DSKS_OFFSET=$GL_DSKS_OFFSET"
echo "- DISK_T_SIZE=$DISK_T_SIZE"

echo -e "- User PD List:\n"
showpd -s ${USER_PDLIST[@]}
GetConfirmation "\nWould you like to call write_label() thru startfunc for the above listed disk(s)?"

write_label_pass_count=0
count=1
for pd_id in "${USER_PDLIST[@]}"; do

    WRT_TO=$((SYS_GLTAB + GL_DSKS_OFFSET + (DISK_T_SIZE * pd_id) ))

    echo -e "\n$count) Will rewrite SystemID=$SystemID to PD=$pd_id"
    CMD="startfunc sysmgr none write_label $WRT_TO $WRT_TO $SYS_NAME $SystemID $WRITE_TO_DISK"
    echo -e "$CMD"

    echo "Rewriting SystemID=$SystemID to PD: $pd_id"
    #Execution of the startfunc command
    $CMD
    retval=$?

    if [ $retval -ne 0 ]; then
        echo "Error: write_label() failed with $retval return value for pd $pd_id. Consult Support."
    else
        echo -e "Successfully wrote $SystemID System ID to pd $pd_id and ToC update is complete."
        ((write_label_pass_count++))
    fi
    ((count++))
done

retval=0
if [ $write_label_pass_count -ne ${#USER_PDLIST[@]} ]; then
    echo -e "\nTOC update failed for $((${#USER_PDLIST[@]} - $write_label_pass_count)) PD(s) out of ${#USER_PDLIST[@]}. Consult Support."
    retval=1
else
    if [[ "$PDLIST" == "all" && $sys_id_mod -eq 1 ]]; then
        echo -e "\nNote: Update on all drives are complete, need to reboot the array."
    fi
fi

if [[ "$PDLIST" != "all" && $sys_id_mod -eq 1 ]]; then
    echo -e "\nNote: Perform similar operation on all drives then need to reboot the array in the end."
fi

exit $retval
