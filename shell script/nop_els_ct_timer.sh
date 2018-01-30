#!/bin/bash
# nop_els_ct_timer.sh:  Script generates /etc/rc2.d/S30nop_els_ct_timer file
# - It works around emfc_thread_els_ct_timeout_monitor issue
# - Reapply the workaround, if node rescue takes place on same setup where 
#   workaround applied earlier
# - This rc script will be automatically removed during TPD upgrade
# - It is created to workaround 97912 and 94777 issue and applicable for
#   TPD=3.1.2.MU2/3.1.2.MU3
# Version: 1.01

RC_SCRIPT_FILE=S30nop_els_ct_timer
DIR=/etc/rc2.d

function generate_rcscript_file
{
File=$1

echo -e "\nGenerating ${File} rc script file"

cat << "EOF" > ${File}
#!/bin/bash
# /etc/rc2.d/S30nop_els_ct_timer: Script to workaround emfc_thread_els_ct_timeout_monitor issue during node boot-up
# - It replaces with emfc_thread_els_ct_timeout_monitor() with emfc_thread_nop() in emfc_thread_handlers array
# - It is suggested workaround when node panics with "tpd:  tpd_cv_wait: thread cannot sleep" while calling
#   emfc_thread_els_ct_timeout_monitor in 3.1.2.MU2/MU3.
#
#  Applicability:
#
#  Bug: 97912
#  Check stack trace before applying:
#  (tpd_panic+0xf7)
#  (tpd_cv_wait+0xa9)
#  (emfc_reserve_mailbox+0x85)
#  (emfc_send_logo_accept_done+0x36)
#  (emfc_rst_port+0x6b8)
#  (emfc_thread_els_ct_timeout_monitor+0x15c)
#  (emfc_task_thread+0xf3)
#
#  Bug: 94777
#  Repeated port toggles due to ELS/CT timeouts.  Check event log for message like so:
#  Port n:s:p - ELS/CT timeout, iocb command x (y), io_tag z
#  where n:s:p is the port, x and z are hex numbers, and y is a string
#
# Note:
# - Script will be automatically removed during TPD upgrade.

CRASHHOME=/opt/tpd
CRASH=${CRASHHOME}/bin/crash
CRASHOPT="-s -i /root/.crashrc"

CLWAIT=/opt/tpd/bin/clwait
LSMOD=/bin/lsmod
OFFSET=17
MAXLOOP=60

case "$1" in
    start)
	echo "Applying workaround for emfc_thread_els_ct_timeout_monitor issue"
	loop=0
        while [ $loop -le $MAXLOOP ]; do
          eval $($CLWAIT --bash)

          if [[ "$integrated" != "" && "$online" != "" && "$mynode" != "" ]]; then

	    $LSMOD | grep -q "^tpd "
	    tpd_loaded=$?

	    emfc_thread_nop=$(grep -w emfc_thread_nop /proc/kallsyms|awk '{print "0x"$1}')
	    #echo "emfc_thread_nop: $emfc_thread_nop"

	    emfc_thread_handlers=$(grep -w emfc_thread_handlers /proc/kallsyms|awk '{print "0x"$1}')
	    #echo "emfc_thread_handlers: $emfc_thread_handlers"

            if [[ $tpd_loaded -eq 0 && "$emfc_thread_nop" != "" && "$emfc_thread_handlers" != "" ]]; then

		emfc_thread_handlers_ptr=$(printf "%#x\n" $((emfc_thread_handlers+$OFFSET*8)))
		#echo "emfc_thread_handlers_ptr: $emfc_thread_handlers_ptr"

		workaround=$(echo "wr -k -64 $emfc_thread_handlers_ptr $emfc_thread_nop")
		#echo "workaround: $workaround"
		echo "$workaround" | $CRASH $CRASHOPT > /dev/null

                break
            fi # end of $tpd_loaded
          fi # end of $integrated
          sleep 15
	  loop=$((loop+1))
        done < /dev/null >/dev/null 2>&1 & # end of while-loop (close i/p & o/p to follow thru)
	;;
    stop)
        ;;
    *)
        echo "Usage: $0 start|stop"
        exit 1
        ;;
esac
EOF

chmod +x ${File}
}

function usage
{
    echo "Usage: $0         # To install $RC_SCRIPT_FILE rc script on live setup"
    echo "       $0 altroot # To install $RC_SCRIPT_FILE rc script on /altroot before upgrade"
    exit 1
}

FS=""
OPT=""

if [ $# -gt 0 ]; then
  if [ $# -ne 1 ]; then
	echo -e "ERROR: Too many arguments\n" 2>&1
	usage
  elif [ $1 != altroot ]; then
	echo -e "ERROR: Unknown option \"$1\"\n"
	usage
  fi
  FS="/altroot"
  OPT="-r" # option to read version details from altroot partition
fi

$(clwait --bash) # It exports mynode, master, online and integrated
if [ $integrated -ne $online ]; then
    echo "ERROR: Not all nodes are integrated clwait: $(clwait)"
    exit 1
fi

showsysmgr|grep -q "System is up and running"
if [ $? -ne 0 ]; then
    echo "ERROR: sysmgr is not started"
    exit 1
fi

showversion $OPT|grep "Release version"|grep -q "3\.1\.2"
if [ $? -ne 0 ]; then
        echo "ERROR: Script is not applicable for this release"; echo
        (set -x; showversion $OPT)
        exit 1
fi

subver=$(showversion -b $OPT | grep "Release version"|awk '{split($3, ver, "."); print ver[4]}')
if [[ "$subver" = "" ||  $subver -ne 422 && $subver -ne 484 ]]; then
        echo "ERROR: Script is not applicable for this version"; echo
        (set -x; showversion -b $OPT)
        exit 1
fi

generate_rcscript_file ${RC_SCRIPT_FILE}.$$

echo -e "\nCopying ${RC_SCRIPT_FILE} rc script across all nodes"
echo -e "- It workarounds emfc_thread_els_ct_timeout_monitor issue during node boot-up\n"

for node in $(shownode -nohdtot|awk '{print $1}')
do
    (set -x; rcp ${RC_SCRIPT_FILE}.$$ node${node}:${FS}${DIR}/${RC_SCRIPT_FILE})
done

rm -f ${RC_SCRIPT_FILE}.$$

echo
(set -x; onallnodes chmod +x ${FS}${DIR}/${RC_SCRIPT_FILE}
onallnodes ls -l ${FS}${DIR}/${RC_SCRIPT_FILE})

if [ "$FS" == "" ]; then # To apply the workaround on running live system; NA for "altroot"
  for node in `seq 0 7`; do 
    if [ $((online & (1 << node))) -eq 0 ]; then
	continue    
    fi 
    (set -x; rsh  node${node} ${DIR}/${RC_SCRIPT_FILE} start)
    echo
  done
fi

echo "Successfully installed ${FS}${DIR}/${RC_SCRIPT_FILE} file on all the nodes."
