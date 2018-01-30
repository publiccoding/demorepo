#!/bin/bash
# vmware_PeerPersistence.sh: It suggests auto_failover option for VMware hosts in RC group.
# - It also finds mixed Persona hosts to avoid CLX issue during upgrade.
# - It helps to avoid issues similar to 134309.
# - This script is applicable when InServ is upgrading from 3.1.2.MU3 or 3.1.2.MU5.

Version=1.04

# Script Algorithm:
# - It works on live setup or insplore or STaTS config file or for given InServ#.
# - Fetches showversion_-b.out showrcopy_-d.out showvlun.out showhost_-d.out data
# - validates whether it is 3.1.2.x TPD setup.
# - Gets RC group name, Status, Role, Options and corresponding VV names for Primary/Secondary RC group from showrcopy_-d.out
# - It gets VVs host names from showvlun.out then maps host persona from showhost_-d.out.
# - If VMware and Non-VMware hosts are in same RC group then it reports an error.
# - If only VMware hosts are in RC group and options are not set with auto_failover then it suggests to set it.
# - If only Non-VMware hosts are in RC group and options set with auto_failover then it suggests to remove it.

ST_PATH=/share/st/scripts
STLATEST=$ST_PATH/stlatest
SHOWFIELD=$ST_PATH/showfield
BIN=/opt/tpd/bin
CLWAIT=$BIN/clwait
FILES="showversion_-b.out showrcopy_-d.out showvlun.out showhost_-d.out showlicense.out showvv_-d.out"
PP_PERSONA="VMware" # For 3.1.2.MU3/MU5 

TPD_VERSIONS="3.1.2.484|3.1.2.592"

SHOWVERSION="/tmp/showversion.out.$$"
SHOWRCOPY="/tmp/showrcopy_-d.out.$$"
SHOWVLUN="/tmp/showvlun.out.$$"
SHOWHOST="/tmp/showhost_-d.out.$$"
SHOWLICENSE="/tmp/showlicense.out.$$"
SHOWVV_D="/tmp/showvv_-d.out.$$"
export TPDLISTDOM=1

cleanup() {
    rm -f $SHOWVERSION $SHOWRCOPY $SHOWVLUN $SHOWHOST $SHOWLICENSE $SHOWVV_D
    exit
}

usage()
{
    echo -e "$0                            # For live setup or required files in current directory" >&2
    echo -e "$0 <-n InServ> [-w] [-v]      # For specific InServ. It looks into STaTS data" >&2
    echo -e "$0 <-f config_file> [-w] [-v] # STaTS config file\n" >&2

    echo -e "\t-n InServ      : STaTS database InServ#" >&2
    echo -e "\t-f config_file : STaTS config_file" >&2
    #echo -e "\t-s             : Skip TPD version checking" >&2 # Hidden option
    echo -e "\t-v             : For Verbose" >&2
    echo -e "\t-w             : log VV_WWN for each Volume" >&2
    echo -e "\nNote: If '$FILES' in current directory script parses them."

    exit 1
}

log_msg()
{
  local msg="$1"

  if [ "$msg" != "" ]; then
    echo -e "$msg" | grep -v "^$"
  fi
}

check_tpd_version()
{
  local File=$1

  if [ ! -f $File ]; then
    echo "ERROR: Unable open $File file" >&2
    exit 1
  fi

  local TPD=$(grep "Release version" $File | awk '{ print $3 }')
  echo $TPD | egrep -qw "$TPD_VERSIONS"
  if [ $? -ne 0 ]; then
    echo -e "ERROR: This script is not applicable for $TPD version.\n" >&2
    exit 1
  fi
}

skip_version_check=0
unset INSERV VERBOSE VV_WWN
while getopts n:f:svwh arg; do
    case "$arg" in
    n)   INSERV="$OPTARG";;
    f)   CONFIG="$OPTARG";;
    s)   skip_version_check=1;;
    v)   VERBOSE=1;;
    w)   VV_WWN=1;;
    h)   usage;;
    [?]) usage;;
    esac
done

echo -e "- You are using script version=$Version on dated $(date)\n"

eval `$CLWAIT --bash 2>/dev/null`

