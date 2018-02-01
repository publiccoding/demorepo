#!/bin/bash
# disable_intcoalesce.sh: Script clears host port interrupt coalescing toc entries (tfc_int_coalesce_u=0)
# - Need root access
# - Defect(s) it works around: 131794
# - It helps in avoiding host port reset during upgrade
# - IntCoal for host ports will be disabled when node reboots during upgrade or need manual node reboot.

Version=1.02

TPD_VERSIONS="3.1.2.278|3.1.2.322|3.1.2.422|3.1.2.484|3.1.2.592"
INTER_DELAY=60

SCRIPT=disable_intcoalesce.sh
LOGNAME="/var/log/tpd/${SCRIPT}.log"

# Script Algorithm:
# 1) Script works in Master node only
# 2) Make sure TPD=3.1.2.MU3/MU5
# 3) Find list of host ports enabled with interrupt coalescing then disable them by using controlport
# 4) By using gdb it gets data below: 
#    - Offset of sys_gltab
#    - Offset of gl_fcloops in gltab_t structure
#    - Offset of fl_int_coalesce_u in fcloop_t structure
#    - Size of fcloop_t structure
# 5) Read ToC data then find list of ports set with fl_int_coalesce_u=1. 
# 6) By using setmemval script sets sys_gltab.gl_fcloops[tfc_id].fl_int_coalesce_u=0. For ex:-
#    - setmemval sysmgr write u8 sys_gltab+$(($GL_FCLOOPS + $tfc_id * $FCLOOP_SIZE + $FL_INT_COALESCE_U)) 0)
# 7) To update ToC script calls toc_update_fcloop() then request_sync()
#    - startfunc sysmgr none toc_update_fcloop $(($SYS_GLTAB+$GL_FCLOOPS + $tfc_id * $FCLOOP_SIZE)) $SYS_GLTAB
#    - startfunc request_sync

TMP_DIR=/tmp
TOC_DESCRIBE=$TMP_DIR/toc_describe.$$

function cleanup {
    rm -f $TOC_DESCRIBE
    exit
}

# Function to check TPD version
function check_tpd_version
{
    showversion -b | grep "Release version" | egrep -qw "$TPD_VERSIONS"
    if [ $? -ne 0 ]; then
        echo -e "ERROR: Script is not applicable for this release or version\n" >&2
        (set -x; showversion -b)
        exit 1
    fi
}

# Get required offsets thru sysmgr executable
get_fcloop_offsets()
{
  gdb -q -n /opt/tpd/bin/sysmgr <<\EOF 2>/dev/null | sed -e "s/^(gdb) //g"
    printf "sys_gltab=%#x\n", (long)&sys_gltab
    printf "gl_fcloops=%#x\n", (long)&((gltab_t *) 0)->gl_fcloops
    printf "fl_int_coalesce_u=%#x\n", (long)&((fcloop_t *) 0)->fl_int_coalesce_u
    printf "fcloop_t=%#x\n", sizeof(fcloop_t)
    q
EOF
}

# Parse ToC data to get list of ports set with tfc_int_coalesce_u=1
get_tfc_int_coalesce_u_list()
{
  # N:S:P bits format in tfc_id or fl_id
  # Node=bit:9-7  Slot=bit:6-3  Port=bit:2-0

  cat $TOC_DESCRIBE | egrep "tfc_int_coalesce|tfc_int_coalesce_u|tfc_id" | awk '
  / tfc_id = /		 	{ tfc_id=$NF }
  / tfc_int_coalesce = /	{ tfc_int_coalesce=$NF }
  / tfc_int_coalesce_u = /	{
	tfc_int_coalesce_u=$NF
	if (tfc_int_coalesce_u == 1) {
	  node=and(rshift(tfc_id, 7), 0x7)
	  slot=and(rshift(tfc_id, 3), 0xf)
	  port=and(tfc_id, 0x7)

	  printf "%6d %d:%d:%d %-8s %18d\n", tfc_id, node, slot, port, (tfc_int_coalesce == 1) ? "enabled" : "disabled", tfc_int_coalesce_u
	}
  }
  '
}

