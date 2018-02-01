#!/bin/bash
# 16gbps_disable_tmwo.sh: Script to disable tmwo (tfc_tmwo=2) for 16Gbps FC HBA host ports
# - Need root access
# - Defect(s) it works around: 158869
# - It helps in avoiding 16Gbps HBA host port reset during upgrade
# - TMWO for host ports disabled in the ToC and sysmgr
#
# Script Algorithm:
# 1) Checks whether TPD is in $TPD_VERSIONS list
# 2) Find list of 16Gbps HBA host ports enabled with TMWO
# 3) By using gdb it gets data below:
#    - Offset of sys_gltab
#    - Offset of gl_fcloops in "struct gltab" structure
#    - Size of fcloop_t structure
#    - Offset of tfc_tmwo in fcloop_t structure
# 4) Read ToC data then find list of ports set with tfc_tmwo=1.
# 5) By using setmemval script sets sys_gltab.gl_fcloops[tfc_id].tfc_tmwo=2 (or OPTION_DISABLE). For ex:-
#    - setmemval sysmgr write u8 sys_gltab+$(($GL_FCLOOPS + $tfc_id * $FCLOOP_SIZE + $FL_TMWO)) 2)
# 6) To update ToC script calls toc_update_fcloop() then request_sync()
#    - startfunc sysmgr none toc_update_fcloop $(($SYS_GLTAB+$GL_FCLOOPS + $tfc_id * $FCLOOP_SIZE)) $SYS_GLTAB

Version=1.01

TPD_VERSIONS="3.2.1.GA|3.2.1.MU[1234]|3.2.2.GA|3.2.2.MU[12]"

FC_MAXRATE=16Gbps

PROG=$(basename $0)

TMP_DIR=/tmp
TOC_DESCRIBE=$TMP_DIR/toc_describe.$$

usage()
{
  local PROG=$(basename $0)

  echo -e "Usage: $PROG --install"
  echo -e "       $PROG --verify"

  echo -e "\n--install : Disables $FC_MAXRATE FC HBA host ports TMWO in sysmgr and ToC"
  echo "--verify  : Verify whether any $FC_MAXRATE host ports enabled with TMWO in sysmgr and ToC"

  exit 1
}

cleanup()
{
    rm -f $TOC_DESCRIBE
    exit
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
  echo
}