if [[ "$mynode" != "" && "$master" != "" && "$integrated" != "" ]]; then
  showsysmgr | grep -q "System is up and running"
  if [ $? -ne 0 ]; then
    echo "ERROR: sysmgr is not started" >&2
    (set -x; showsysmgr -d)
    exit 1
  fi

  #trap cleanup INT QUIT TERM
  trap cleanup 0 1 2 3 4 5 6 7 9 15       # handle signals

  ( set -x
    $BIN/showversion -b > $SHOWVERSION
    $BIN/showrcopy -d > $SHOWRCOPY
    $BIN/showvlun > $SHOWVLUN
    $BIN/showhost -d > $SHOWHOST
    $BIN/showlicense > $SHOWLICENSE
    $BIN/showvv -d > $SHOWVV_D
  )
elif [[ "$INSERV" != "" || "$CONFIG" != "" ]]; then
  #trap cleanup INT QUIT TERM
  trap cleanup 0 1 2 3 4 5 6 7 9 15       # handle signals
  if [ "$CONFIG" == "" ]; then
    CONFIG=$($STLATEST -n $INSERV -f config)
  fi
  if [[ "$CONFIG" != "" && -f $CONFIG ]]; then
    cat $CONFIG | sed -e "1,/A name=showversion>/d" -e "/A href=/,$ d" > $SHOWVERSION
    cat $CONFIG | sed -e "1,/A name=showrcopy>/d" -e "/A href=/,$ d" > $SHOWRCOPY
    cat $CONFIG | sed -e "1,/A name=showvlun>/d" -e "/A href=/,$ d" > $SHOWVLUN
    cat $CONFIG | sed -e "1,/A name=showhost>/d" -e "/A href=/,$ d" > $SHOWHOST
    cat $CONFIG | sed -e "1,/A name=showlicense>/d" -e "/A href=/,$ d" > $SHOWLICENSE
    cat $CONFIG | sed -e "1,/A name=showvvd>/d" -e "/A href=/,$ d" > $SHOWVV_D
  fi
elif [ $(ls $FILES 2>/dev/null | wc -l) == 4 ]; then
    SHOWVERSION="showversion_-b.out"
    SHOWRCOPY="showrcopy_-d.out"
    SHOWVLUN="showvlun.out"
    SHOWHOST="showhost_-d.out"
    SHOWLICENSE="showlicense.out"
    SHOWVV_D="showvv_-d.out"
else
    echo -e "ERROR: $FILES not found in current directory.\n" >&2
    usage
fi

if [ $skip_version_check -ne 1 ]; then
  check_tpd_version $SHOWVERSION
fi

RCGrpCnt=0
cnt=1
log_cnt=1

