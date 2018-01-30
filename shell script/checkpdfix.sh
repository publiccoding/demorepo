#!/bin/bash
# checkpdfix.sh: Script to find inconsistent LD Raid sets for big drives using at-risk chunklets
# It creates POA script based on the setup and generates VV block mapping report
# Script is written based on 98184, 99124 issues
# It works for TPD=3.1.2.GA/3.1.2.MU1/3.1.2.MU2/3.1.2.MU3/3.1.2.MU5/3.1.3.MU1/3.1.3.MU2/3.2.1.MU2

Version=2.02

# Script is applicable for 3.1.2.GA/3.1.2.MU1/MU2/MU3/MU5/3.1.3.MU1/3.1.3.MU2/3.2.1.MU2 only
TPD="3.1.2.278$|3.1.2.322|3.1.2.422|3.1.2.484|3.1.2.592|3.1.3.230|3.1.3.262|3.2.1.200"

# Version: 2.02
# Enabled script support for 3.1.3.MU2 and 3.2.1.MU2 versions

# Version: 2.01
# Enabled script support for 3.1.2.MU5 and 3.1.3.MU1 versions

# Version: 2.00
# Merging checkpdfix.tcl into this script as here-document. It creates checkpdfix.tcl script for execution
# Earlier downloadable checkpdfix.tcl is depricated

# Version: 1.04
# Cosmetic change of "non-correctable at-risk raid sets" to "at-risk raid sets" at request of service team
# Added -ha mag to createcpg

# Version: 1.03
# On how to run the script?
# - Download checkpdfix.tcl, checkpdfix.sh scripts to InServ then give executable permissions to them
# - Run "./checkpdfix.sh" to find list of inconsistencies, Summary report, VV block mapping report
#   and poa_checkpdfix.sh script

# On how to run poa_checkpdfix.sh script?
# - Run "./poa_checkpdfix.sh" to execute based on the system
# - While running this script it creates /common/support/done_checkpdfix.$FUNC.stage files.
# - stage files tracks which part of the POA is completed.
# - If someone interrupts the script, in the next run it runs where it left out earlier.
# - Before exiting from the script it removes POA function stage files.
# - Note: To clear stage files rerun ./checkpdfix.sh

# About scripts:
# (1) checkpdfix.tcl
# - List of drives big enough to be at-risk and list of LDs using at-risk chunklets
#
# (2) checkpdfix.sh
# - checkpdfix.tcl output data is input for this script
# - List of drives that are big enough to be at-risk
# - List of LDs using at-risk chunklets
# - For each LD Raid set it checks whether it is correctable or not
#   Raid 0/1/5/6 set can tolerate 0, (setsize-1), 1 and 2 bad chunklets
# - If LD raid set is non-correctable then lists impacted VVs based on pd and pdch
# - If LD raid set is correctable then lists correctable VVs based on pd and pdch

# - In summary report it generates below:
# * Number of drives that are big enough to be at-risk
# * Number of drives at-risk chunklets used as spare
# * Number of correctable at-risk raid sets
# * Number of non-correctable at-risk raid sets
# * List of VVs involved in the issue - user need to check whether they are used by Remote Copy or
#   backed up to different media ?
# * List of non-recoverable VVs
# * It creates showblock_report.out for VV block mapping report on all at-risk LD raid sets

# - It creates poa_checkpdfix.sh script based on the configuration. This script resolves big drives
#   at-risk chunklets. This script does below:
# * At-risk chunklets for 3T drive pdch below is 660, For 4T drive pdch below is 1563
# * Verify any chunklet move is pending?
# * Verify any checkld is pending?
# * Set media fail on all the at-risk chunklets. We use controlpd chmederr set <pdch> <wwn>
# * Flush buffer cache by moving temporary full VV to thin VV. It causes vvblock_3phase, which flushes the cache.
#    On tunevv failure script may exit then you need to retry later.
# * On all the at-risk chunklets that are free, create a temporary ld on chunklet <pdch>.
#   We use createld -o <owner> -b <backupowner> <ldname> 0 1 <pdid>:<pdch> to do this.
# * On all the at-risk chunklets that do not contain a temporary ld, relocate the chunklet.
#   We use movech -f -nowait <pdid>:660 to do this.
# * On all the lds, check the each raid set that contained at-risk chunklet.
#   We use checkld -rs <raidset_number> <ld> to do this.
# * If lds using at-risk chunklets that are inconsistent then it fixes them by running command below:
#   We use checkld -y <ld> to do this
# * Remove media fail on all the at-risk chunklets.
#   We use controlpd chmederr unset <pdch> <wwn> to do this.
# * On all the at-risk chunklets that contain a temporary ld, remove the temporary ld.
#   We use removeld -f <ldname> to do this.
# * Checks whether any LDs are left inconsistent?
# * Clean-up earlier created POA function stage files
# * Check any objects (LD, VV, CPG) created by script still present?

TMP_DIR=/tmp
DIR=/common/support
CHECKPDFIX_TCL=$(dirname $0)/checkpdfix.tcl
SHOWBLOCK_REPORT=$PWD/showblock_report.out
POA_CHECKPDFIX=$PWD/poa_checkpdfix.sh

