#!/usr/bin/ksh
# chkioctl.sh: Script to check active ioctls. Need to run it on the InServ with root access
# Version      : 1.01
# Developed on : 2012-09-17
# Last Modified: 2014-08-06
# Bug#         : 78639
# Contact      : UDU-EngESCTeam@hp.com

# Version: 1.01
# - tocsvr in master node can have one outstanding ioctl from 3.1.3. Modified the code to handle it.

echo -e "- This script gets active_ioctls value thru cli interface. If cli is stuck use chkactive_ioctls.sh script.\n"

MAXCOUNT=10
SLEEPTIME=30
count=0
ioctl_sts=0
node_pass_cnt=0

while [ 1 ]; do
    `clwait --bash`
    if [ $online -eq $integrated ]; then
	break
    fi
    printf "Not all nodes are integrated Online=0x%02X Integrated=0x%02X\n" $online $integrated
    sleep 30
done

printf "Online=0x%02X Integrated=0x%02X\n" $online $integrated

tpd_level=$(showversion -b | grep "^Release version" | awk '{ 
    TPD=$3;
    split(TPD, t, ".");
    tpd_level=t[1]*1000000 + t[2]*100000 + t[3]*10000 + t[4];
    print tpd_level
  }'
)

prev_online=$online
prev_integrated=$integrated

while [ 1 ]
IO_TYPE_NOTDEFINED=
IO_TYPE_MANGLER=
IO_TYPE_TOCSVR=
IO_TYPE_PDSCRUB=
do
    echo "\nIteration count: $count"
    for node in `seq 0 7`; do
	if [ $((ioctl_sts & (1 << node))) -ne 0 ]; then # No pending ioctls
		continue
	fi

        if [ $((online & (1 << node))) -eq 0 ]; then
            continue
        fi

        VALUE=$(showmemval kernel$node none u32 4 active_ioctls)
        IO_TYPE_NOTDEFINED=$(echo "$VALUE" | awk '{print $2'})
        IO_TYPE_MANGLER=$(echo "$VALUE" | awk '{print $3'})
        IO_TYPE_TOCSVR=$(echo "$VALUE" | awk '{print $4'})
        IO_TYPE_PDSCRUB=$(echo "$VALUE" | awk '{print $5'})

        if [[ $IO_TYPE_TOCSVR -gt 0 && $node -eq $master && $tpd_level -gt 3130000 ]]; then
            ((IO_TYPE_TOCSVR--))
	fi

	if [ $IO_TYPE_MANGLER -gt 1 ] || [ $IO_TYPE_TOCSVR -gt 0 ]; then
	    sts=YES
	else
	    sts=NO
	    ioctl_sts=$((ioctl_sts | 1 << node))
	    node_pass_cnt=$((node_pass_cnt+1))
	fi
        echo "Node $node: NOTDEFINED=$IO_TYPE_NOTDEFINED MANGLER=$IO_TYPE_MANGLER TOCSVR=$IO_TYPE_TOCSVR PDSCRUB=$IO_TYPE_PDSCRUB IOCTL_PENDING=$sts"
    done

    count=$((count+1))
    if [ $ioctl_sts -eq $online ] || [ $count -ge $MAXCOUNT ]; then
	break
    fi

    sleep $SLEEPTIME
done

if [ $ioctl_sts -ne $online ]; then
	printf "\nSTATUS: FAIL - ioctls are still pending for some nodes. Node Mask=0x%02X\n" $((online-ioctl_sts))
	echo "\nNote: Contact HP"
	exit 1
fi

`clwait --bash`
if [ $online -ne $prev_online ]; then
	printf "\nSTATUS: FAIL - clwait Online changed from Online=0x%02X to Online=0x%02X\n" $prev_online $online
	echo "\nNote: Rerun the script to authenticate it"
	exit 1
fi

if [ $integrated -ne $prev_integrated ]; then
	printf "\nSTATUS: FAIL - clwait Integrated changed from Integrated=0x%02X to Integrated=0x%02X\n" $prev_integrated $integrated
	echo "\nNote: Rerun the script to authenticate it"
	exit 1
fi

echo "\nSTATUS: PASS for Node Count=$node_pass_cnt"