# disable if interrupt coalescing is enabled for host ports
disable_host_port_intcoal()
{
  local PORTS=$(showport -par |  awk '{ if ($2 == "host" && $NF == "enabled") print $1 }')

  if [ "$PORTS" != "" ]; then
    local count=$(echo $PORTS|wc -w) 
    echo -e "$count host port(s) below enabled with interrupt coalescing:\n"
    showport -par | awk '{ if ($1 == "N:S:P" || ($2 == "host" && $NF == "enabled")) print }'

    GetConfirmation "\nDo you like to disable interrupt coalescing for above host port(s)?"

    for port in $PORTS
    do
      echo -e "\nDisabling host port interrupt coalescing for Port:$port"
      (set -x; controlport intcoal disable $port)
      (set -x; sleep $INTER_DELAY)
    done
  fi
}

GetConfirmation()
{
  local MSG="$1"

  echo -e "$MSG"
  while true ; do
    echo -e -n "select q=quit y=yes n=no: "
    read reply
    if [ $reply == "y" ]; then
        echo
        break
    elif [[ $reply == "q" || $reply == "n" ]]; then
        exit
    else
        echo "Unrecognized input \"$reply\""
    fi
  done
}

# Read ToC data from IDE disk then generate $TOC_DESCRIBE file
read_toc_data()
{
  # Reading TOC data from IDE disk
  toctool -r > /dev/null
  src=toc_`toctool -s | awk 'BEGIN { gen = 0 } { if ($2 > gen) {gen=$2; sysid=$12} } END { print sysid "_" gen }'`

  # Writing ToC text data to $TOC_DESCRIBE file
  cd /common/tocs
  tocsvr --describe $src > $TOC_DESCRIBE
}

# Script to clear fl_int_coalesce_u in sysmgr and tfc_int_coalesce_u in ToC
clear_int_coalesce_u()
{
  local PORT_LIST="$1"

  echo -e "\nClearing interrupt coalescing user flag for above ports"

  OFFSETS=$(get_fcloop_offsets)

  # Get the offset of gl_fcloops
  SYS_GLTAB=$(echo "$OFFSETS" | grep "sys_gltab=" | awk -F "=" '{ print $NF }')
  GL_FCLOOPS=$(echo "$OFFSETS" | grep "gl_fcloops=" | awk -F "=" '{ print $NF }')
  FL_INT_COALESCE_U=$(echo "$OFFSETS" | grep "fl_int_coalesce_u=" | awk -F "=" '{ print $NF }')
  FCLOOP_SIZE=$(echo "$OFFSETS" | grep "fcloop_t=" | awk -F "=" '{ print $NF }')

  echo "$PORT_LIST" | while read tfc_id nsp intcoal tfc_int_coalesce_u; do
    (set -x; setmemval sysmgr write u8 sys_gltab+$(($GL_FCLOOPS + $tfc_id * $FCLOOP_SIZE + $FL_INT_COALESCE_U)) 0)
    (set -x; cli startfunc sysmgr none toc_update_fcloop $(($SYS_GLTAB+$GL_FCLOOPS + $tfc_id * $FCLOOP_SIZE)) $SYS_GLTAB)
  done

  echo
  (set -x; cli startfunc sysmgr none request_sync)
  (set -x; cli startfunc sysmgr none request_sync)
  echo -e "\n- ToC update is complete."
}

check_tpd_version

trap cleanup 0 1 2 3 4 5 6 7 9 15       # handle signals

$(clwait --bash)
if [ $master -ne $mynode ]; then
        echo "ERROR: Run this script from Master node only" >&2
        exit 1
fi

TPD=$(showversion -b | grep "Release version" | awk '{ print $3 }')
( echo -e "- You are using script version=$Version, TPD=$TPD and running it on $(date)\n"

  read_toc_data

  PORT_LIST=$(get_tfc_int_coalesce_u_list)
  if [ "$PORT_LIST" == "" ]; then
    echo "None of the ports set with tfc_int_coalesce_u=1"
    exit
  fi

  echo -e "\nAs per ToC user changed interrupt coalescing for ports below:\n"
  echo "tfc_id N:S:P IntCoal  tfc_int_coalesce_u"
  echo "$PORT_LIST"

  clear_int_coalesce_u "$PORT_LIST"

  echo -e "\n- IntCoal for host ports will be disabled when node reboots during upgrade or need manual node reboot."
) 2>&1 | tee -a $LOGNAME

echo  -e "\n- Script output is saved as $LOGNAME"
