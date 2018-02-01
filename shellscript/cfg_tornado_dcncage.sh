#!/bin/bash
# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
#
# cfg_tornado_dcncage.sh: Script generates /etc/init.d/tpd_cfg_tornado_dcncage
# - It configures a Tornado Enclosures DP-1 port to operate at appropriate speed
# - Defect(s) it works around: 194691
# - Reapply the work around, if node rescue takes place on same setup
#
# How script works?
# - It creates init/rc script.
# - init/rc script will monitor the phy state then set appropriate speed
# - For ex:- To handle power cycle of DCN cage or node conditions

Version=1.00

DESCRIPTION="Configures a Tornado Enclosures DP-1 port"

INITDIR=/etc/init.d
INITSCRIPT=tpd_cfg_tornado_dcncage

ALPHABET=({a..z} {A..Z})
ALPHCNT=0

usage()
{
  local PROG=$(basename $0)

  echo -e "\nUsage: $PROG --install"
  echo -e "       $PROG --uninstall"
  echo -e "       $PROG --verify\n"

  echo "--install   : Installs required init/rc script in root."
  echo "--uninstall : Uninstalls required init/rc script from root partition."
  echo "--verify    : Verify whether init/rc script installed."

  exit 1
}

generate_rcscript()
{
    cat << RC_EOF # Import variables from main script or function to here-document
#!/bin/bash
# /etc/init.d/$INITSCRIPT: It runs $INITSCRIPT to avoid '$DESCRIPTION'
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
. /etc/environment

DESCRIPTION="$DESCRIPTION"
INITDIR=/etc/init.d
INITSCRIPT=$INITSCRIPT
RC_EOF

    cat << "RC_EOF" # No variables will be imported
SLEEP_TIME=300 # Retry every 5 minutes
MAJOR=2
INFORMATIONAL=5

STORESERV_MODEL_LIST="8..."

run_cfg_tornado_dcncage_during_init()
{
  local retval=0

  if [ $mynode -eq $master ]; then
    update_pwfile
  fi

  if [ -z "$STORESERV_MODEL" ]; then
    STORESERV_MODEL=$(showsys -d | awk ' /System Model/ { print $NF }')
    echo "$STORESERV_MODEL" | egrep -qw "$STORESERV_MODEL_LIST"
    retval=$?
    if [[ -n "$STORESERV_MODEL" && $retval -ne 0 ]]; then
     exit 0
    fi
  fi

  SLEEP_TIME=600 # After first execution inter delay is 10 minutes

  if [[ $retval -eq 0 && $mynode -eq $master ]]; then
      local dcncage=$(showcage |  awk '/DCN/ { if ($3 != "---" && $5 != "---" && $9 == 4078 && $10 == 4078) print $2 }')
      echo "$dcncage" | while read cage;
      do
        local dcn_version_path=$(showcage -nohdtot $cage | awk '($9 == 4078) && ($3 != "---") && ($10 == 4078) && ($5 != "---")')
        if [ -z "$dcn_version_path" ]; then
          cotinue
        fi # PATH and VERSION should match

        local cage_sfp=$(showcage -sfp -d $cage)

        echo "$cage_sfp" | grep -e "FCAL" -e "Part Number" | grep -A1 "FCAL 0" | grep -q "Part Number .* 713533-00[34]"
        if [ $? -eq 0 ]; then # Is it connected with AOC cable?
          cli cgcmd  -tc tty -C $cage -c phydump -p a | grep -q "^ *[4567] |Port .*12.0G"
          if [ $? -eq 0 ]; then # If Phy value is 12.0G then it set it to 6.0G
            for (( phy=4; phy <= 7; phy++ ))
            do
              cli cgcmd -tc tty -C $cage -c phy_txconf $phy std phy_rate 7 -p a
              cli cgcmd -tc tty -C $cage -c phy_txconf $phy std g4_with_ssc 0 -p a
              cli cgcmd -tc tty -C $cage -c phy_txconf $phy std g4_without_ssc 0 -p a
            done # LOOP for DPI PHY SETTING
          fi # PHY SPEED CHECK
        fi # Active Optic Cable

        echo "$cage_sfp" | grep -e "FCAL" -e "Part Number" | grep -A1 "FCAL 1" | grep -q "Part Number .* 713533-00[34]"
        if [ $? -eq 0 ]; then # Is it connected with AOC cable?
          cli cgcmd  -tc tty -C $cage -c phydump -p b | grep -q "^ *[4567] |Port .*12.0G"
          if [ $? -eq 0 ]; then # If Phy value is 12.0G then it set it to 6.0G
            for (( phy=4; phy <= 7; phy++ ))
            do
              cli cgcmd -tc tty -C $cage -c phy_txconf $phy std phy_rate 7 -p b
              cli cgcmd -tc tty -C $cage -c phy_txconf $phy std g4_with_ssc 0 -p b
              cli cgcmd -tc tty -C $cage -c phy_txconf $phy std g4_without_ssc 0 -p b
            done # LOOP for DPI PHY SETTING
          fi # PHY SPEED CHECK
        fi # Active Optic Cable
      done # LOOP for DCN cages
  fi # TORNADO MODEL and MAster Node only
}

terminate_script()
{
    # Exclude your process while terminating init/rc script
    pid_list=$(ps -C $SCRIPT,$INITSCRIPT --no-headers -o pid= | grep -v $$ | xargs)

    if [ -n "$pid_list" ]; then
        kill -9 $pid_list >/dev/null 2>&1 # Force to terminate the process
        sleep 2
    fi
}

SCRIPT=$(basename $0)

  case "$1" in
    install)
        $(clwait --bash)
        update-rc.d -f ${INITSCRIPT} remove >/dev/null 2>&1
        update-rc.d ${INITSCRIPT} defaults  >/dev/null 2>&1

        message="Successfully installed ${INITDIR}/${INITSCRIPT} file on node $mynode."
        em_test --severity=$INFORMATIONAL --post="$INITSCRIPT: $message" >/dev/null
        echo $message
        ;;

    uninstall)
        $(clwait --bash)
        update-rc.d -f ${INITSCRIPT} remove >/dev/null 2>&1
        message="Removed $INITSCRIPT init script from node $mynode."
        em_test --severity=$INFORMATIONAL --post="$INITSCRIPT: $message" >/dev/null
        echo $message
        ;;

    start)
        terminate_script
        echo "Launching $SCRIPT script to work around '$DESCRIPTION' issue"
        prev_pid=""
        while true ; do
          eval $(clwait --bash)

          if [[ "$integrated" != "" && "$online" != "" && "$mynode" != "" ]]; then # Is tpd module loaded?

            (( mask=1<<mynode ))
            (( integrated_mask=mask&integrated ))

            if [ $integrated_mask -ne 0 ]; then # This node is in cluster
                run_cfg_tornado_dcncage_during_init
            fi

          fi # End of - Is tpd module loaded?
          sleep $SLEEP_TIME
        done < /dev/null >/dev/null 2>&1 & # end of while-loop (close i/p & o/p to follow thru)
        ;;

    stop)
        terminate_script
        ;;

    *)
        echo "Usage: $0 start|stop"
        exit 1
        ;;
  esac