MOVE_PD_PDCH=""
RAIDSET_LD=""
CorrectableCnt=0
NonCorrectableCnt=0

CHECKPDFIX=$TMP_DIR/checkpdfix.$$

function cleanup {
    rm -f $CHECKPDFIX $CHECKPDFIX.ldch $CHECKPDFIX.Impacted_VV $CHECKPDFIX.AllVVs
    rm -f $CHECKPDFIX.showblock
}

function Generate_checkpdfix_tcl()
{

cat <<\EOF
#!/bin/sh
# checkpdfix.tcl: Script to list big drives at-risk PDs, LDs, Spare PDs and Chunklet Size
# Version: 1.00
# Run cli from the user's PATH \
exec cli Tpdcli::runscript "$0" ${1+"$@"}

# clone for debugging

# (C) Copyright 2013 Hewlett-Packard Development Company, L.P

# Note: this code requires Tcl version 8.5 or later since it uses big ints.
# Chunklet size in MiB is available in ::Tpd::tpdconstant(chsize_mb)

namespace eval Checkpdfix {
    variable verbosity 3
    variable diag_range_block 20480 # 10MB
    variable min_block [expr {2 ** 32}]
    variable mask_block [expr {0xffffffff}]
}

# Return a list of pdinfo for drives that are big enough and have a valid id.
# Also creates associative arrays chunk_low(pdid) and chunk_high(pdid)
proc Checkpdfix::filterbig {pdinfol} {
    variable verbosity
    variable diag_range_block
    variable min_block
    variable mask_block
    variable chunk_low
    variable chunk_high

    set npdinfol [list]
    foreach pdinfo $pdinfol {
        set id [Tpd::idConvert [lindex $pdinfo $Tpd::getpdInd(id)]]
        if {$id == "---"} {
            # Skip this PD
            # XXX need better printout
            #Puts "Skipping pd ID $id"
            continue
        }
        set pd_total_chunks [lindex $pdinfo $Tpd::getpdInd(totalchunks)]
        # pd_test_chunk is one past the TOC and last data chunklet
        set pd_test_chunk [expr {$pd_total_chunks + 1}]

        set pd_test_block [expr {$pd_test_chunk * $::Tpd::tpdconstant(chsize_mb) * 2048}]
        if {$pd_test_block + $diag_range_block - 1 < $min_block} {
            # Skip this PD since it is not large enough
            # XXX Add better printout
            continue
        }

        # Need to check this PD
        lappend npdinfol $pdinfo

        set chunk_low($id) [expr {(($pd_test_block & $mask_block) /(2048 * $::Tpd::tpdconstant(chsize_mb))) - 1}]
        set chunk_high($id) [expr {((($pd_test_block + $diag_range_block - 1) & $mask_block) /(2048 * $::Tpd::tpdconstant(chsize_mb))) - 1}]
    }
    return $npdinfol
}

# returns a list of LD names and updates spare pd list to spare_pdl variable
proc Checkpdfix::findMapLds {pdidl} {
    variable chunk_low
    variable chunk_high
    variable spare_pdl [list]

    # get ldDb
    Tpd::getldDb [getld -idnamedomain] [list] id2name

    set ldnamel [list]

    # for each PD, find the LD name for chunklets in the range
    # [chunk_low..chunk_high]
    foreach pdid $pdidl {
        # need to set $Tpd::showsysobjs?
        set pdchl [Tpdcli::getpdch $pdid]
        set chunk_l $chunk_low($pdid)
        set chunk_h $chunk_high($pdid)
#puts "PD: $pdid; LO: $chunk_l; HI: $chunk_h; chunklets: [llength $pdchl]"
        foreach ch $pdchl {
            set pdc [lindex $ch $Tpd::getpdchInd(pdch)]

            # skip if not in range
            if {$pdc < $chunk_l || $pdc > $chunk_h} {
                continue
            }
            set ldid [lindex $ch $Tpd::getpdchInd(ldid)]
            set ldname [Tpd::ldid2name $ldid]

            if {$ldname != "----"} {
                lappend ldnamel $ldname
            }

            # Whether chunklet used as spare?
            set state [lindex $ch $Tpd::getpdchInd(state)]
            set usage [lindex $ch $Tpd::getpdchInd(usage)]
            set media [lindex $ch $Tpd::getpdchInd(media)]

            if {[lindex $ch $Tpd::getpdchInd(spare)] == 1} {
                set spare "Y"
            } else {
                set spare "N"
            }

#puts "PD: $pdid; LO: $chunk_l; HI: $chunk_h; chunklets: [llength $pdchl] usage: $usage spare: $spare"
	    if {($usage == "available")  && ($spare == "Y")} {
		lappend spare_pdl $pdid
	    }
        }; # foreach ch
    }; # foreach pdid

    # cleanup
    unset Tpd::ldDb

    return [lsort -unique $ldnamel]
}

proc Checkpdfix::sleep {time} {
    after $time set end 1
    vwait end
}

proc Checkpdfix::checkld {ldnamel} {
    # now checkld
    set inpreq 0
    foreach LD $ldnamel {
	set cmd "--ld $LD"
        # Input interaction not required
        Tpdcli::iact_cleardata
        set rval [eval Tpdcli::iact_log 0 $inpreq checkld "$cmd"]

        if {[llength $rval] != 0} {
            # set logged_data [Tpdcli::iact_getdata]
            # Tpdcli::iact_getdata is broken!
            set logged_data $Tpdcli::iact_data
            puts "cmd: $cmd: $rval: $logged_data"
        }
    }; # foreach LD

    set ldnamel_temp $ldnamel
    set ldnamel_err [list]

    while {[llength $ldnamel_temp] != 0} {
        set ldnamel_next [list]
# Puts "id name tot_rs ldck_done incons_num"
        foreach LD $ldnamel_temp {
            set ldl [getld $LD]
            set ld [lindex $ldl 0] 
            set id [lindex $ld $Tpd::getldInd(id)]
            set name [lindex $ld $Tpd::getldInd(name)]
            set rtype [lindex $ld $Tpd::getldInd(rtype)]
            set tot_rs [lindex $ld $Tpd::getldInd(tot_rs)]
            set ldck_done [lindex $ld $Tpd::getldInd(ldck_done)]
            set incons_num [lindex $ld $Tpd::getldInd(incons_num)]
# Puts "$id $name $tot_rs $ldck_done $incons_num"

            # check for errors
            if {$incons_num != 0} {
                lappend ldnamel_err [list $LD $incons_num $tot_rs]
            } elseif {$tot_rs != $ldck_done} {
                lappend ldnamel_next $LD; # check again
            } elseif {$rtype == 0} {
                Puts "$LD is RAID 0!"
                incr incons_num
                lappend ldnamel_err [list $LD $incons_num $tot_rs]
            }
        }; # foreach LD
        set ldnamel_temp $ldnamel_next
	Checkpdfix::sleep 1000
    }; # while llength $ldnamel_temp

    if {[llength $ldnamel_err] != 0} {
        Puts "The following LD have errors:"
        set ld_tot 0
        set err_tot 0
        set chk_tot 0
        foreach LD $ldnamel_err {
            set name [lindex $LD 0]
            set err  [lindex $LD 1]
            set chk  [lindex $LD 2]
            Puts "LD $name had $err errors, in $chk chunklets"
            incr ld_tot
            incr err_tot $err
            incr chk_tot $chk
        }; # foreach LD
        Puts "$ld_tot out of [llength $ldnamel] LDs had a total of $err_tot errors"
        exit 1
    }

    Puts "PASS: All at-risk raid sets are consistent."

    return
}

proc Checkpdfix::main {} {
    variable verbosity
    variable diag_range_block
    variable chunk_low
    variable spare_pdl

    set pdinfol [getpd]

    # filter out PDs with invalid IDs
    # and PDs that are too small
    set pdinfol [filterbig $pdinfol]

    set ndrives [llength $pdinfol]
    if {$ndrives == 0} {
        Puts "This system has no drives that are at-risk"
        return
    }
    Puts "This system has $ndrives drives that are big enough to be at-risk.\n"

    Puts "\nChunklet Size (MB): $::Tpd::tpdconstant(chsize_mb)"

    # Get the list of pdids from pdinfol
    set pdidl [Tpdcli::objindexl $pdinfol $Tpd::getpdInd(id)]

    # Now print out PDs
    foreach pdinfo $pdinfol {
        set pdid [Tpd::idConvert [lindex $pdinfo $Tpd::getpdInd(id)]]
	set capacity [lindex $pdinfo $Tpd::getpdInd(capacity)]
	set Size_MB [format "%.0f" [lindex $capacity $Tpd::getpdInd(capacity,total)]]
	set wwn [lindex $pdinfo $Tpd::getpdInd(wwn)]

	set chunk_l $chunk_low($pdid)
	Puts "PD: $pdid $chunk_l $wwn"
    }

    # Get the list of LDs that have chunklets in the bad ranges for any
    # of the PDs

    set ldnamel [findMapLds $pdidl]

    set ldname_cnt [llength $ldnamel]

    if {$ldname_cnt != 0} {
	Puts "\n$ldname_cnt lds using at-risk chunklets:\n"

	# Now print out LDs
	foreach LD $ldnamel {
	    Puts "LD: $LD"
	}
    }

    set spare_cnt [llength $spare_pdl]

    if {$spare_cnt != 0} {
	Puts "\n$spare_cnt spares using at-risk chunklets:\n"

	# Now print Spares
	foreach pdid $spare_pdl {
	    set chunk_l $chunk_low($pdid)
	    Puts "SPAREPD: $pdid $chunk_l"
	}
    }

    if {($ldname_cnt == 0) && ($spare_cnt == 0)} {
	Puts "PASS: No lds or spares are using at-risk chunklets\n"
        exit 0
    }

    #checkld ldnamel ; # It is excluded to avoid longer delays
}

if {[info tclversion] < 8.5} {
        error "You need Tcl 8.5 or later to run this program.  Upgrade the CLI client to 3.1.2 or later."
}

Checkpdfix::main
EOF

}

