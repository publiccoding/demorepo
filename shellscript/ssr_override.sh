#!/bin/bash
# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
#
# ssr_override.sh : Creates ssr_override touchfile for dds to prevent background snapshot removals before restarting sysmgr.
#
# Bug(s) Prevents: 185535

Version=1.00

TPD_VERSIONS="3.2.1.MU5"

TOUCHFILE=/common/touchfiles/ssr_override
ALPHABET=({a..z} {A..Z})

usage()
{
  local PROG=$(basename $0)

    echo -e "Usage: $PROG --install"
    echo -e "       $PROG --uninstall"
    echo -e "       $PROG --verify\n"

    echo "--install   : Creates $TOUCHFILE touchfile in all the nodes."
    echo "--uninstall : Removes $TOUCHFILE touchfile from all the nodes."
    echo "--verify    : Verify whether $TOUCHFILE touchfile present or not."

    echo -e "\nNote: After TPD upgrade/abort or patch install run '$0 --uninstall to remove $TOUCHFILE file."

  exit 1
}

get_script_version()
{
    local patches=$(showversion -b | awk '/^Patches/ && $2 != "None" { print "+"$2 }')
    local tpd=$(showversion -b)
    tpd=$(translate_tpd_release_version "$tpd")

    local altroot_tpd=$(showversion -b -r)
    altroot_tpd=$(translate_tpd_release_version "$altrootTPD")

    echo -e "- You are using $SCRIPT script version=$Version, TPD=$tpd$patches and running it on $(date "+%Y-%m-%d %X")"
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
            if (NF == 1) {
                TAG = "GA";
            } else {
                TAG = $2;
            }

            split($1, t, ".");
            tpd_version = t[1]"."t[2]"."t[3]"."TAG;
            print tpd_version;
        }
    '
}

get_tpd_version()
{
    local partition=$1

    (
        if [[ "$partition" == "root" || "$partition" == "both" ]]; then
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
            if (NF == 1) {
                TAG = "GA";
            } else {
                TAG = $2;
            }

            split($1, t, ".");
            tpd_version = t[1]"."t[2]"."t[3]"."TAG;
            print tpd_version;
        }
    '
}

# Function to check TPD version
check_tpd_version()
{
    if [[ $# -eq 0 || $# -gt 2 ]]; then
        echo "ERROR: Insufficient arguments passed to ${FUNCNAME[0]} function - caller: ${FUNCNAME[1]}"
        exit 1
    fi

    local tpd_versions="$1"
    local partition=""

    if [ $# -ge 2 ]; then
        local partition=$2
    fi

    local tpd=$(get_tpd_version $partition)
    echo "$tpd" | egrep -qw "$tpd_versions"

    if [ $? -ne 0 ]; then
        echo "$(basename $0 .sh): Script is not applicable for $tpd release or version."
        exit 1
    fi
}

isit_dds_setup()
{
  # Check is it dedup setup
  showvv -nohdtot -p -prov dds -showsysobjs | grep -qw dds
  if [ $? -ne 0 ]; then
    echo -e "\nERROR: No dds volume(s) found. This script is not applicable."
    exit 1
  fi
}

if [ $# -eq 0 ]; then
    usage
fi

option=$1

get_script_version $0 $*


ALPHCNT=0

case $option in
    "--install")
        upgradesys_status=$(cli upgradesys -status)
        echo "$upgradesys_status" | grep -q "System is not currently undergoing an online upgrade"
        if [ $? -eq 0 ]; then
            partition="root"
        else
            partition="both"
        fi

        check_tpd_version "$TPD_VERSIONS" $partition
        isit_dds_setup
        echo "(${ALPHABET[ALPHCNT++]}) Creating $TOUCHFILE file in all the nodes."
        onallnodes "(set -x; touch $TOUCHFILE) 2>&1"
        ;;

    "--uninstall")
        echo "(${ALPHABET[ALPHCNT++]}) Removing if $TOUCHFILE file is present."
        onallnodes "(set -x; rm -f $TOUCHFILE) 2>&1"
        ;;

    "--verify")
        ;;

    *)
        usage
        ;;
esac

echo -e "\n(${ALPHABET[ALPHCNT++]}) Verifying whether $TOUCHFILE file is present?"
onallnodes "ls -l $TOUCHFILE"