while read grpName grpStatus grpRole grpMode grpOptions Volumes ; do
   ((RCGrpCnt++))
   unset RCMSG VOLMSG NOHOSTMSG PMSG
   RCMSG=$(echo -e "$cnt) RCGroup=$grpName Status=$grpStatus Role=$grpRole Mode=$grpMode Options=$grpOptions")

   if [ "$VV_WWN" != "" ]; then
	VOLMSG=$(egrep -w "$Volumes" $SHOWVV_D | awk '{ printf "VV=%s VV_WWN=%s\n", $2, $11 }')
   else
	VOLMSG=$(echo "Volumes=$(echo $Volumes | sed -e "s/|/ /g")")
   fi

   Hosts=$(egrep -w "$Volumes" $SHOWVLUN | awk '{ print $4 }' | sort -u | xargs | sed -e "s/ /|/g")
   Persona=""
   if [ "$Hosts" != "" ]; then
     Persona=$(egrep -w "$Hosts" $SHOWHOST | awk '{ print $4 }' |sort -u)
   else
       NOHOSTMSG=$(echo "INFO: Volumes are not mapping to any hosts")
   fi

   NonVMware=0
   personaCnt=0
   for persona in $Persona
   do
     echo $persona | grep -qw "$PP_PERSONA"
     if [ $? -ne 0 ]; then
       NonVMware=1 # Non-VMware host is in RC group
     fi
     HostList=$(egrep -w "$Hosts" $SHOWHOST | awk '{ print $2, $4 }' | sort -u | grep -w $persona | awk '{ print $1 }')
     PMSG="$PMSG\n"$(echo "$persona" $HostList | awk '
		  { 
		    printf "%-14s Hosts=", $1
		    j=1
		    for(i=2; i<=NF; i++) {
		      if (j>1) printf " "
		      if (j%10==0) printf "\n%21s", " "
		      printf "%s", $i
		      j++
		    }
		  }
		  END { printf "\n" }
		')
     ((personaCnt++))
   done

   autoFailover=0
   echo $Persona | grep -qw "$PP_PERSONA"
   if [ $? -eq 0 ]; then
     autoFailover=1 # VMware host is in RC group
   fi

   Msg=""
   log=0
   echo $grpOptions | grep -qw auto_failover
   AFOpt=$? # 0: auto_failover is in Options; !0: auto_failover is not in Options

   if [ $NonVMware -ne 0 ]; then # If Non-VMware host is in RC group
     if [[ $AFOpt -eq 0 || $autoFailover -eq 1 ]]; then # Any TRUE
       Msg="--- ERROR: Non-VMware hosts in same RC group, suggested to exclude them --"
       log=1
     fi

     if [[ $AFOpt -ne 0 && $autoFailover -ne 1 ]]; then # Both FLASE
       Msg="Passed: No action"
     fi
   fi

   if [ $NonVMware -eq 0 ]; then # Only VMware hosts are in RC group
     if [[ $AFOpt -eq 0 && $autoFailover -eq 1 ]]; then
       Msg="Passed: No action"
     fi

     if [[ $AFOpt -ne 0 && $autoFailover -ne 1 ]]; then
       Msg="Passed: No action"
     fi

     if [[ $AFOpt -ne 0 && $autoFailover -eq 1 ]]; then
       Msg="+++ ERROR: Must add auto_failover policy in RC group options +++"
       log=1
     fi

     if [[ $AFOpt -eq 0 && $autoFailover -ne 1 ]]; then
       Msg="--- ERROR: Remove auto_failover policy from RC group options ---"
       log=1
     fi
   fi

   if [ $log -eq 1 ]; then
	((log_cnt++))
   fi

   if [[ $log -eq 1 || "$VERBOSE" != "" ]]; then
     log_msg "$RCMSG"
     log_msg "$VOLMSG"
     log_msg "$NOHOSTMSG"
     log_msg "$PMSG"
     echo "$Msg"
     echo
     ((cnt++))
   fi
done < <(
  cat $SHOWRCOPY | sed -e "1,/Group Information/d" | grep "[A-Z]" | awk '
  BEGIN { volflag=0; Volumes="" }
  /^Name .* ID .*Target / {
#	if ((Volumes != "") && match(grpRole, "Primary") == 1 && match(grpMode, "Sync") == 1) # Commenting to log any Role
	if ((Volumes != "") && match(grpMode, "Sync") == 1)
	  print grpName, grpStatus, grpRole, grpMode, grpOptions, Volumes
	getline line
	$0=line
	grpName=$1
	grpStatus=$5
	grpRole=$6
	grpMode=$7
	if (NF > 7) grpOptions=$NF
	else grpOptions="None"
	volflag=0
  }

  /LocalVV .*ID .*RemoteVV/ {
	volflag=1
	Volumes=""
  }

  {
    if (volflag && $1 != "LocalVV" && NF>5) {
      if (Volumes == "") { Volumes=$1 }
      else { Volumes=Volumes"|"$1 }
    }
  } END {
#     if ((Volumes != "") && match(grpRole, "Primary") == 1 && match(grpMode, "Sync") == 1) # Commenting to log any Role
     if ((Volumes != "") && match(grpMode, "Sync") == 1)
       print grpName, grpStatus, grpRole, grpMode, grpOptions, Volumes
    }'
)

if [ $log_cnt -ne 1 ]; then
  egrep -q "Peer Persistence|Golden License" $SHOWLICENSE
  if [ $? -ne 0 ]; then
    echo -e "\nERROR: InServ doesn't have 'Peer Persistence' license."
    echo "Note: Upgrade may cause volumes transition to non-ALUA presentations, STANDBY paths will no longer be available. It can cause ESX to lose connectivity."
  fi
fi
exit

if [[ $RCGrpCnt -ne 0 && $cnt -eq 1 ]]; then
  echo -e "\n- All $RCGrpCnt RC groups passed peer persistence checking"
fi