# In $POA_CHECKPDFIX file add globals and create call_poa_func()
function init_poa_checkpdfix_script {
    local PD_PDCHLIST=$(awk '/^PD:/ {printf "%s:%s ", $2, $3}' $CHECKPDFIX)

    local PDCH_WWNLIST=$(awk '/^PD:/ {printf "%s:%s ", $3, $4}' $CHECKPDFIX)

cat << EOF
#!/bin/bash
# $POA_CHECKPDFIX: This script is generated to run checkpdfix Plan of Actions
PD_FILTER="$PD_FILTER"

PDCH_WWNLIST="$PDCH_WWNLIST"

PD_PDCHLIST="$PD_PDCHLIST"

SPAREPD_PDCHLIST="$SPAREPD_PDCHLIST"

LD_LIST="$LD_LIST"

DIR="$DIR"

EOF

cat <<\EOF
# Function to call POA functions and allow restart
 function call_poa_func {
    local FUNC=$1
    FILE=$DIR/done_checkpdfix.$FUNC.stage

    if [ ! -f $FILE ]; then
	$FUNC
	touch $FILE
    else
	echo -e "\n$FUNC is already complete - skipping"
    fi
 }

EOF
}

# Create controlpd_chmederr_set/unset()
function gen_controlpd_chmederr {
    local set_unset=$1

    if [ "$set_unset" == "set" ]; then
	val="invalid"
    else
	val="valid"
    fi

# In below here doc need \$ for target function
cat <<EOF
# POA function to change media state of required chunklets to $val
 function controlpd_chmederr_$set_unset {
    echo -e "\nRunning controlpd chmederr $set_unset <chunklet#> WWN # For all big drives at-risk chunklets"
    for pdch_wwn in \$PDCH_WWNLIST; do
        pdch=\${pdch_wwn%:*}
        wwn=\${pdch_wwn#*:}
        (set -x; controlpd chmederr $set_unset \$pdch \$wwn)
    done
 }

EOF
}

# Create run_removespare()
function gen_run_removespare {
cat <<\EOF
# POA function to call removespare for PDs using at-risk chunklets as spare
 function run_removespare {
    echo -e "\nRunning removespare for PDs using at-risk chunklets as spare"
    for sparepd_pdch in $SPAREPD_PDCHLIST; do
	(set -x; removespare -f $sparepd_pdch)
    done
 }

EOF
}

# Create run_createspare()
function gen_run_createspare {
cat <<\EOF
# POA function to call createspare to restore earlier spares
 function run_createspare {
    echo -e "\nRunning createspare to restore earlier spares"
    for sparepd_pdch in $SPAREPD_PDCHLIST; do
	(set -x; createspare -f $sparepd_pdch)
    done
 }

EOF
}

# Create run_createld()
function gen_run_createld {
cat <<\EOF
# POA function to run createld for free at-risk chunklets
 function run_createld {
    echo -e "\nRunning cli createld -o <owner> -b <backupowner> <ldname> 0 1 <pdid>:<pdch> # For free at-risk chunklets"

    for pd_pdch in $PD_PDCHLIST; do
	pdid=${pd_pdch%:*}
	pdch=${pd_pdch#*:}
	LDName="checkpdfix_ld.$pdid"

	# Exclude used pds - to avoid errors in createld
	if [ "$MOVE_PD_PDCH" != "" ]; then
	    echo "$MOVE_PD_PDCH" | grep -q " $pdid:"
	    if [ $? -eq 0 ]; then
		continue
	    fi
	fi

	showld -nohdtot $LDName |grep -q " $LDName "
	if [ $? -eq 0 ]; then
	    #echo "WARNING: $LDName pre-existing - skipping createld for PD=$pdid" >&2
	    continue
	fi

	(set -x; cli createld -o 0 -b 1 $LDName 0 1 $pdid:$pdch)
    done
 }

EOF
}

# Create run_removeld()
function gen_run_removeld {
cat <<\EOF
# POA function to run removeld for at-risk chunklets that contain a temporary ld
 function run_removeld {
    echo -e "\nRunning removeld for at-risk chunklets that contain a temporary ld"

    showld -nohdtot checkpdfix_ld.* | while read dummy LDName dummy; do
	(set -x; removeld -f $LDName)
    done
 }

EOF
}

# Create flush_cache()
function gen_flush_cache {
cat <<\EOF
# POA function to run flush cache
 function flush_cache {
    echo -e "\nRunning \"flush buffer cache\" by using vvblock_3phase"
    CPG=checkpdfix_cpg
    VV=checkpdfix_vv

    # clean-up any VV/CPG with checkpdfix_...
    {
    removevv -f $VV
    removecpg -f $CPG
    } >/dev/null 2>&1

    (set -x; createcpg -ha mag -t r1 -p -devtype NL $CPG)
    if [ $? -ne 0 ]; then
        echo "WARNING: \"createcpg -ha mag -t r1 -p -devtype NL $CPG\" failed"

        (set -x; createcpg -ha mag -t r1 $CPG)
        if [ $? -ne 0 ]; then
            echo "ERROR: \"createcpg -ha mag -t r1 $CPG\" failed - contact support"
	    exit 1
        fi
    fi

    (set -x; createvv $CPG $VV 256)
    if [ $? -ne 0 ]; then
        echo "ERROR: \"createvv $VV\" failed - contact support"
        (set -x; removecpg -f $CPG)
        exit 1
    fi

    # Retrying tunevv $retries times on failure. Mainly we noticed it due to "Unable to block vv's" during tunetpvv_3phase_block
    local retries=3
    while : ; do
        (set -x; tunevv usr_cpg $CPG -f -waittask -tpvv $VV)
        ret=$?
        if [ $ret -eq 0 ]; then
            break
        fi

        (( retries -=1 ))
        echo -e "$retries retries left in running tunevv (or) flushing buffer cache\n"
	if [ $retries -eq 0 ]; then
	    break
	fi

        (set -x; sleep 60)
    done
    (set -x; removevv -f $VV)
    (set -x; removecpg -f $CPG)
    if [ $retries -eq 0 ]; then
        echo "ERROR: tunevv failed probably due to heavy IO load - run this script later and/or contact support"
        exit 1
    else
	echo "flushing buffer cache is successful"
    fi
 }

EOF
}

# Create run_movech()
function gen_run_movech {

    # This cannot be computed during init_poa_checkpdfix_script()
    echo -e "MOVE_PD_PDCH=\"$MOVE_PD_PDCH\"\n"

cat <<\EOF
# POA function to Move chunklets which are in use
 function run_movech {

    echo -e "\nRunning move chunklets which are in use"

    for pd_pdch in $MOVE_PD_PDCH; do
	# Due to "chmederr set .." it may already Auto-relocated
	(set -x; movech -f -nowait $pd_pdch 2>&1) |grep -v "Error: Disk .* chunklet .* is not in use."
    done
 }

EOF
}

# Create Verify_showpdch_mov_complete()
function gen_Verify_showpdch_mov_complete {
cat <<\EOF
# POA function to verify move chunklet is complete
 function Verify_showpdch_mov_complete {
    echo -e "\nVerifying whether movech pending?"

    local delay=0
    while : ; do
    	count=$(showpdch -mov -nohdtot 2>/dev/null |awk '{print $1, $2, $3}' |egrep "$PD_FILTER" |wc -l)
    	if [ $count -eq 0 ]; then
	    break
	fi

	echo "$count chunklet(s) still moving (for last $delay sec) - you can interrupt now and run this same script later"
	sleep 30
	((delay += 30))
    done

    echo -e "No chunklet move is pending for LDs using at-risk chunklets"
 }

EOF
}

# Create checkld_raidset()
function gen_checkld_raidset {

    echo -e "RAIDSET_LD=\"$RAIDSET_LD\"\n"

cat <<\EOF
# POA function to run checkld for all LDs at-risk chunklets
 function checkld_raidset {
    if [ "$1" != "checkld" ]; then
        Verify_showpdch_mov_complete
    fi

    echo -e "\nRunning checkld -rs <raidset_number> <ld> # For all LDs at-risk chunklets"

    for raidset_ld in $RAIDSET_LD; do
	RAIDSET_NUM=${raidset_ld%:*}
	LD=${raidset_ld#*:}

	(set -x; checkld -rs $RAIDSET_NUM $LD)
    done
 }

EOF
}

# Create Verify_checkld_complete()
function gen_Verify_checkld_complete {
cat <<\EOF

# POA function to verify checkld completed for at-risk chunklets
 function Verify_checkld_complete {
    echo -e "\nVerify whether checkld pending for at-risk chunklets?"

    local delay=0
    while : ; do
	count=$(showld -ck -nohdtot $LD_LIST |grep checking|wc -l)
	if [ $count -eq 0 ]; then
	    break
	fi

        if [ "$1" == "checkld" ]; then
	    echo "$count raid set(s) LD \"checking\" still in progress (for last $delay sec)"
        else
	    echo "$count raid set(s) LD \"checking\" still in progress (for last $delay sec) - you can interrupt now and run this same script later"
        fi
	sleep 30
	((delay += 30))
    done

    echo -e "No checkld pending for at-risk LDs"
 }

EOF
}

# Create handle_at_risk_inconsistent_lds()
function gen_handle_at_risk_inconsistent_lds {
cat <<\EOF

# POA function to handle at-risk inconsistent LDs
 function handle_at_risk_inconsistent_lds {

    Verify_checkld_complete

    echo -e "\nVerify whether at-risk chunklet LDs are inconsistent - if then handle them"

    inconsistent_cnt=$(showld -ck -nohdtot $LD_LIST |grep inconsistent|wc -l)
    if [ $inconsistent_cnt -ne 0 ]; then
	echo -e "\n$inconsistent_cnt at-risk LDs inconsistent"

	for LD in $(showld -ck -nohdtot $LD_LIST |grep inconsistent |awk '{print $2}'); do
	    (set -x; checkld -y $LD)
	done
    else
	echo -e "\nAll at-risk LDs consistent"
    fi
 }

EOF
}

# Create in calling poa_checkpdfix_functions
function gen_call_poa_checkpdfix_functions {
cat <<\EOF

if [ $# -ne 0 ]; then
    if [[ "$1" == "checkld" && "$RAIDSET_LD" != "" ]]; then
        checkld_raidset "checkld"
        Verify_checkld_complete "checkld"
        (set -x; showld -ck $LD_LIST) | egrep "Detailed_State|inconsistent|no lds listed"
        exit
    else
        echo "Usage: $0 [checkld]" >&2
        echo "Ex1: $0         # Runs full POA" >&2
        echo "Ex2: $0 checkld # Runs checkld only to find any inconsistencies" >&2
        exit 1
    fi
fi

# Plan of action for checkpdfix based on the configuration
echo "Executing plan of action for checkpdfix based on the configuration"

if [ "$LD_LIST" != "" ]; then
    Verify_showpdch_mov_complete
fi

if [ "$RAIDSET_LD" != "" ]; then
    Verify_checkld_complete
fi

call_poa_func controlpd_chmederr_set

if [ "$LD_LIST" != "" ]; then
    call_poa_func flush_cache
fi

if [ "$SPAREPD_PDCHLIST" != "" ]; then
    call_poa_func run_removespare
fi

call_poa_func run_createld

if [ "$LD_LIST" != "" ]; then
    call_poa_func run_movech

    if [ "$RAIDSET_LD" != "" ]; then
	call_poa_func checkld_raidset

	call_poa_func handle_at_risk_inconsistent_lds

        # Verify checkld -y <LD> is complete
	Verify_checkld_complete
    fi
fi

call_poa_func controlpd_chmederr_unset

call_poa_func run_removeld

if [ "$SPAREPD_PDCHLIST" != "" ]; then
    call_poa_func run_createspare
fi

showld -ck -nohdtot |grep -q inconsistent
if [ $? -eq 0 ]; then
    echo "WARNING: Folowing LDs are inconsistent consult support"
    showld -ck |egrep "^Id |inconsistent"
fi

# Clean-up earlier created POA function stage files
rm -f $CHECKLD_RS $DIR/done_checkpdfix.*.stage

{ showld "checkpdfix*"; showvv "checkpdfix*"; showcpg "checkpdfix*"; } | grep -q checkpdfix

if [ $? -eq 0 ]; then
    echo "ERROR: checkpdfix LD/VV/CPG remains - make sure they're removed manually" >&2
    { showld "checkpdfix*"; showvv "checkpdfix*"; showcpg "checkpdfix*"; } | grep checkpdfix >&2
    exit 1
fi

EOF
}

# Map VVs for given raid set based on showblock data
function MapVVList {
    local row_set=$1
    local Correctable=$2

    grep " $row_set$" $CHECKPDFIX.ldch | while read pdid pdch rest; do

	# Map VV Names and block offsets for checkpd diag issue
	((begin=(pdch + 1) * chsize_mb * 1024*(1024/512)))
	((end=begin + 10 * 1024 * (1024 / 512) - 1)) # 10 MB
	
        # Note: Linux awk handles hex values in constant expressions!
        #       Otherwise needs --non-decimal-data

        showblock -nohdtot -d pd $pdid $begin $end |
            awk --non-decimal-data '
$1 == "VV" {
   vv = $3
   block = $4
}
$1 == "PD" {
# Dennis
   if (block == "--" || vv == "") next  # no VV entry
   getline
   # get blocksize by taking diff of first PD entry
   st_en = $3
   i = split(st_en, blk, "-")
   if (i != 2) {
      print "Error in", st_en
      exit 1
   }
   diff = blk[2] - blk[1]
   b_last = block + diff
   printf "%s %s 0x%lX\n", vv, block, b_last
}' > $CHECKPDFIX.showblock

	VVList=$(awk '{ print $1 }' $CHECKPDFIX.showblock |sort -u)

	if [[ "$VVList" != "" && "$VVList" != "---" ]]; then
	    echo "$VVList" >> $CHECKPDFIX.AllVVs
	    (echo "# pd=$pdid pdch=$pdch row-set=$row_set"; cat $CHECKPDFIX.showblock) >> $SHOWBLOCK_REPORT

  	    # If non-correctable then list Impacted VVList based on pd and pdch
	    if [ $Correctable == "No" ]; then
		echo "$VVList" >> $CHECKPDFIX.Impacted_VV
	    fi
	else
	    VVList="None"
	fi

	if [ $Correctable == "Yes" ]; then
	    echo - Correctable VVs=\"${VVList}\" for pd=$pdid, pdch=$pdch
	else
	    echo - Impacted VVs=\"${VVList}\" for pd=$pdid, pdch=$pdch
	fi
    done
    echo

} # MapVVList

# Plan of action for Check PD issue
function checkpd_planofaction {
    local count=$1

    gen_call_poa_checkpdfix_functions >> $POA_CHECKPDFIX
    chmod +x $POA_CHECKPDFIX

    echo -e "\n($count) Created $POA_CHECKPDFIX script to apply plan of action for this setup"
    echo -e "*** Run $POA_CHECKPDFIX to execute Plan of Action ***\n"
    echo "WARNING: During execution of $POA_CHECKPDFIX script operations below are prohibited to avoid conflicting issues."
    echo "AO, create vv/ld, chunklet move, moverelocpd, etc.,"
}

# Check whether given RAID set is correctable or not
function IsRaidsetCorrectable {
    local LD=$1
    local RAID=$2
    local pdchCnt=$3
    local SetSz=$4

    ret="No"

    # Raid 0/1/5/6 set can tolerate 0, (setsize-1), 1 and 2 bad chunklets, respectively
    case $RAID in
    0) ret="No"
       ;;

    1) if [ $pdchCnt -le $((SetSz-1)) ]; then
	    ret="Yes"
       fi
       ;;
    5) if [ $pdchCnt -le 1 ]; then
	    ret="Yes"
       fi
       ;;
    6) if [ $pdchCnt -le 2 ]; then
	    ret="Yes"
       fi
       ;;
    *) echo "ERRROR: Unknown RAID type LD=$LD RAID=$RAID pdchCnt=$pdchCnt SetSz=$SetSz" >&2
	    ret="Unknown"
       ;;
    esac

    echo $ret # Return "Yes"/"No" to know whether RAID set correctable or not
}

