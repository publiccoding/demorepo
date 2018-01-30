#!/bin/bash
# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
#
# reset_pathsick_sas_ports.sh: Reset SAS ports if TE_PATHSICK events reported in event log
# - Based on "scsi_cmnd_retry: pd .. port .. on N:S:P - opcode 0x.. rval 0x31" events, it takes corrective action
# - Defect(s) it works around: 125677
# - Reapply the work around, if node rescue takes place on same setup
#
# On how script works:
# - Check last 15 minutes for TE_PATH_SICK events.
# - If events are below threshold or no events found then it says Passed.
# - If events are above threshold and port reset causes write IO failures then it says Consult Support.
# - If events are above threshold and port reset can resolve the problem then script lists which ports should be reset.
# - If we use --install option then script will reset port-by-port.
# - Expected time for recovery: (<Number of ports to be reset> * 1 + 7) minutes
#   * To reset each port script can 1 minute
#   * Script sleeps for 7 more minutes after all required ports are rset one after other.
# - Script checks last 5 minutes for TE_PATH_SICK events. If issue is still seen then it says Consult Support.

Version=1.00
TPD_VERSIONS="3.1.2|3.1.3|3.2.1|3.2.2.GA|3.2.2.MU1"

evt_min=15
factor_per_min=2

EVTLOG_PATTERN="scsi_cmnd_retry: pd .* opcode .* rval 0x31"

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
OUT_TE_PATHSICK_NOT_SEEN="%s: TE_PATHSICK events were not seen in last %s minutes. Result: Passed"
OUT_TE_PATHSICK_EVTS_BELOW_THRESHOLD="\n%s: TE_PATHSICK events are below threshold %d in last %d minutes. Result: Passed"
OUT_TE_PATH_SICK_RECOVERY_TIME="%s: %s node disk port(s) reset and recovery from TE_PATH_SICK events can take up to %s minutes"
OUT_HBA_PORT_RESET_TIME="%s: Resetting %s node disk  port. It can take up to %s seconds"
OUT_HBA_PORT_RESET_SUCCESSFUL="\n%s: Successfully reset %s node disk port(s)."
OUT_WAIT_RECHECK_MIN="%s: Waiting %s minutes before recheck"
ERR_FUNC_INSUFF_ARGS="%s: %s() insufficient or more number of arguments passed. Expected: %d, Received: %d"
ERR_SCRIPT_NA="%s: Script is not applicable for %s release or version."
ERR_SCRIPT_NA_MODEL="%s: Script is not applicable for %s StoreServ Model."
ERR_SYSMGR_NOT_STARTED="%s: sysmgr is not started."
ERR_NON_SAS_CONFIG="%s: This StoreServ does not have SAS HBA ports"
ERR_NOT_ALL_NODES_INTEGRATED="%s: Not all nodes integrated. clwait: $(clwait 2>/dev/null)"
ERR_HBA_PORT_RESET_FAILED="%s: Reset failed on %s node disk port"
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
  local PROG=$(basename $0)

  echo -e "Usage: $PROG --install"
  echo -e "       $PROG --verify\n"

  echo "--install   : It applies the workaround. Before installing, it asks for user confirmation."
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

