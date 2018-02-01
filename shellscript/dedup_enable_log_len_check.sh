#!/bin/bash
# dedup_enable_log_len_check.sh:  Script generates /etc/init.d/tpd_enable_log_len_check file
# - It enables log len check to limit max DDS garbage collection to 1TB for given ddcscan run
# - Defect(s) it works around: 146519
# - Reapply the work around, if node rescue takes place on same setup
# - init script will be automatically removed during TPD upgrade

Version=1.01

TPD_VERSIONS="3.2.2.GA"
SCRIPT=dedup_enable_log_len_check.sh
LOGNAME="/var/log/tpd/${SCRIPT}.log"

ENVIRONMENT=/etc/environment
INITDIR=/etc/init.d
RCDIR=/etc/rc2.d
ALPHABET=({a..z} {A..Z})
INFORMATIONAL=5 # To post events
LOGNAME="/var/log/tpd/sdt_inqC0_in_kernel.out"

hex2decimal()
{
  local val=$1

  echo $val | awk --non-decimal-data '{ printf "%d\n", $1 }'
}

GetConfirmation()
{
  local MSG="$1"

  unset GETCONFIRMATION
  echo -e "$MSG"
  while true ; do
    echo -e -n "select y=yes n=no q=quit : "
    read reply
    if [ $reply == "y" ]; then
        GETCONFIRMATION="APPLY-IT"
        echo
        break
    elif [[ $reply == "q" || $reply == "n" ]]; then
        echo "- As per user not applying this workaround."
        GETCONFIRMATION="SKIP-IT"
        break
    else
        echo "Unrecognized input \"$reply\""
    fi
  done
}

get_xvar_value()
{
  local TPDVARTYPE=$1
  local TPDVARNAME=$2
  local TPDVARSIZE=$3
  local DEFAULTVAL=$4
  local NEWVAL=$5

  if [[ "$FS" != "" && "$OPTION" != "--uninstall" ]]; then # It is applicable when altroot option is not specified or for live setup only
    return
  fi

  if [ "$TPDVARTYPE" != "kernel" ]; then
    tcli -e "$TPDVARTYPE list" | grep -qw $TPDVARNAME
    if [ $? -eq 0 ]; then # Checking tpd variable exists in current running TPD?
       tcli -e "$TPDVARTYPE show -n $TPDVARNAME"
    fi
  else
    echo -n "$TPDVARNAME = "
    for node in $(seq 0 7); do
      if (( (online & (1 << node)) == 0 )); then # Check whether node is online
        continue
      fi
      echo -n "kernel$node:$(showmemval kernel$node none $TPDVARSIZE 1 $TPDVARNAME | awk '{ print $NF }') "
    done
    echo
  fi
}