function SummaryReport {
    echo "------------------- Summary Report -------------------"

    count=1
    if [ $pdcnt -ne 0 ]; then
	echo -e "\n($count) This system has $pdcnt drives that are big enough to be at-risk."
	((count += 1))
    fi

    if [ "$SPAREPD_PDCHLIST" != "" ]; then
	spare_cnt=$(echo $SPAREPD_PDCHLIST|wc -w)
	echo -e "\n($count) It has $spare_cnt drives at-risk chunklets used as spare"
	((count += 1))
    fi

    if [ $ldcnt -ne 0 ]; then
	echo -e "\n($count) It has $ldcnt LDs using at-risk chunklets"
	((count += 1))
    else
	echo -e "\n($count) No LDs are using at-risk chunklets"
	((count += 1))
    fi

    # For correctable at-risk raid sets
    if [ $CorrectableCnt -ne 0 ]; then
	echo -e "\n($count) INFO: Found $CorrectableCnt correctable at-risk raid sets"
	((count += 1))
    fi

    # For non-correctable at-risk raid sets
    if [ $NonCorrectableCnt -ne 0 ]; then
	echo -e "\n($count) FAIL: Found $NonCorrectableCnt at-risk raid sets"
	((count += 1))
    fi

    if [ -f $CHECKPDFIX.AllVVs ]; then
	sort -u -o $CHECKPDFIX.AllVVs $CHECKPDFIX.AllVVs
	vvcnt2=$(wc -l < $CHECKPDFIX.AllVVs)
	echo -e "\n($count) Check whether $vvcnt2 VVs below are in use by Remote Copy or backed up to different media? If then resync them"
	cat $CHECKPDFIX.AllVVs
	((count += 1))
    fi

    if [ -s $CHECKPDFIX.Impacted_VV ]; then
	sort -u -o $CHECKPDFIX.Impacted_VV $CHECKPDFIX.Impacted_VV
	vvcnt=$(wc -l < $CHECKPDFIX.Impacted_VV)
	echo -e "\n($count) $vvcnt VVs below are impacted due to checkpd issue: (These VVs are non-recoverable \"consult support\" on it.)"
	cat $CHECKPDFIX.Impacted_VV
	((count += 1))
    fi

    if [ -f $SHOWBLOCK_REPORT ]; then
	echo -e "\n($count) $SHOWBLOCK_REPORT for VV block mapping report on all at-risk LD raid sets"
	((count += 1))
    fi

    if [[ $LD_LIST != "" && $CorrectableCnt -eq 0 && $NonCorrectableCnt -eq 0 ]]; then
	echo -e "\n($count) All at-risk raid sets are consistent"
	((count += 1))
    fi

    checkpd_planofaction $count
}