# Function to check TPD version
check_tpd_version()
{
  if [ $# -ne 1 ]; then
    printf "ERROR: Insufficient arguments passed."
    exit 1
  fi

  local TPD_VERSIONS="$1"
  local TPD=$(showversion -b)
  TPD=$(translate_tpd_release_version "$TPD")

  echo "$TPD" | egrep -qw "$TPD_VERSIONS"
  if [ $? -ne 0 ]; then
      echo -e "\nERROR: Script is not applicable for $TPD release or version."
      showversion -b
      exit 1
  fi
}

# Get required offsets thru sysmgr executable
get_fcloop_offsets()
{
  gdb -q -n /opt/tpd/bin/sysmgr <<\EOF 2>/dev/null | sed -e "s/^(gdb) //g"
    printf "sys_gltab=%#x\n", (long)&sys_gltab
    printf "gl_fcloops=%#x\n", (long)&((struct gltab *) 0)->gl_fcloops
    printf "fl_tmwo=%#x\n", (long)&((fcloop_t *) 0)->fl_tmwo
    printf "fcloop_t=%#x\n", sizeof(fcloop_t)
    q
EOF
}

# Parse ToC data to get list of ports set with tfc_tmwo=1
get_tfc_tmwo_list()
{
  local PORT_LIST=$(showport -par | \
      awk -v FC_MAXRATE=$FC_MAXRATE '{ if ($2 == "host" && $5 == FC_MAXRATE && $10 == "enabled") print $1 }' | xargs | sed -e "s/ /|/g"
  )

  if [ "$PORT_LIST" == "" ]; then
    return
  fi

  # N:S:P bits format in tfc_id or fl_id
  # Node=bit:9-7  Slot=bit:6-3  Port=bit:2-0

  egrep "tfc_tmwo|tfc_tmwo_u|tfc_id" $TOC_DESCRIBE | awk '
  / tfc_id = /		{ tfc_id=$NF }
  / tfc_tmwo = /	{ tfc_tmwo=$NF }
  / tfc_tmwo_u = /	{
	tfc_tmwo_u=$NF
	if (tfc_tmwo == 1) {
	  node=and(rshift(tfc_id, 7), 0x7)
	  slot=and(rshift(tfc_id, 3), 0xf)
	  port=and(tfc_id, 0x7)

	  printf "%6d %d:%d:%d %-8s %10d\n", tfc_id, node, slot, port, (tfc_tmwo == 1) ? "enabled" : "disabled", tfc_tmwo_u
	}
  }
  ' | egrep "$PORT_LIST"
}

GetConfirmation()
{
  local MSG="$1"
  local FUNC="$2"

  GETCONFIRMATION=""
  if [ $# -eq 2 ]; then
    echo -e "\n$FUNC: $MSG"
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

# Read ToC data from IDE disk then generate $TOC_DESCRIBE file
read_toc_data()
{
  echo "${FUNCNAME[1]}: Reading TOC data, it can take few minutes in large system"
  # Reading TOC data from IDE disk
  src="toc_$(toctool -r | grep Created | sed -e "s/.*toc_//g" -e "s/\.tar//g" | sort -nr | head -1)"

  echo "${FUNCNAME[1]}: Converting ToC data to ASCII format"
  # Writing ToC text data to $TOC_DESCRIBE file
  tocsvr --describe /common/tocs/$src > $TOC_DESCRIBE
}

# Script sets tfc_tmwo=2 (or OPTION_DISABLE) in sysmgr and ToC
disable_tmwo()
{
  local OPT=$1

  read_toc_data

  PORT_LIST=$(get_tfc_tmwo_list)
  if [ "$PORT_LIST" == "" ]; then
    echo "${FUNCNAME[0]}: None of the $FC_MAXRATE FC HBA host ports enabled with TMWO"
    exit
  fi

  echo -e "\nAs per ToC TMWO enabled for $FC_MAXRATE FC HBA host ports below:\n"
  echo "tfc_id N:S:P TMWO     tfc_tmwo_u"
  echo "$PORT_LIST"

  if [ "$OPT" != "--install" ]; then
    return
  fi

  GetConfirmation "Would you like to disable TMWO for above host port(s)?" "${FUNCNAME[0]}"
  if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
    return
  fi

  OFFSETS=$(get_fcloop_offsets)

  # Get the offset of gl_fcloops
  SYS_GLTAB=$(echo "$OFFSETS" | grep "sys_gltab=" | awk -F "=" '{ print $NF }')
  GL_FCLOOPS=$(echo "$OFFSETS" | grep "gl_fcloops=" | awk -F "=" '{ print $NF }')
  FCLOOP_SIZE=$(echo "$OFFSETS" | grep "fcloop_t=" | awk -F "=" '{ print $NF }')
  FL_TMWO=$(echo "$OFFSETS" | grep "fl_tmwo=" | awk -F "=" '{ print $NF }')

  echo "- SYS_GLTAB=$SYS_GLTAB"
  echo "- GL_FCLOOPS=$GL_FCLOOPS"
  echo "- FCLOOP_SIZE=$FCLOOP_SIZE"
  echo -e "- FL_TMWO=$FL_TMWO\n"

  echo "$PORT_LIST" | while read tfc_id nsp tmwo tfc_tmwo_u; do
    (set -x; setmemval sysmgr write u8 sys_gltab+$(($GL_FCLOOPS + $tfc_id * $FCLOOP_SIZE + $FL_TMWO)) 2)
    (set -x; cli startfunc sysmgr write toc_update_fcloop $(($SYS_GLTAB+$GL_FCLOOPS + $tfc_id * $FCLOOP_SIZE)) $SYS_GLTAB)
  done

  echo -e "\n${FUNCNAME[0]}: TMWO for $FC_MAXRATE FC HBA host ports disabled in the ToC and sysmgr"
}

if [ $# -ne 1 ]; then
  usage
fi

OPTION=$1

check_tpd_version "$TPD_VERSIONS"

get_script_version $PROG $*

trap cleanup 0 1 2 3 4 5 6 7 9 15       # handle signals

case $OPTION in
  "--install") ;;

  "--verify")   ;;

  *)            usage
                ;;
esac

disable_tmwo $OPTION
