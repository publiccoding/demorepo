#!/bin/bash
# check_pd_label.sh: Script to check "3PARDATA" PD label for each drive by using testread
# Note:
# - If any drive got invalid label and drive is in normal-normal state then run rewrite_pd_label.sh script on each drive basis
# - If multiple drives reported degraded/failed with invalid_label then run, repair_pd_invalid_label.sh

Version=1.02

pd_count=0
invalid_label_count=0
INVALID_LABEL_PD_LIST=""
for pd_id in $(showpd -nohdtot -showcols Id,Type,State,Detailed_State | egrep -v " VV |--" | egrep "normal|invalid_label" | awk '{ print $1 }') ; do
    ((pd_count++))
    echo -n "checking PD $pd_id"
    testread -f /dev/tpddev/pd/$pd_id -o 16 -n 1 | grep 3PARDATA
    if [ $? -ne 0 ]; then
      INVALID_LABEL_PD_LIST="${INVALID_LABEL_PD_LIST} $pd_id"
      ((invalid_label_count++))
        echo ": invalid_label found"
    fi

done

if [ -n "$INVALID_LABEL_PD_LIST" ]; then
    printf "\n\n- %d drive(s) below reported with invalid label:\n\n" $invalid_label_count
    showpd -i -nohdtot $INVALID_LABEL_PD_LIST
fi

printf "\nTested %s disks, Found %s OK, Action required on %s disks\n" $pd_count $((pd_count - invalid_label_count)) $invalid_label_count