# Make sure sysmgr is up and running
showsysmgr |grep -q "System is up and running"
if [ $? -ne 0 ]; then
        echo "showsysmgr failed: $(showsysmgr)"
	(set -x; showsysmgr -d)
        exit 1
fi

# See if we should check for version compatibility
if [ ! -e $DIR/done_checkpdfix.all_version ]; then
    showversion -b | grep "Release version" | egrep -qw "$TPD"
    if [ $? -ne 0 ]; then
        echo -e "ERROR: Script is not applicable for this release or version\n" >&2
        (set -x; showversion -b)
        exit 1
    fi
fi

echo -e "- You are using script version=$Version\n"

echo "Generating $CHECKPDFIX_TCL script. It'll be used while running $0"
Generate_checkpdfix_tcl > $CHECKPDFIX_TCL
chmod +x $CHECKPDFIX_TCL

# Check whether $CHECKPDFIX_TCL file exists and got executable permissions
if [ ! -x $CHECKPDFIX_TCL ]; then
    echo "ERRROR: $CHECKPDFIX_TCL file is not present or doesn't have executable permissions" >&2
    exit 1
fi

# Avoid in overwriting earlier $SHOWBLOCK_REPORT; if it exists exit from the script
if [ -f $SHOWBLOCK_REPORT ]; then
    echo "ERROR: Script ran earlier move $SHOWBLOCK_REPORT file and rerun again" >&2
    exit 1