RC_EOF
}

cfg_tornado_dcncage()
{
    local option=$1

    case $option in
    "--postinstall") # For patch postinstall and during node rescue if script installed as a patch
        generate_rcscript > $INITDIR/$INITSCRIPT 2>/dev/null
        chmod +x $INITDIR/$INITSCRIPT

        update-rc.d -f ${INITSCRIPT} remove >/dev/null 2>&1
        update-rc.d ${INITSCRIPT} defaults  >/dev/null 2>&1
        ;;

    "--install")
        echo -e "\n(${ALPHABET[ALPHCNT++]}) Installing ${INITSCRIPT} script in all nodes of the cluster."
        onallnodes "
            if [ -x $INITDIR/$INITSCRIPT ]; then
                $INITDIR/$INITSCRIPT stop
            fi
        " > /dev/null

        generate_rcscript > $INITDIR/$INITSCRIPT
        chmod +x $INITDIR/$INITSCRIPT

        onothernodes "rcp node$mynode:$INITDIR/$INITSCRIPT $INITDIR" > /dev/null
        onallnodes "${INITDIR}/${INITSCRIPT} install"
        onallnodes "${INITDIR}/${INITSCRIPT} start" > /dev/null
    ;;

    "--uninstall")
        echo -e "\n(${ALPHABET[ALPHCNT++]}) uninstalling ${INITSCRIPT} script from all nodes of the cluster."
        onallnodes "
            if [ -x $INITDIR/$INITSCRIPT ]; then
                ${INITDIR}/${INITSCRIPT} stop
                ${INITDIR}/${INITSCRIPT} uninstall
                rm -f $INITDIR/$INITSCRIPT
            fi
        "
    ;;

    "--verify")
        echo -e "\n(${ALPHABET[ALPHCNT++]}) $INITSCRIPT init/rc script file list:"
        onallnodes "
            if [ -f ${INITDIR}/${INITSCRIPT} ]; then
                ls -l ${INITDIR}/${INITSCRIPT}
            fi
        "

        echo -e "\n(${ALPHABET[ALPHCNT++]}) Checking whether ${INITSCRIPT} script process is running?"
        onallnodes "ps -f -w -C $INITSCRIPT --no-header"

        echo -e "\n(${ALPHABET[ALPHCNT++]}) checkhealth cabling status"
        checkhealth -detail cabling
    ;;

    *)
        usage
    ;;
    esac

    return 0
}

if [ $# -ne 1 ]; then
    usage
fi

option=$1

$(clwait --bash 2>/dev/null)

cfg_tornado_dcncage $option
retval=$?

exit $retval