# It sets given [kmd]var or kernel global during node boot-up
set_tpd_variable_during_init()
{
  local OPT="$1"
  local TPDVARTYPE="$2"
  local TPDVARNAME="$3"
  local TPDVARSIZE="$4"
  local DEFAULTVAL=$(hex2decimal $5)
  local NEWVAL=$(hex2decimal $6)
  local DEFECTS="$7"
  local DESCRIPTION="$8"

  local INITSCRIPT=tpd_$TPDVARNAME
  ALPHCNT=0

  if [ "$OPT" == "--install" ]; then

    GetConfirmation "\nDo you like to apply work-around thru init script?"
    if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
	return
    fi

    generate_initscript_file $TPDVARTYPE $TPDVARNAME $TPDVARSIZE $DEFAULTVAL $NEWVAL "$DEFECTS" "$DESCRIPTION" > $INITSCRIPT.$$
    chmod +x $INITSCRIPT.$$

    unset node_list
    for node in $(seq 0 7); do
      if (( (online & (1 << node)) == 0 )); then # Check whether node is online
        continue
      fi

      if [ "$FS" == "" ]; then # To apply the workaround in live system; NA for "altroot"
	# Terminate earlier pid to install latest bits
        rsh node${node} "ps -C $INITSCRIPT --no-headers -o pid= | xargs kill 2>/dev/null"
      fi

      node_list=${node_list:+$node_list","}
      node_list="${node_list}node$node"
      rcp ${INITSCRIPT}.$$ node${node}:${FS}${INITDIR}/${INITSCRIPT}
      rsh node${node} "$CHROOT update-rc.d -f ${INITSCRIPT} remove 2>&1 >/dev/null" 2>&1 > /dev/null
      rsh node${node} "$CHROOT update-rc.d ${INITSCRIPT} defaults 2>&1 >/dev/null" 2>&1 >/dev/null
      if [ "$FS" == "" ]; then # To apply the workaround in live system; NA for "altroot"
        echo "Node ${node}:"
        rsh node${node} ${INITDIR}/${INITSCRIPT} start
      fi
    done
    rm -f ${INITSCRIPT}.$$

    message="Successfully installed ${FS}${INITDIR}/${INITSCRIPT} file on $node_list."
    em_test --severity=$INFORMATIONAL --post="$INITSCRIPT: $message" >/dev/null
    echo -e "\n- RESULT: $message\n"

  elif [ "$OPT" == "--uninstall" ]; then
      echo "(${ALPHABET[ALPHCNT++]}) Terminating $INITSCRIPT process on all the nodes then restoring $TPDVARNAME to default"
      onallnodes "(if [ -f $INITDIR/$INITSCRIPT ]; then
                   $INITDIR/$INITSCRIPT stop
                 fi
                )" > /dev/null

	echo -e "- Removing $INITSCRIPT script from each node\n"
	local FILESLIST=$(onallnodes "ls -l ${FS}${INITDIR}/${INITSCRIPT} 2>/dev/null" | grep ${INITSCRIPT})
	onallnodes "$CHROOT update-rc.d -f ${INITSCRIPT} remove > /dev/null" > /dev/null
	onallnodes "rm -f ${FS}${INITDIR}/${INITSCRIPT}" > /dev/null

        if [ "$TPDVARTYPE" != "kernel" ]; then # Setting variables to default values
          tcli -e "$TPDVARTYPE set -n $TPDVARNAME -v $DEFAULTVAL" > /dev/null
        else
          for node in $(seq 0 7); do
            if (( (online & (1 << node)) == 0 )); then # Check whether node is online
              continue
            fi
            setmemval kernel$node write $TPDVARSIZE $TPDVARNAME $DEFAULTVAL > /dev/null
          done
        fi

	if [ "$FILESLIST" != "" ]; then
          message="Removed $INITSCRIPT init script, current $(get_xvar_value $TPDVARTYPE $TPDVARNAME $TPDVARSIZE $DEFAULTVAL $NEWVAL)"
          em_test --severity=$INFORMATIONAL --post="$message" >/dev/null
          echo -e "- RESULT: $message\n"
	fi
  fi # End of - "$OPT" == "--install"

  echo -e "- Verifying $INITSCRIPT init script:\n"

  echo -e "(${ALPHABET[ALPHCNT++]}) $INITSCRIPT init/rc script files list:"
  onallnodes "(ls -l ${INITDIR}/${INITSCRIPT} /altroot${INITDIR}/${INITSCRIPT} \
      ${RCDIR}/S*${INITSCRIPT} /altroot${RCDIR}/S*${INITSCRIPT} 2>/dev/null)"

  if [[ "$TPDVARTYPE" != "kernel" && "$TPDVARTYPE" != "kvar" ]]; then
    echo -e "(${ALPHABET[ALPHCNT++]}) Checking whether ${INITSCRIPT} script process running?"
    onallnodes "ps -f -w -C $INITSCRIPT --no-header"
  fi

  echo -e "(${ALPHABET[ALPHCNT++]}) Current $TPDVARNAME ($TPDVARTYPE) value: (Default: $DEFAULTVAL, Work-around: $NEWVAL)"
  get_xvar_value $TPDVARTYPE $TPDVARNAME $TPDVARSIZE $DEFAULTVAL $NEWVAL

  echo -e "\n(${ALPHABET[ALPHCNT++]}) Event log messages with ${INITSCRIPT} pattern in last one hour:"
  (set -x; showeventlog -min 60 -debug -oneline -msg "${INITSCRIPT}")
}