fi

mkdir -p $DIR

if [ ! -d $DIR ]; then
    echo "ERROR: Failed to create $DIR directory - fix the issue and rerun it" >&2
    exit 1
fi

#trap cleanup INT QUIT TERM
trap "cleanup;exit" 0 1 2 3 4 5 6 7 9 15       # handle signals

# Remove old files if any to avoid appending to old data
cleanup
rm -f $CHECKLD_RS $DIR/done_checkpdfix.*.stage

# Get big drives and inconsistent LD list
$CHECKPDFIX_TCL > $CHECKPDFIX

# PD filter for big drives only -it contains ^pd pdch data for each drive
PD_FILTER=$(awk '/^PD:/ {if (count) printf "|"; printf "^%s %s ", $2, $3; count++}' $CHECKPDFIX)

if [ "$PD_FILTER" == "" ]; then
    echo "This system has no drives that are at-risk"
    exit
fi

chsize_mb=$(awk '/^Chunklet Size/ {print $NF}' $CHECKPDFIX)

if [ "$chsize_mb" == "" ]; then
    echo "ERROR: Unable to find Chunklet Size (MB) information" >&2
    exit 1
fi

echo -e "Chunklet Size (MB): $chsize_mb\n"

# LD list for LDs using at-risk chunklets
LD_LIST=$(awk '/^LD:/ {printf " %s ", $2}' $CHECKPDFIX)

