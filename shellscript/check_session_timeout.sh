#!/bin/bash
# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
#
# check_session_timeout.sh : Script to check that SessionTimeout value of CLI commands is an integer
#
# - Applicable Defect(s): 207834, 208356
# - Script is applicable to all TPD_VERSIONS

Version=1.01

# Failure Codes (or) exit values from scripts
PASS=0        # Passed
FAILPERM=1    # Failure, permanent

usage()
{
    local prog=$(basename $0)

    echo -e "Usage: $prog --verify\n"

    echo "--verify: Verify if the SessionTimeout value for the cli commands is valid."

    exit $FAILPERM
}

get_script_version()
{
    echo -e "- You are running the script '$1 $2' version $Version on $(date "+%Y-%m-%d %T")"
    echo -e "- clwait: $(clwait)"

    if [ $# -ne 0 ]; then
      echo "- User command line: $*"
    fi
}

check_session_timeout()
{
    local sessionTimeout=$(pr_test --table=pr_sysparms --print | grep -A1 SessionTimeout)
    if [ "$sessionTimeout" == "" ]; then
        echo "${FUNCNAME[0]}: Verification complete. Status: Pass"
        return $PASS
    fi

    local sessionTimeoutValue=$(echo "$sessionTimeout" | grep -w value | cut -d'{' -f2 | cut -d'}' -f1)
    local valuelen=$(echo "$sessionTimeout" | grep -w valuelen | cut -d',' -f1 |cut -d'=' -f2)
    # Number of characters in sessionTimeoutValue plus the nul character
    local sessionTimeoutLen=$((${#sessionTimeoutValue} + 1))
    if  [[ $sessionTimeoutValue =~ ^[0-9]+$ && $valuelen -eq $sessionTimeoutLen ]];then
        echo "${FUNCNAME[0]}: SessionTimeout value is valid."
        echo "${FUNCNAME[0]}: Verification complete. Status: Pass"
        return $PASS
    fi

    echo -e "${FUNCNAME[0]}: SessionTimeout value is not valid.\n - SessionTimeout should be an integer value greater than zero"
    return $FAILPERM
}

if [ $# -ne 1 ]; then
    usage
fi

OPTION=$1

get_script_version $(basename $0) "$@"

case $OPTION in
    "--verify")
        ;;

    *)
        usage
        ;;
esac

check_session_timeout
rval=$?
exit $rval