# It creates script to tune [kmd]var during node boot-up
generate_initscript_file()
{
  local TPDVARTYPE="$1"
  local TPDVARNAME="$2"
  local TPDVARSIZE="$3"
  local DEFAULTVAL=$4
  local NEWVAL=$5
  local DEFECTS="$6"
  local DESCRIPTION="$7"

  local INITSCRIPT=tpd_$TPDVARNAME
  local FUNC=set_${TPDVARTYPE}_variable_during_init # It is used in init script

  cat << EOF # Import variables from main script or function to here-document
#!/bin/bash
# $INITDIR/$INITSCRIPT: It sets $TPDVARNAME=$NEWVAL to avoid '$DESCRIPTION'
# - It is applicable in TPD=$TPD
# - Defect(s) it works around: $DEFECTS
# - Script will be automatically removed in next TPD upgrade.

Version=$Version # Version of the script

### BEGIN INIT INFO
# Provides:         $INITSCRIPT
# Required-Start:   tpdinit
# Required-Stop:
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: To avoid '$DESCRIPTION'
### END INIT INFO

# Exporting environment variables
. $ENVIRONMENT

TPDVARTYPE=$TPDVARTYPE
TPDVARNAME=$TPDVARNAME
TPDVARSIZE=$TPDVARSIZE
DEFAULTVAL=$DEFAULTVAL
NEWVAL=$NEWVAL
DESCRIPTION="$DESCRIPTION"

SLEEP_TIME=300
MAJOR=2
INFORMATIONAL=5

$FUNC()
{
EOF

case $TPDVARTYPE in # Is it kvar, mvar, dvar, kernel (For Kernel global variables)
  kernel)
  cat << "KERNEL_EOF"
    if [[ $integrated_mask -ne 0 ]]; then # This node is in cluster

        setmemval kernel$mynode write $TPDVARSIZE $TPDVARNAME $NEWVAL
        em_test --severity=$INFORMATIONAL --post="$SCRIPT: Setting $TPDVARNAME=$NEWVAL"
	exit
    fi  # End of $integrated_mask
KERNEL_EOF
 ;;

  kvar)
  cat << "KVAR_EOF"
    if [[ $integrated_mask -ne 0 ]]; then # This node is in cluster

        tcli -e "kvar show -n $TPDVARNAME"|grep -q ":$DEFAULTVAL"
        if [ $? -eq 0 ]; then
          tcli -e "kvar set -n $TPDVARNAME -v $NEWVAL"
          message=$(tcli -e "kvar show -n $TPDVARNAME")
          em_test --severity=$INFORMATIONAL --post="$SCRIPT: After setting $TPDVARNAME=$NEWVAL: kvar shows $message"
        fi
        tcli -e "kvar show -n TPDVARNAME"
	exit
    fi  # End of $integrated_mask
KVAR_EOF
 ;;

  mvar)
  cat << "MVAR_EOF"
    if [[ $integrated_mask -ne 0 ]]; then # This node is in cluster

        pm_pid=$(ps -C pm --no-headers -o pid=)

        pid=$(ps -f -C sysmgr --no-headers | grep -e " $pm_pid .* sysmgr --pmfg" | head -1 | awk '{ print $2 }')

        if [ "$pid" != "" ] && [[ $pid != "$prev_pid" || $master != "$prev_master" ]]; then # Change of sysmgr pid/master node

          Current=$(tcli -e "mvar show -n $TPDVARNAME" 2>/dev/null | awk '{ print $NF }')
	  Current=$(hex2decimal $Current)
          if [ "$Current" != "" ]; then # If tcli command works
            prev_pid=$pid
            prev_master=$master
          fi

          if [ "$Current" == "$DEFAULTVAL" ]; then

            tcli -e "mvar set -n $TPDVARNAME -v $NEWVAL"
            message=$(tcli -e "mvar show -n $TPDVARNAME")
            em_test --severity=$INFORMATIONAL --post="$SCRIPT: After setting $TPDVARNAME=$NEWVAL: mvar shows '$message'"

          fi
        fi # End of - Change of sysmgr pid/master node
    fi # end of $integrated_mask
MVAR_EOF
 ;;

  dvar)
  cat << "DVAR_EOF"
    if [[ $integrated_mask -ne 0 ]]; then # This node is in cluster

        pm_pid=$(ps -C pm --no-headers -o pid=)

        pid=$(ps -f -w -C ddcscan --no-headers | grep " $pm_pid .* ddcscan -b" | head -1 | awk '{ print $2 }')

        if [ "$pid" != "" ] && [[ $pid != "$prev_pid" ]]; then # Change of ddcscan pid

          Current=$(tcli -e "$TPDVARTYPE show -n $TPDVARNAME" 2>/dev/null | grep "Nid $mynode:" | awk '{ print $NF }')
          if [ "$Current" != "" ]; then # If tcli command works
            prev_pid=$pid
          fi

          if [ "$Current" == "$DEFAULTVAL" ]; then

            tcli -e "$TPDVARTYPE set -n $TPDVARNAME -v $NEWVAL"
            message=$(tcli -e "$TPDVARTYPE show -n $TPDVARNAME")
            em_test --severity=$INFORMATIONAL --post="$SCRIPT: After setting $TPDVARNAME=$NEWVAL: $TPDVARTYPE shows '$message'"

          fi
        fi # End of - Change of ddcscan pid
    fi # End of - $integrated
DVAR_EOF
 ;;
esac

  cat << "EOF"
} # End of set_<TPDVARTYPE>_variable_during_init

 hex2decimal()
 {
   local val=$1

   echo $val | awk --non-decimal-data '{ printf "%d\n", $1 }'
 }

SCRIPT=$(basename $0)

  case "$1" in
    start)
        echo "Launching $SCRIPT script to work around '$DESCRIPTION' issue by setting $TPDVARNAME=$NEWVAL ($TPDVARTYPE)"
        prev_pid=""
        while true ; do
          eval $(clwait --bash)

          if [[ "$integrated" != "" && "$online" != "" && "$mynode" != "" ]]; then # Is tpd module loaded?

            (( mask=1<<mynode ))
            (( integrated_mask=mask&integrated ))
