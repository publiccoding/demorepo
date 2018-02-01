#!/bin/bash
# cmpleak_info.sh : Script to know cmp leak if any in live setup

# cmpAvailable   = sum of "Queue Statistics" on node basis + "Temporary and Page Credits" on node basis.
# cmpAllocated   = (cmp_end - cmp_start)
# CMPAvailable%  = cmp Available/cmpAllocated*100
#
# - CMPAvailable% < $CMP_AVAILABLE_MAJOR cmpLeakStatus marked as "Major"
# - CMPAvailable% < $CMP_AVAILABLE_MINOR cmpLeakStatus marked as "Minor"
# - CMPAvailable% > $CMP_AVAILABLE_MINOR cmpLeakStatus marked as "Normal"

Version=1.03

CMP_AVAILABLE_MAJOR=50
CMP_AVAILABLE_MINOR=70

function get_cmp_struct_size
{
  gdb -q -n /opt/tpd/bin/sysmgr <<\EOF | grep "cmp_t size=" | awk -F "=" '{ print $NF }'
    printf "cmp_t size=%d\n", sizeof(cmp_t)
    q
EOF
}

$(clwait --bash)

# Make sure sysmgr is up and running
showsysmgr |grep -q "System is up and running"
if [ $? -ne 0 ]; then
        echo "ERROR: showsysmgr failed: $(showsysmgr)" >&2
        (set -x; showsysmgr -d)
        exit 1
fi

TPD=$(showversion -b | grep "Release version" | awk '{ print $3 }')

echo -e "\n- You are using script version=$Version, TPD=$TPD and running it on $(date)\n"

cmp_struct_size=$(get_cmp_struct_size)

cmp_start=$(showmemval kernel${mynode} none u64 1 cmp_start | awk -F ":" '{ print $NF }')
cmp_end=$(showmemval kernel${mynode} none u64 1 cmp_end | awk -F ":" '{ print $NF }')

cmp_allocated=$(((cmp_end-cmp_start)/cmp_struct_size))

#cmp_allocated=$(echo 'printf "cmp_allocated=%d\n", cmp_end-cmp_start' | crash -s | grep "cmp_allocated=" | awk -F "=" '{ print $NF }')

echo "Node# cmpAvailable  cmpAllocated cmpAvailable% cmpLeakStatus"
echo "------------------------------------------------------------"

statcmp -iter 1 | sed -e "s/---/   /g" | awk -v cmp_allocated=$cmp_allocated -v CMP_AVAILABLE_MAJOR=$CMP_AVAILABLE_MAJOR -v CMP_AVAILABLE_MINOR=$CMP_AVAILABLE_MINOR '
BEGIN { data=0 }
/Queue Statistics/ { data=1 }
/Temporary and Page Credits/ { data =2 }
/Page Statistics/ { data =0 }
{
  if (data && $1 ~ /[0-7]/)
	for(i=2; i<=NF; i++) cmp_available[$1]+=$i
}
END {
     for (elem in cmp_available) {
	cmp_available_percent=cmp_available[elem]/cmp_allocated*100

	if (cmp_available_percent < CMP_AVAILABLE_MAJOR) CmpSts="Major"
	else if (cmp_available_percent < CMP_AVAILABLE_MINOR) CmpSts="Minor"
	else CmpSts="Normal"

	sort="sort"
	printf "node%s %12s  %12s  %12.2f        %s\n", elem, cmp_available[elem], cmp_allocated, cmp_available_percent, CmpSts | sort
   }
  }
'

echo -e "\nNote:"
echo "- cmpAvailable% < $CMP_AVAILABLE_MAJOR% - cmpLeakStatus=Major"
echo "- cmpAvailable% < $CMP_AVAILABLE_MINOR% - cmpLeakStatus=Minor"
echo "- cmpAvailable% > $CMP_AVAILABLE_MINOR% - cmpLeakStatus=Normal"