reset_sas_port_on_pathsick()
{
  local OPT=$1

  if [ "$OPT" == "--file" ]; then
      local FILE=$2
      local tpd_release_version=$(grep "Release version" $FILE)

      translate_tpd_release_version "$tpd_release_version" | egrep -qw "$TPD_VERSIONS"
      if [ $? -ne 0 ]; then
        exit $FAILNA
      fi

      local t_start=$(date -d "$(sed -e "1,/^Time/d" $FILE | head -n 1 | awk '{ print $1, $2 }')" "+%s" 2>/dev/null)
      local t_end=$(date -d "$(sed -e "1,/^Time/d" $FILE | tail -n 10 | head -1 | awk '{ print $1, $2 }')" "+%s" 2>/dev/null)
      if [[ "$t_start" == "" || "$t_end" == "" ]]; then
        exit $FAILPERM
      fi

      evt_min=$(((t_end - t_start)/60 + 1))
      EVTLOG=$(grep "$EVTLOG_PATTERN" $FILE)
  else
      EVTLOG=$(showeventlog -oneline -debug -min $evt_min -nohdtot -msg "$EVTLOG_PATTERN" | egrep -v "No event matched your criteria|^Time")
  fi

  minimum_event_count=$((evt_min * factor_per_min))

  if [ "$EVTLOG" == "" ]; then
      output OUT_TE_PATHSICK_NOT_SEEN ${FUNCNAME[0]} $evt_min
      return $PASS
  fi

  EVTLOG_DATA_CNT=$(echo "$EVTLOG" |\
       sed -e "s/.*scsi_cmnd_retry: pd //g" -e "s/ - opcode.*//g" -e "s/pd//g" -e "s/port//g" -e "s/on//g" | sort | uniq -c |\
       awk '{ print $2, $3, $4, $1 }'
  )

  # If events are above threshold then indicate them with "!"
  echo "$EVTLOG_DATA_CNT" | awk -v minimum_event_count=$minimum_event_count '
    BEGIN { printf "-pd-id- disk-port N:S:P event-count\n" }
    {
        if ($4 >= minimum_event_count)
           printf "pd %4s port %s   %s %10s!\n", $1, $2, $3, $4
        else
           printf "pd %4s port %s   %s %10s\n", $1, $2, $3, $4
    }'

  # Get the disk port list above TE_PATHSICK event count threshold
  EVTLOG_DATA_CNT_FILTERED=$(echo "$EVTLOG_DATA_CNT" | awk -v minimum_event_count=$minimum_event_count '($NF >= minimum_event_count)')

  # If all events are below threshold
  if [ "$EVTLOG_DATA_CNT_FILTERED" == "" ]; then
      output OUT_TE_PATHSICK_EVTS_BELOW_THRESHOLD ${FUNCNAME[0]} $minimum_event_count $evt_min
      return $PASS
  fi

  # Code below will be executed when TE_PATHSICK events are above threshold

  nsp_list=($(echo "$EVTLOG_DATA_CNT_FILTERED" | awk '{ print $3 }' | sort -u))

  NSP_RESET_EXCLUDE_LIST=""
  NSP_RESET_LIST=""
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
    DiskPortCnt=$(echo "$EVTLOG_DATA_CNT_FILTERED" | egrep "$NSP_PATTERN" | awk '{ print  $2 }' | sort -u | wc -l)

    # If TE_PATHSICK issue > 1 disk port then add nsp to $NSP_RESET_EXCLUDE_LIST
    if [ $DiskPortCnt -gt 1 ]; then
        NSP_RESET_EXCLUDE_LIST=${NSP_RESET_EXCLUDE_LIST:+$NSP_RESET_EXCLUDE_LIST","}
        NSP_RESET_EXCLUDE_LIST=${NSP_RESET_EXCLUDE_LIST}$nsp
        continue
    fi

    # If TE_PATHSICK issue limited to one of the disk port only then add it to $NSP_RESET_LIST
    NSP_RESET_LIST=${NSP_RESET_LIST:+$NSP_RESET_LIST","}
    NSP_RESET_LIST=${NSP_RESET_LIST}$nsp
  done

  if [ "$NSP_RESET_EXCLUDE_LIST" != "" ]; then
      output CA_TE_PATHSICK_EVTS_ON_MULTI_DISK_PORTS ${FUNCNAME[0]} $NSP_RESET_EXCLUDE_LIST
  fi

  if [ "$NSP_RESET_LIST" != "" ]; then
        output CA_TE_PATHSICK_HBA_PORT_RESET ${FUNCNAME[0]} $NSP_RESET_LIST
  fi

  if [[ "$OPT" != "--install" || "$NSP_RESET_LIST" == "" ]]; then
      return $FAILPERM
  fi

  local count=$(echo $NSP_RESET_LIST | sed -e "s/,/ /g" | wc -w)

  output OUT_TE_PATH_SICK_RECOVERY_TIME ${FUNCNAME[0]} $NSP_RESET_LIST $((count + 7))

  GetConfirmation OUT_CNF_NODE_DISK_PORT_RESET ${FUNCNAME[0]}
  if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
      return $FAILNOTRUN
  fi

  # Code below will reset each SAS port which are in $NSP_RESET_LIST
  rval=$PASS
  for nsp in $(echo $NSP_RESET_LIST | sed -e "s/,/ /g"); do
      prev_nsp_state=$(showport -nohdtot $nsp | awk '{ print $3 }')

      output OUT_HBA_PORT_RESET_TIME ${FUNCNAME[0]} $nsp 60
      TPDFORCE_OVERRIDE=1 controlport rst -l -f $nsp > /dev/null

      if [ "$prev_nsp_state" == "ready" ]; then
          for cnt in 1 2 3; do
            sleep 10
            rval=$PASS
            nsp_state=$(showport -nohdtot $nsp | awk '{ print $3 }')
            if [ "$nsp_state" != "ready" ]; then
                rval=$FAILPERM
            fi
          done
      fi

      if [ $rval -ne $PASS ]; then
           output ERR_HBA_PORT_RESET_FAILED ${FUNCNAME[0]} $nsp
           break
      fi

      sleep 15
  done

  if [ $rval -ne $PASS ]; then
      return $rval
  fi

  output OUT_HBA_PORT_RESET_SUCCESSFUL ${FUNCNAME[0]} $NSP_RESET_LIST

  if [ "$NSP_RESET_EXCLUDE_LIST" != "" ]; then
      return $FAILPERM
  fi

  evt_min=5
  output OUT_WAIT_RECHECK_MIN ${FUNCNAME[0]} $((evt_min+2))
  sleep $((7*60)) # Wait here for 2+5=7 minutes

  reset_sas_port_on_pathsick --verify
}

OPTION=$1

case $OPTION in
  "--install")  OPT="--install"
                ;;

  "--verify")   OPT="--verify"
                ;;

  "--file")     OPT="--file"
                FILE=$2
	        if [[ "$FILE" == "" || ! -f $FILE ]]; then
		  echo "ERROR: Unable to open '$FILE'"
		  exit $FAILPERM
                fi

	        reset_sas_port_on_pathsick --file $FILE
	        rval=$?
	        exit $rval
                ;;

  *)            echo -e "ERROR: Invalid option '$OPTION' specified.\n"
		usage
                ;;
esac

$(clwait --bash)

get_script_version $0 $*

is_sysmgr_up

isallnodesintegrated

is_it_sas_config

reset_sas_port_on_pathsick $OPT

rval=$?
rval=${rval:=$PASS}
exit $rval