EOF

  echo -e "\n            $FUNC\n"

  cat << "EOF"
          fi # End of - Is tpd module loaded?
          sleep $SLEEP_TIME
        done < /dev/null >/dev/null 2>&1 & # end of while-loop (close i/p & o/p to follow thru)
        ;;

    stop)
        echo "- Terminating $SCRIPT script pids if any"
        ps -C $SCRIPT --no-headers -o pid= | xargs kill
        ;;

    *)
        echo "Usage: $0 start|stop"
        exit 1
        ;;
  esac
EOF
}

get_tpd_version()
{
  showversion -b $SHOWVERSION_OPT | grep "^Release version" | sed -e "s/Release version//g" -e "s/[()]//g" | sort -u | awk '
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
  if [ $# -ne 1 ]; then
    printf "ERROR: Insufficient arguments passed."
    exit 1
  fi

  local TPD_VERSIONS="$1"

  local TPD=$(get_tpd_version)
  echo "$TPD" | egrep -qw "$TPD_VERSIONS"
  if [ $? -ne 0 ]; then
      echo -e "\nERROR: Script is not applicable for $TPD release or version."
      showversion -b
      exit 1
  fi
}

usage()
{
  local PROG=$(basename $0)

  echo -e "\nUsage: $PROG --install [altroot]"
  echo -e "       $PROG --uninstall [altroot]"
  echo -e "       $PROG --verify\n"

  echo "--install   [altroot] : Installs required init/rc script in root or altroot partitions. Before installing, it asks for user confirmation."
  echo "--uninstall [altroot] : Uninstalls required init/rc script from root or altroot partitions."
  echo "--verify              : Verify whether init/rc script installed."

  exit 1
}

get_script_version()
{
    TPD=$(showversion -b | grep "Release version" | awk '{ print $3 }')
    echo -e "- You are using script version=$Version, TPD=$TPD and running it on $(date)"
    echo -e "- clwait: $(clwait)"

    if [ $# -gt 1 ]; then
      echo "- User command line: $*"
    fi
}

pre_check()
{
  eval $(clwait --bash) # It exports mynode, master, online and integrated
  if [ $integrated -ne $online ]; then
    echo "ERROR: Not all nodes integrated clwait: $(clwait)" >&2
    exit 1
  fi

  showsysmgr|grep -q "System is up and running"
  if [ $? -ne 0 ]; then
    echo "ERROR: sysmgr is not started" >&2
    (set -x; showsysmgr -d)
    exit 1
  fi

  if [ ! -f $ENVIRONMENT ]; then
    echo "ERROR: $ENVIRONMENT file does not exists" >&2
    exit 1
  fi
}

dedup_enable_log_len_check()
{
  local TPDVARTYPE=dvar # It can be kvar, mvar, dvar, kernel
  local TPDVARNAME=enable_log_len_check
  local TPDVARSIZE=xx  # For kvar,mvar,dvar pass "xx" - it is not used. Appkicable for TPDVARTYPE=kernel only.
  local DEFAULTVAL=0
  local NEWVAL=1
  local DEFECTS="146519" # No spaces in between
  local DESCRIPTION="unlimited DDS garbage collection causing shortage of log pages"

  printf "\n(%s) %s\n" $((NUMCNT++)) "${FUNCNAME[0]}: $DESCRIPTION"

  set_tpd_variable_during_init $OPT $TPDVARTYPE $TPDVARNAME $TPDVARSIZE $DEFAULTVAL $NEWVAL $DEFECTS "$DESCRIPTION"
}


OPTION=$1
NUMCNT=1

pre_check
get_script_version $(basename $0) $*
unset FS CHROOT OPT SHOWVERSION_OPT

case $OPTION in
  "--install")
		if [[ $# -eq 2 && $2 != "altroot" ]]; then
		    echo "ERROR: '$2' unknown option specified" >&2
		    exit 1
		fi

		OPT="--install"
		if [ "$2" == "altroot" ]; then
		    FS="/altroot"
		    CHROOT="chroot $FS"
		    SHOWVERSION_OPT="-r"
		fi
		check_tpd_version "$TPD_VERSIONS"
	;;

  "--verify")	OPT="--verify"
	;;

  "--uninstall") OPT="--uninstall"
		 if [ "$2" == "altroot" ]; then
		    FS="/altroot"
		    CHROOT="chroot $FS"
		 fi

                 check_tpd_version "$TPD_VERSIONS" # It is needed as default values are changed in other TPD versions
	;;

  *) usage
	;;
esac

if [ "$OPT" != "" ]; then
  get_script_version $(basename $0) $* >> $LOGNAME
  (dedup_enable_log_len_check
  ) | tee -a $LOGNAME

  echo -e "\n- Log is at $LOGNAME"
else
  echo "ERROR: Invalid option specified" >&2
fi
