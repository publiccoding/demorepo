#!/bin/bash
# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
#
# reset_disks_to_avoid_pathsick.sh: Reset disks to avoid TE_PATHSICK
#
# - Defect(s) it works around: 125677
#
# On how script works:
# - It gets PD list then for each PD then it runs controlpd clearerr
# - It sleeps for 7 minutes before checking TE_PATHSICK events for last 5 minutes
# - If TE_PATHSICK events are seen above threshold then script checks whether issue is with single disk port or multi-disk port.
# - If issue is with single disk port then suggests to reset specific ports.
# - If issue is with multi-disk port then asks to contact support.

Version=1.00

# For EGA specify GA and EMUx specify MUx
TPD_VERSIONS="3.1.2|3.1.3|3.2.1|3.2.2"

# Failure Codes (or) exit values from scripts
PASS=0        # Passed
FAILPERM=1    # Failure, permanent
FAILTEMP=2    # Failure, temporary
FAILWARN=3    # Warning (only allowed during precheck and postupgrade)
FAILNOTRUN=4  # Failed, Not Yet Run
FAILNA=5      # Failed, Not Applicable
FAILOTHER=127 # Failed, other unknown failure

OUT_CMDOUTPUT="%s"
OUT_USERACCEPTEDWAD="User reply='%s'. User accepted %s workaround. Applying workaround."
OUT_NOT_APPLYINGWAD="User reply='%s'. Not applying %s workaround."
OUT_TE_PATHSICK_NOT_SEEN="%s: TE_PATHSICK events were not seen in last %s minutes. Result: Passed"
OUT_TE_PATHSICK_EVTS_BELOW_THRESHOLD="\n%s: TE_PATHSICK events are below threshold %d in last %d minutes. Result: Passed"
ERR_FUNC_INSUFF_ARGS="%s: %s() insufficient or more number of arguments passed. Expected: %d, Received: %d"
ERR_SCRIPT_NA="%s: Script is not applicable for %s release or version."
ERR_SYSMGR_NOT_STARTED="%s: sysmgr is not started."
ERR_NON_SAS_CONFIG="%s: This StoreServ does not have SAS HBA ports"
ERR_NOT_ALL_NODES_INTEGRATED="%s: Not all nodes integrated. clwait: $(clwait 2>/dev/null)"
CA_TE_PATHSICK_EVTS_ON_MULTI_DISK_PORTS="\n%s: TE_PATHSICK events seen on multiple %s node disk port(s). To resolve them Consult Support\n"
CA_TE_PATHSICK_HBA_PORT_RESET="\n%s: %s node disk port(s) reset can help in resolving TE_PATHSICK events\n"

output()
{
    arg=("${@:2}")
    local message_format="${!1}"
    printf "$message_format\n" "${arg[@]}"
}

