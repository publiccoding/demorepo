#!/bin/bash
# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
# move_fw_dir.sh: Relocate the firmware directory from /opt/tpd/fw to /common on 3.2.1.MU3.
#
# To install the 3.2.1.MU3 P48 firmware patch, we need more free space in root partition.
#  
#  - If the free space is not adequate, P48 is subject to installation failure.
#  - To get free space in the root partition, we wrote move_fw_dir.sh script.
#    It moves /opt/tpd/fw to /common/fw_sdaN then links it back to /opt/tpd/fw.
#  - During this procedure, it also checks if we have adequate free space in the /common partition.
#    If not, the script will fail.
#       - The user needs to manually free the space in /common partition.
#       - Estimated free space needed in /common partition is 256MB + /opt/tpd/fw directory size (around 700MB).

Version=1.01

TPD_VERSIONS="3.2.1.MU3"

COPY_DIR="/common/support"
MV_FW_DIR_SCRIPT="$COPY_DIR/__move_fw_dir__"
ALPHABET=({a..z} {A..Z})
INFORMATIONAL=5

usage()
{
    local prog=$(basename $0)

    echo -e "Usage: $prog --install"
    echo -e "       $prog --verify\n"

    echo -e "--install : Move the contents of /opt/tpd/fw to /common if there is not enough room to apply a firmware patch."
    echo -e "--verify  : Check the free space in the / directory and list the firmware directories."
    echo -e "\n"

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
      echo -e "- User command line: $*"
    fi

    echo -e "$(showsys -d | grep "^Nodes in Cluster" | sed -e 's/,/,node/g' | awk '{ printf "- Results below are applicable for node%s\n", $NF }')\n\n"
}