SPAREPD_PDCHLIST=$(awk '/^SPAREPD:/ {printf "%s:%s ", $2, $3}' $CHECKPDFIX)

init_poa_checkpdfix_script > $POA_CHECKPDFIX

# Generate "controlpd chmederr set <chunklet#> <wwn>" for all > 2 TB drives
gen_controlpd_chmederr set >> $POA_CHECKPDFIX

# Generate controlpd() for all > 2 TB drives
gen_controlpd_chmederr unset >> $POA_CHECKPDFIX

# Generate "removespare <pdid>:<chunklet#>" for all spare > 2 TB drives
gen_run_removespare >> $POA_CHECKPDFIX

# Generate "createspare  <pdid>:<chunklet#>" for all spare > 2 TB drives
gen_run_createspare >> $POA_CHECKPDFIX

# Generate createld() for free at-risk chunklets
gen_run_createld >> $POA_CHECKPDFIX

# Generate run_removeld()
gen_run_removeld >> $POA_CHECKPDFIX

# Generate Verify_showpdch_mov_complete
gen_Verify_showpdch_mov_complete >> $POA_CHECKPDFIX

# Generate Verify_checkld_complete
gen_Verify_checkld_complete >> $POA_CHECKPDFIX

pdcnt=$(grep "^PD:" $CHECKPDFIX |wc -l)
echo -e "This system has $pdcnt drives that are big enough to be at-risk.\n"

