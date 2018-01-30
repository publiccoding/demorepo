#!/bin/bash
# check_xri_availability.sh: Script to check xri availability
# Defect(s) covered: 156750,155358

Version=1.00
TPD_VERSIONS="3.2.2.GA|3.2.2.MU[12]"

ERR_FUNC_INSUFF_ARGS="%s: %s() insufficient or more number of arguments passed. Expected: %d, Received: %d"
ERR_SCRIPT_NA="%s: Script is not applicable for %s release or version."
ERR_SYSMGR_NOT_STARTED="%s: sysmgr is not started."

output()
{
    arg=("${@:2}")
    local message_format="${!1}"
    printf "$message_format\n" "${arg[@]}"
}

usage()
{
  local PROG=$(basename $0)

    echo -e "       $PROG --verify\n"

    echo "--verify    : Verify whether init/rc script installed."

    exit 1
}

reset_kvar()
{
  tcli -e "kvar set -n hba_wiggle_code -v 1"
  exit
}

get_tpd_version()
{
  showversion -b | grep "^Release version" | sed -e 's/Release version//g' -e 's/[()]//g' | sort -u | awk '
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
  if [[ $# -ne 1 ]]; then
    output ERR_FUNC_INSUFF_ARGS $(basename $0 .sh) ${FUNCNAME[0]} 1 $#
    exit 3
  fi

  local TPD_VERSIONS="$1"

  local TPD=$(get_tpd_version)
  echo "$TPD" | egrep -qw "$TPD_VERSIONS"
  if [ $? -ne 0 ]; then
      output ERR_SCRIPT_NA $(basename $0 .sh) "$TPD"
      exit 5
  fi
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
  echo -e "$(showsys -d | grep "^Nodes in Cluster" | sed -e 's/,/,node/g' | awk '{ printf "- Results below are applicable for node%s\n", $NF }')\n\n"
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

is_sysmgr_up()
{
  showsysmgr | grep -q "System is up and running"
  if [ $? -ne 0 ]; then
    output ERR_SYSMGR_NOT_STARTED $(basename $0 .sh)
    (set -x; showsysmgr -d)
    exit 1
  fi
}

OPTION="$1"

case $OPTION in
  "--verify")   OPT="--verify"
                ;;

  *)            echo -e "ERROR: Invalid option '$OPTION' specified.\n"
                usage
                ;;
esac

$(clwait --bash)

get_script_version $0 $*

check_tpd_version "$TPD_VERSIONS"

is_sysmgr_up

trap reset_kvar 0 1 2 3 4 5 6 7 9 15

tcli -e "kvar set -n hba_wiggle_code -v 0"

TARGET_READY_PORTS=$(showport -nohdtot | awk '/target .* ready .* host/ { print $1 }'|xargs)
EMFC_PORT_LIST=$(showport -nohdtot -i $TARGET_READY_PORTS | awk '/LPe1200/ { print $1 }' | xargs)

if [ "$EMFC_PORT_LIST" == "" ]; then
  echo "- No emfc HBA ports found"
  exit
fi

echo "- $(echo $EMFC_PORT_LIST | wc -w) emfc 8Gb ports in target ready state: $EMFC_PORT_LIST"

for port in $EMFC_PORT_LIST
do
  tcli -e "port wiggle -p $port"
done > /dev/null

(set -x; sleep 60)

AVAIL_XRI_EVENTS=$(showeventlog -oneline -debug -min 3 -msg "Max xri: .* Avail xri:" | grep -v ^Time | \
    sed -e "s/.* Port //g" -e "s/ - .* Avail xri://g" -e "s/iocb: .*//g" -e "s/,//g"
)

if [ "$AVAIL_XRI_EVENTS" == "" ]; then
 echo "No 'Avail' xri events reported"
 exit
fi

echo "N:S:P  Avail_xri  Status"

XRI_AVAILABILITY=$(for emfc_port in $EMFC_PORT_LIST; do
    echo "$AVAIL_XRI_EVENTS" | grep -w $emfc_port | tail -n 1 | awk --non-decimal-data '{
      Avail_xri=$2
      if (Avail_xri < 1024) Status="Major"
      else if (Avail_xri < 2048) Status="Minor"
      else Status="Normal"

      printf "%s  %9d  %s\n", $1, $2, Status
    }'
done | sort -nk2)

echo "$XRI_AVAILABILITY"

echo -e "\nNote:\n- If a patch for xri depletion is installed now, reset each emfc 8Gb host port to make patch fully functional."
echo -e "- User can rest emfc 8Gb hba ports in the order below:\n"

echo "$XRI_AVAILABILITY" | while read port Avail_xri Status; do
  echo "controlport rst -f $port"
  echo "sleep 300"
done