translate_tpd_release_version()
{
    local tpd_release_version="$1"

    echo -e "$tpd_release_version" | grep "^Release version" | sed -e 's/Release version//g' -e 's/[()]//g' | sort -u | awk '
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
        echo -e "ERROR: Insufficient arguments passed to ${FUNCNAME[0]} function - caller: ${FUNCNAME[1]}"
        exit 1
    fi

    local tpd_versions="$1"
    local partition=""

    if [ $# -ge 2 ]; then
        local partition=$2
    fi

    local tpd=$(get_tpd_version $partition)
    echo -e "$tpd" | egrep -qw "$tpd_versions"

    if [ $? -ne 0 ]; then
        echo -e "$(basename $0 .sh): Script is not applicable for $tpd release or version."
        exit 1
    fi
}

is_sysmgr_up()
{
    showsysmgr | grep -q "System is up and running"
    if [ $? -ne 0 ]; then
        echo -e "$SCRIPT: sysmgr is not started."
        (set -x; showsysmgr -d) 2>&1
        exit 1
    fi
}

isallnodesintegrated()
{
    eval $(clwait --bash) # It exports mynode, master, online and integrated
    if [ $integrated -ne $online ]; then
        echo -e "$SCRIPT: Not all nodes integrated. clwait: $(clwait 2>/dev/null)"
        exit 1
    fi
}

generate_script()
{
    # here-doc, no global substitution
    cat << "EOF"
#!/bin/bash

 move_node_fw_dir()
 {
     local option=$1
     local retval=0

     # 256MB in bytes + /opt/tpd/fw required space in /common
     ESTIMATED_SPACE_THRESHOLD=268435456 # units in bytes

     if [ "$option" == "--verify" ]; then
         local link_file="$(ls -ld /opt/tpd/fw | grep ^l)"

         root_free_bytes=$(df -h -B1 / | tail -n 1 | awk '{ print $4 }')
         echo -e "- Free space in / directory: $(( root_free_bytes / 1024 / 1024 ))M"

         common_free_bytes=$(df -h -B1 /common | tail -n 1 | awk '{ print $4 }')
         echo -e "- Free space in /common directory: $(( common_free_bytes / 1024 / 1024 ))M"

         # link_file is a link file, fix is not needed, we can exit
         if [ -n "$link_file" ]; then
             echo -e "- Firmware directory /opt/tpd/fw is already a link file."
             return $retval
         fi

         fw_dir_used=$(du -h -B1 /opt/tpd/fw | tail -n 1 | awk '{ print $1 }')
         est_space_needed=$(( fw_dir_used + ESTIMATED_SPACE_THRESHOLD ))

         # there is not enough space in common to copy the contents of /opt/tpd/fw
         # exit with a failure code
         if [ $est_space_needed -gt $common_free_bytes ]; then
             echo -e "- Error: Not enough free space in /common to copy the contents of /opt/tpd/fw - Consult support."
             retval=1
         fi

         return $retval
     fi

     new_fw=$(df -h / | tail -n 1 | awk '{ print $1 }' | sed -e 's|/dev/||')

     rm -rf /common/fw_$new_fw
     cp -rpP /opt/tpd/fw /common/fw_$new_fw 2>&1

     if [ $? -ne 0 ]; then
         echo -e "- Error: Copying /opt/tpd/fw directory to /common/fw_$new_fw unsuccesful - Consult support."
         retval=1
     else
         rm -rf /opt/tpd/fw
         ln -s /common/fw_$new_fw /opt/tpd/fw

         echo -e "- Successfully moved /opt/tpd/fw directory to /common/fw_$new_fw and created link.\n"
     fi

     return $retval
 }

 if [ $# -ne 1 ]; then
     echo -e "Usage: $0 <--install> || <--verify>"
     echo -e "retval=1"
     exit 1
 fi

 option=$1

 move_node_fw_dir $option
 retval=$?

 echo -e "retval=$retval"
 exit $retval
EOF
}

GetConfirmation()
{
  local MSG="$1"

  GETCONFIRMATION=""
  echo -e "\n$(basename $0 .sh): $MSG"
  while true ; do
    echo -e -n "select y=yes n=no q=quit : "
    read reply
    if [ $reply == "y" ]; then
        GETCONFIRMATION="APPLY-IT"
        echo
        break
    elif [[ $reply == "q" || $reply == "n" ]]; then
        echo -e "- As per user not applying this workaround."
        GETCONFIRMATION="SKIP-IT"
        break
    else
        echo -e "Unrecognized input \"$reply\""
    fi
  done
}

move_fw_dir()
{
    local option=$1
    local retval=0
    ALPHCNT=0

    $(clwait --bash)

    onallnodes "mkdir -p $COPY_DIR" > /dev/null
    generate_script > $MV_FW_DIR_SCRIPT
    chmod +x $MV_FW_DIR_SCRIPT

    # copy the generated script to all other nodes
    onothernodes "rcp node$mynode:$MV_FW_DIR_SCRIPT $MV_FW_DIR_SCRIPT" > /dev/null

    # Run the verify option of the script on all nodes.
    echo -e "${ALPHABET[ALPHCNT++]}) Verifying space availability on each node."

    # run the --verify option
    output=$(onallnodes "$MV_FW_DIR_SCRIPT --verify")

    # check for non-zero return values, indicating an error
    err_check=$(echo "$output" | grep "^retval=" | grep -v "^retval=0")

    if [ -n "$err_check" ]; then
        retval=1
    fi

    # remove internal retval messages
    echo -e "$output" | grep -v "^retval="

    echo -e "\n${ALPHABET[ALPHCNT++]}) Listing off firmware directories:"
    onallnodes 'ls -ld /opt/tpd/fw /common/fw_sda* 2>/dev/null'


    if [[ "$option" == "--verify" || -n "$err_check" ]]; then

        if [ "$option" == "--verify" ]; then
            echo -e "\n${ALPHABET[ALPHCNT++]}) Event log messages with ${FUNCNAME[0]} pattern in last one hour:"
            showeventlog -oneline -debug -min 60 -msg "${FUNCNAME[0]}:"
        fi

        if [[ $retval -ne 0 && "$option" == "--install" ]]; then
            echo -e "\nTo resolve above issues - Consult support."
        fi

        return $retval
    fi

    num_nodes=$(showsys -d | awk '/^Number of Nodes/ { print $NF }')

    # check for existing links, return if all nodes have a link already
    link_num_nodes=$(echo "$output" | grep "already a link file" | wc -l)
    if [ $link_num_nodes -eq $num_nodes ]; then
        echo -e "\nThe workaround has already been applied."
        return $retval
    fi

    #echo -e "${ALPHABET[ALPHCNT++]}) At least one node does not have enough free space in the / directory to apply a firmware patch."

    GetConfirmation "Would you like to apply the workaround to relocate the firmware directories?"

    if [ "$GETCONFIRMATION" == "SKIP-IT" ]; then
        exit 1
    fi

    echo -e "\n${ALPHABET[ALPHCNT++]}) Results of installation stage:"
    for node in {0..7}; do
        if (( (online & (1 << node)) == 0 )); then
            continue
        fi

        echo -e "\nNode $node:"

        output=$(rsh node$node "$MV_FW_DIR_SCRIPT --install" 2>&1)
        echo -e "$output" | grep -v "^retval="

        err_check=$(echo "$output" | grep "^retval=" | grep -v "^retval=0")

        if [ -n "$err_check" ]; then
            retval=1
            break
        fi
    done

    echo -e "\n${ALPHABET[ALPHCNT++]}) Listing off firmware directories:"
    onallnodes 'ls -ld /opt/tpd/fw /common/fw_sda* 2>/dev/null'

    if [ $retval -ne 0 ]; then
        echo -e "\nTo resolve file operation issues - Consult support."
    else
        message="${FUNCNAME[0]}: Successfully relocated firmware directories."
        em_test --severity=$INFORMATIONAL --post="$message" > /dev/null
        echo -e "\n$message"
    fi

    return $retval
}

cleanup()
{
    onallnodes "rm -f $MV_FW_DIR_SCRIPT" > /dev/null
    exit
}

trap cleanup EXIT SIGINT SIGQUIT SIGILL SIGTRAP SIGABRT SIGBUS SIGFPE SIGKILL SIGSEGV SIGTERM # handle signals

if [ $# -ne 1 ]; then
    usage
fi

FS=""
SHOWVERSION_OPT=""

is_sysmgr_up

isallnodesintegrated

get_script_version $0 $*

option=$1

case $option in
    "--install")
        check_tpd_version "$TPD_VERSIONS"
        ;;

    "--verify")
        ;;

    *)
        usage
        ;;
esac

move_fw_dir $option
retval=$?

exit $retval