usage()
{
  local prog=$(basename $0)

  echo -e "Usage: $prog --install"
  echo -e "       $prog --check"
  echo -e "       $prog --verify\n"

  echo "--install   : It applies the workaround"
  echo "--check     : Checks whether it is applicable to current system config"
  echo "--verify    : It checks current status"

  exit $FAILPERM
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
  local partition=$2

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

is_it_sas_config()
{
  showport -nohdtot | grep -qw "SAS"
  if [ $? -ne 0 ]; then
      output ERR_NON_SAS_CONFIG $(basename $0 .sh)
      exit $FAILNA
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
        printf "%s\n" "Unrecognized input '$reply'"
    fi
  done
}

reset_disks_to_avoid_pathsick()
{
  local opt=$1
  local evt_min=15
  local factor_per_min=2
  local description="Clears the disks TE_PATHSICK error"
  local evtlog_pattern="scsi_cmnd_retry: pd .* opcode .* rval 0x31"
  local controlpd_failed_list=""

  if [ $opt == "--install" ]; then
    pd_list=$(showpd -nohdtot | egrep -v "^\---|no_valid_ports|\?|No PDs listed" | awk '{print $1}')

    local wwn_list=$(showpd -nohdtot -i | grep -v "?")
    for pd in $pd_list; do
      local wwn=$(echo "$wwn_list" | awk -v pd=$pd '($1==pd) { print $4 }')
      local data=$(echo -e "\nWorking on pd::wwn -> $pd::$wwn")
      output OUT_CMDOUTPUT "$data"
      if [ "${wwn}" != "" ]; then
        controlpd clearerr ${wwn}
        if [ $? -ne 0 ]; then
          controlpd_failed_list="${controlpd_failed_list} $pd"
        fi
      fi
    done
    if [ "$controlpd_failed_list" != "" ]; then
      output ERR_CONTROLPD_CLEARERR_FAILED ${FUNCNAME[0]}
      output OUT_CMDOUTPUT "$controlpd_failed_list"
    fi
  fi

  evtlog=$(showeventlog -oneline -debug -min $evt_min -nohdtot -msg "$evtlog_pattern" | egrep -v "No event matched your criteria|^Time")

  if [ "$evtlog" == "" ]; then
      output OUT_TE_PATHSICK_NOT_SEEN ${FUNCNAME[0]} $evt_min
      return $PASS
  fi

  if [ $opt == "--install" ]; then
    evt_min=5
    printf "\n%s: Recovery from TE_PATH_SICK events can take up to %s minutes\n\n" ${FUNCNAME[0]} $((evt_min+2))
    sleep $(((evt_min+2)*60))
    evtlog=$(showeventlog -oneline -debug -min $evt_min -nohdtot -msg "$evtlog_pattern" | egrep -v "No event matched your criteria|^Time")

    if [ "$evtlog" == "" ]; then
      output OUT_TE_PATHSICK_NOT_SEEN ${FUNCNAME[0]} $evt_min
      return $PASS
    fi
  fi

  minimum_event_count=$((evt_min * factor_per_min))

  evtlog_data_cnt=$(echo "$evtlog" |\
       sed -e "s/.*scsi_cmnd_retry: pd //g" -e "s/ - opcode.*//g" -e "s/pd//g" -e "s/port//g" -e "s/on//g" | sort | uniq -c |\
       awk '{ print $2, $3, $4, $1 }'
  )

  # If events are above threshold then indicate them with "!"
  echo "$evtlog_data_cnt" | awk -v minimum_event_count=$minimum_event_count '
    BEGIN { printf "-pd-id- disk-port N:S:P event-count\n" }
    {
        if ($4 >= minimum_event_count)
           printf "pd %4s port %s   %s %10s!\n", $1, $2, $3, $4
        else
           printf "pd %4s port %s   %s %10s\n", $1, $2, $3, $4
    }'

  # Get the disk port list above TE_PATHSICK event count threshold
  evtlog_data_cnt_filtered=$(echo "$evtlog_data_cnt" | awk -v minimum_event_count=$minimum_event_count '($NF >= minimum_event_count)')

  # If all events are below threshold
  if [ "$evtlog_data_cnt_filtered" == "" ]; then
      output OUT_TE_PATHSICK_EVTS_BELOW_THRESHOLD ${FUNCNAME[0]} $minimum_event_count $evt_min
      return $PASS
  fi

  # Code below will be executed when TE_PATHSICK events are above threshold

  nsp_list=($(echo "$evtlog_data_cnt_filtered" | awk '{ print $3 }' | sort -u))

  nsp_reset_exclude_list=""
  nsp_reset_list=""
  for nsp in ${nsp_list[@]}; do
    NSP_PATTERN=$(echo $nsp | awk -F ":" '{
        nsp_node=$1
        nsp_slot=$2
        nsp_port=$3

        if ($1%2 == 0) nsp_node_pair=$1+1
        else nsp_node_pair=$1-1

        if ($3%2 == 1) nsp_port_pair=$3+1
        else nsp_port_pair=$3-1

        printf "[%s%s]:%s:[%s%s]\n", nsp_node, nsp_node_pair, nsp_slot, nsp_port, nsp_port_pair
    }')

    # Get the disk port count based on $NSP_PATTERN
    DiskPortCnt=$(echo "$evtlog_data_cnt_filtered" | egrep "$NSP_PATTERN" | awk '{ print  $2 }' | sort -u | wc -l)

    # If TE_PATHSICK issue > 1 disk port then add nsp to $nsp_reset_exclude_list
    if [ $DiskPortCnt -gt 1 ]; then
        nsp_reset_exclude_list=${nsp_reset_exclude_list:+$nsp_reset_exclude_list","}
        nsp_reset_exclude_list=${nsp_reset_exclude_list}$nsp
        continue
    fi

    # If TE_PATHSICK issue limited to one of the disk port only then add it to $nsp_reset_list
    nsp_reset_list=${nsp_reset_list:+$nsp_reset_list","}
    nsp_reset_list=${nsp_reset_list}$nsp
  done

  if [ "$nsp_reset_exclude_list" != "" ]; then
      output CA_TE_PATHSICK_EVTS_ON_MULTI_DISK_PORTS ${FUNCNAME[0]} $nsp_reset_exclude_list
  fi

  if [ "$nsp_reset_list" != "" ]; then
      output CA_TE_PATHSICK_HBA_PORT_RESET ${FUNCNAME[0]} $nsp_reset_list
  fi

  return $FAILPERM
}

if [ $# -ne 1 ]; then
  usage
fi

option=$1

case $option in
  "--install")
    ;;

  "--verify")
    ;;

  "--check")
    is_it_sas_config
    exit $PASS
    ;;
  *)echo -e "ERROR: Invalid option '$option' specified.\n"
    usage
    ;;
esac

$(clwait --bash)

get_script_version $0 $*

is_sysmgr_up

check_tpd_version "$TPD_VERSIONS"

isallnodesintegrated

is_it_sas_config

reset_disks_to_avoid_pathsick $option

rval=$?
rval=${rval:=$PASS}
exit $rval
