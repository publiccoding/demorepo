#!/bin/bash
# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
#
# check_pm_cmp_lrunlen.sh: Script to check PM CMP LRU length

Vesrsion=1.00

PM_CMP_MAJOR=75 # It is in Percent
PM_CMP_MINOR=50 # It is in Percent

if [ $(grep -w -e lru_cachepg_proc_hdr -e npm_cmps /proc/kallsyms | wc -l) -ne 2 ]; then
    echo "- Script is not supported in this TPD version."
    (set -x; showversion -b)
    exit 1
fi

if [[ $# -ne 1 || $# -eq 1 && $1 != "--verify" ]]; then
    echo "Usage: $(basename $0) --verify"
    exit 1
fi

$(clwait --bash)
pm_cmp_lrunlen_hdr=0

npm_cmps=0
for node in {0..7}; do
    if (( (online & (1 << node)) == 0 )); then # Check whether node is online
        continue
    fi

    lru_cachepg_proc_hdr=$(showmemval kernel${node} none u32 1 lru_cachepg_proc_hdr | awk '{ print $NF }')
    if [ $npm_cmps -eq 0 ]; then
        npm_cmps=$(showmemval kernel${node} none u32 1 npm_cmps | awk '{ print $NF }')
    fi

    if [ $npm_cmps -eq 0 ]; then
        continue
    fi

    if [ $pm_cmp_lrunlen_hdr -eq 0 ]; then
        echo -e "- PM CMPs LRU length usage:\n"
        echo "Node    NPmCmps    LruLen   Percent  Status"
        echo "-------------------------------------------"
        pm_cmp_lrunlen_hdr=1
    fi

    echo $lru_cachepg_proc_hdr $npm_cmps $node | awk -v PM_CMP_MAJOR=$PM_CMP_MAJOR -v PM_CMP_MINOR=$PM_CMP_MINOR '{
        pm_cmps_percent=($1*100/$2)

        status="Normal"
        if (pm_cmps_percent >= PM_CMP_MAJOR) status="Major"
        else if (pm_cmps_percent >= PM_CMP_MINOR) status="Minor"

        printf "node%d %9d %9d %9.2f  %s\n", $3, $2, $1, pm_cmps_percent, status
    }'
done

if [ $pm_cmp_lrunlen_hdr -ge 1 ]; then
    echo -e "\nNote:"
    echo "- If PM Cmps LruLen Percent >= $PM_CMP_MAJOR% then status is Major."
    echo "- If PM Cmps LruLen Percent >= $PM_CMP_MINOR% then status is Minor."
    echo "- If PM Cmps LruLen Percent < $PM_CMP_MINOR% then status is Normal."
    echo -e "\n- If PM CMPs LruLen status is 'Major' then Consult Support."
else
    echo "$(basename $0) script is not supported in this configuration."
fi
