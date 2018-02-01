#!/bin/bash
# increase_rsh_connections.sh: Script to increase rsh connections 
# - It avoids 'poll: protocol failure in circuit setup' issue while running fixglist script
# - Defect(s) it works around: 150979,148829

Version=1.02

# It is applicable for 3.1.2.MU3, 3.1.2.MU5, 3.1.3.GA, 3.1.3.MU1, 3.1.3.MU2, 3.2.1.GA, 3.2.1.MU1, 3.2.1.MU2, 3.2.1.MU3, 3.2.1.MU4, 3.2.2.GA
TPD_VERSIONS="3.1.2.484|3.1.2.592|3.1.3.202|3.1.3.230|3.1.3.262|3.2.1.46|3.2.1.120|3.2.1.200|3.2.1.292|3.2.1.356|3.2.2.290"

INETD_CONF=/etc/inetd.conf
TCP_TW_RECYCLE=/proc/sys/net/ipv4/tcp_tw_recycle
OPENBSD_INETD=/etc/init.d/openbsd-inetd

ALPHABET=({a..z} {A..Z})
INFORMATIONAL=5 # To post events
SCRIPT=increase_rsh_connections.sh
LOGNAME="/var/log/tpd/${SCRIPT}.out"

usage()
{
  local PROG=$(basename $0)

  echo -e "Usage: $PROG --install"
  echo -e "       $PROG --uninstall"
  echo -e "       $PROG --verify\n"

  echo "--install   : To install the work-around."
  echo "--uninstall : It uninstalls the work-around."
  echo "--verify    : Verifies the work-around."

  echo -e "\nNote:"
  echo "- During advanced upgrade, --uninstall the work-around once TPD bits are loaded in altroot partition."
  echo "- If upgrade is reverted, --uninstall the work-around to restore back to defaults."

  exit 1
}

increase_rsh_connections()
{
  local OPT=$1
  local workaround=0

  if [ "$OPT" == "--install" ]; then
    echo -e "(${ALPHABET[ALPHCNT++]}) Applying work-around"

    cat $INETD_CONF | sed -e "1,/:BSD: Shell/d" | grep -P -q "nowait\t"
    if [ $? -eq 0 ]; then
      workaround=1
    fi

    # Replace nowait with nowait.10000 in /etc/inetd.conf file after '#:BSD: Shell, login, exec and talk are BSD protocols.'
    onallnodes 'sed -i -e "1,/:BSD: Shell/p" -e "1,/:BSD: Shell/d" -e "s/nowait\t/nowait.10000\t/"' $INETD_CONF > /dev/null
    onallnodes 'sed -i -e "1,/:BSD: Shell/p" -e "1,/:BSD: Shell/d" -e "s/nowait /nowait.10000 /"' $INETD_CONF > /dev/null

    # Set TCP_TW_RECYCLE with '1' (Default: 0)
    onallnodes "echo 1 > $TCP_TW_RECYCLE" > /dev/null

    # Restart inetd on all the nodes
    onallnodes $OPENBSD_INETD restart > /dev/null

    if [ $workaround -eq 1 ]; then
      em_test --severity=$INFORMATIONAL --post="$SCRIPT: Successfully applied the work-around." >/dev/null
    fi
  elif [ "$OPT" == "--uninstall" ]; then
    echo "(${ALPHABET[ALPHCNT++]}) Restoring to defaults"

    cat $INETD_CONF | sed -e "1,/:BSD: Shell/d" | grep -P -q "nowait.10000\t"
    if [ $? -eq 0 ]; then
      workaround=1
    fi

    # Replace nowait.10000 with nowait.10000 in /etc/inetd.conf file after '#:BSD: Shell, login, exec and talk are BSD protocols.'
    onallnodes 'sed -i -e "s/nowait.10000\t/nowait\t/"' $INETD_CONF > /dev/null
    onallnodes 'sed -i -e "s/nowait.10000 /nowait /"' $INETD_CONF > /dev/null

    # Set TCP_TW_RECYCLE to default
    onallnodes "echo 0 > $TCP_TW_RECYCLE" > /dev/null

    # Restart inetd on all the nodes
    onallnodes $OPENBSD_INETD restart > /dev/null

    if [ $workaround -eq 1 ]; then
      em_test --severity=$INFORMATIONAL --post="$SCRIPT: Successfully restored to defaults." >/dev/null
    fi
  fi

  echo -e "\n(${ALPHABET[ALPHCNT++]}) Verifying work-around"

  echo -e "\n- Data from /etc/inetd.conf file (Work-around: nowait.10000, Default: nowait)"
  cat $INETD_CONF | sed -e "1,/:BSD: Shell/d" | grep nowait

  echo -e "\n- tcp_tw_recycle value: (Work-around: 1, Default: 0)"
  onallnodes "echo $TCP_TW_RECYCLE = $(cat $TCP_TW_RECYCLE)"

  echo -e "- inetd processes:"
  onallnodes ps --no-headers -fC inetd

  echo -e "- Event log messages with ${SCRIPT} pattern in last one hour:"
  (set -x; showeventlog -min 60 -debug -oneline -msg "${SCRIPT}")

}

# Function to check TPD version
check_tpd_version()
{
  showversion -b | grep "Release version" | egrep -qw "$TPD_VERSIONS"
  if [ $? -ne 0 ]; then
    echo -e "ERROR: Script is not applicable for this release or version\n" >&2
    (set -x; showversion -b)
    exit 1
  fi
}

get_script_version()
{
  TPD=$(showversion -b | grep "Release version" | awk '{ print $3 }')
  echo -e "- You are using script version=$Version, TPD=$TPD and running it on $(date)"
  echo -e "- clwait: $(clwait)\n"
}

get_script_version

$(clwait --bash)
if [[ "$integrated" == "" && "$mynode" == "" ]]; then
  echo "ERROR: It is not InServ live setup"
  exit 1
fi

OPTION=$1
ALPHCNT=0

case $OPTION in
  "--install")  check_tpd_version "$TPD_VERSIONS"
        ;;

  "--verify")
        ;;

  "--uninstall") check_tpd_version "$TPD_VERSIONS"
        ;;

  *) usage
        ;;
esac

increase_rsh_connections $OPTION | tee -a $LOGNAME

echo -e "\n- Log is at $LOGNAME"