ldcnt=$(echo $LD_LIST|wc -w)

# If ldcnt=0 then generate plan of action
if [ $ldcnt -eq 0 ]; then
    SummaryReport
    exit
fi

echo -e "This system has $ldcnt LDs using at-risk chunklets\n"

ldcnt=0

# For each LD figureout whether its raid set is correctable or not?
while read LD; do
    ((ldcnt += 1))
    RAID_SetSz=$(showld -d $LD -nohdtot |awk '{print $4 ":" $10}')
    RAID=${RAID_SetSz%:*}
    SetSz=${RAID_SetSz#*:}

    # Filter required pd and pdch and generate PD, PDCH, Row-Set, ldch information for each ldch
    showldch $LD -nohdtot | awk '{ print $5, $6, $1, $2 "-" $3 }' | egrep "$PD_FILTER" > $CHECKPDFIX.ldch

    raidsetcnt=0
    # For given LD, walk thru each suspected unique row-set combination
    while read pdchCnt row_set; do
	Correctable=$(IsRaidsetCorrectable $LD $RAID $pdchCnt $SetSz)
	if [ "$Correctable" == "Unknown" ]; then
	    exit 1
	fi

	((raidsetcnt += 1))

	printf "$ldcnt.$raidsetcnt) LD=%-16s RAID=%s SetSz=%-2s row-set=%-5s pdchCnt=%-2s Correctable=%s\n" $LD $RAID $SetSz $row_set $pdchCnt $Correctable
 
	MapVVList $row_set $Correctable

	if [ $Correctable == "Yes" ]; then
	  ((CorrectableCnt += 1))
	else
	  ((NonCorrectableCnt += 1))
	fi

	raidset_number=""
	while read pdid pdch ldch rest; do
	    # To clear inconsistencies append to move chunklets script
	    MOVE_PD_PDCH="$MOVE_PD_PDCH $pdid:$pdch"

	    # checkld -rs per raid set
	    if [ "$raidset_number" == "" ]; then
		((raidset_number=ldch / SetSz))
		RAIDSET_LD="$RAIDSET_LD $raidset_number:$LD"
	    fi
	done < <(grep " $row_set$" $CHECKPDFIX.ldch)

    done < <(awk '{print $4}' $CHECKPDFIX.ldch |sort |uniq -c)
done < <(awk '/^LD:/ {print $2}' $CHECKPDFIX)

# Functions generated below uses variables from above while-loop
# Generate run_movech() to move chunklets are in use
gen_run_movech >> $POA_CHECKPDFIX

# Generate checkld_raidset() to check whether they are consistent
gen_checkld_raidset >> $POA_CHECKPDFIX

# Generate handle_at_risk_lds_inconsistent() to handle at-risk inconsistent LDs
gen_handle_at_risk_inconsistent_lds >> $POA_CHECKPDFIX

# Generate flush_cache()
gen_flush_cache >> $POA_CHECKPDFIX

SummaryReport
