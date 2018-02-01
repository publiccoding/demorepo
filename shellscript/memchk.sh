#!/bin/bash
# memchk.sh: Script to get memory information of the cluster
# - It gets %Memused, MemFree, %Swapused, Cached, Slab,fmp_slab,Vmalloc,RSS,UnityR and Memory
#
# Note: tpd_fmp_req slab will be excluded during slab threshold calculations

Version=2.06

TMP_DIR=/tmp
MEMINFO=$TMP_DIR/meminfo.$$
SLABINFO=$TMP_DIR/slabinfo.$$
PS_AUXW=$TMP_DIR/ps_auxw.$$
VMALLOCINFO=$TMP_DIR/VMALLOCINFO.$$
PROC_STATUS=$TMP_DIR/proc_sattus.$$

cleanup()
{
    rm -f $MEMINFO.? $SLABINFO.? $PS_AUXW.? $PROC_STATUS.? $VMALLOCINFO.?
    exit
}

get_meminfo_data()
{
  local file=$1

  onallnodes "cat /proc/meminfo" | grep "[A-Za-z]" | awk -v OUTFILE=$file '
  /^Node .:/ { gsub(/:/, "", $2); node=$2; }
  {
    if ($1 != "Node")
      print $0  > OUTFILE"."node
  }
  '
}

get_slabinfo_data()
{
  local file=$1

  onallnodes "cat /proc/slabinfo" | grep "[A-Za-z]" | awk -v OUTFILE=$file '
  /^Node .:/ { gsub(/:/, "", $2); node=$2; }
  {
    if ($1 != "Node")
      print $0  > OUTFILE"."node
  }
  '
}

get_ps_auxw()
{
  local file=$1

  onallnodes 'ps auxw | cut -c 1-132 | grep -v "^USER" | grep "[A-Za-z]"' | awk -v OUTFILE=$file '
  /^Node .:/ { gsub(/:/, "", $2); node=$2; }
  {
    if ($1 != "Node")
      print $0  > OUTFILE"."node
  }
  '
}

get_proc_status()
{
  local file=$1

  onallnodes 'egrep -h "^Name|^Pid|^VmSize|^VmRSS|^VmSwap|^Threads" /proc/*/status' | grep "[A-Za-z]" | awk -v OUTFILE=$file '
  /^Node .:/ { gsub(/:/, "", $2); node=$2; }
  {
    if ($1 != "Node")
      print $0  > OUTFILE"."node
  }
  '
}

get_vmallocinfo()
{
  local file=$1


  onallnodes "cat /proc/vmallocinfo" | grep "[A-Za-z]" | awk -v OUTFILE=$file '
  /^Node .:/ { gsub(/:/, "", $2); node=$2; }
  {
    if ($1 != "Node")
      print $0  > OUTFILE"."node
  }'
}

process_meminfo()
{
  echo -e "\n($((NUM_CNT++))) Memory Usage Summary(in GB):\n"
  echo -e "Node  MemTotal %MemUsed MemFree %SwapUsed RSSTotal  Cached Vmalloc UnityR fmp_slab SlabUsage   SlabStatus"
  for node in `seq 0 7`; do
    if [ $((online & (1 << node))) -eq 0 ]; then
      continue
    fi

    excl_slab=$(grep tpd_fmp_req $SLABINFO.$node | awk '{ slab+=$2*$4/1024/1024/1024 } END { print slab }')

    RSS_TOT=$(grep -v ^USER $PS_AUXW.$node | awk '{ RSS_sum+=$6 } END { print RSS_sum/1024/1024 }')

    huge_pages_size=$(get_huge_pages_size $MEMINFO.$node)

    VmallocUsed=$(grep -vw ioremap $VMALLOCINFO.$node | awk '{ sum+=$2 } END { print sum/1024 }')
    if [ "$VmallocUsed" == "" ]; then
      VmallocUsed=$(grep -w VmallocUsed $MEMINFO.$node | awk '{ print $2 }')
    fi

    cat $MEMINFO.$node | awk -v node=$node -v excl_slab=$excl_slab -v RSS_TOT=$RSS_TOT \
	-v huge_pages_size=$huge_pages_size -v VmallocUsed=$VmallocUsed '
    /MemTotal:/  { MemTotal=$2 }
    /MemFree:/   { MemFree=$2 }
    /^Cached:/   { Cached=$2/1024/1024 }
    /SwapTotal:/ { SwapTotal=$2 }
    /SwapFree:/  { SwapFree=$2 }
    /Slab:/      {
	Slab=$2

	VmallocUsed=VmallocUsed/1024/1024
        swapused=(1-SwapFree/SwapTotal)*100;
        memused=(1-MemFree/MemTotal)*100;
        slab=Slab/1024/1024;
        unity=huge_pages_size
        memory=(MemTotal - unity) # Excluding Unity memory for slab threshold calculation
        memused=(1-MemFree/memory)*100;
	MemFree=MemFree/1024/1024
        slab=Slab/1024/1024;
        memory=memory/1024/1024;
        memory_total=MemTotal/1024/1024

        # To support various memory models using formula below
        if (memory < 4) { SLAB_MINOR_THRESHOLD=1.5; SLAB_MAJOR_THRESHOLD=1.8 }
        else { SLAB_MINOR_THRESHOLD=memory*.35; SLAB_MAJOR_THRESHOLD=memory*.45 }

        slab2=slab-excl_slab # Subtracting flash cache slab size - to keep earlier slab thresholds

        if (slab2 < SLAB_MINOR_THRESHOLD) { Status="Normal" }
        else if (slab2 < SLAB_MAJOR_THRESHOLD) { Status="Minor" }
        else { Status="Major" }

        printf "%4d %9.3f %8.2f %7.3f %9.2f %8.3f %7.3f %7.3f %6.1f %8.3f %9.3f   %s\n", node, memory, memused, MemFree, swapused, RSS_TOT, Cached, VmallocUsed, unity, excl_slab, slab, Status;
    }'
  done
}

get_huge_pages_size()
{
  local FILE=$1

  val=$(grep -w -e HugePages_Total -e Hugepagesize $FILE | awk '
  /HugePages_Total/	{ HugePages_Total=$NF }
  /Hugepagesize/ {
        Hugepagesize=$(NF-1)
        unity=HugePages_Total*Hugepagesize/1024/1024
	print unity
  }
  ')

  val=${val:=0}
  echo "$val"
}

process_slabinfo()
{
  for node in `seq 0 7`; do
    if [ $((online & (1 << node))) -eq 0 ]; then
      continue
    fi

    echo -e "\nNode ${node}:"
    echo "slab(MB) name              active   objs  size obj/slab pages/slab ..."
    cat $SLABINFO.$node | awk '{printf "%8.2f %s\n", $2*$4/1024/1024, $0}' | sort -nr | head -$count
  done
}

process_vmallocinfo()
{
  for node in `seq 0 7`; do
    if [ $((online & (1 << node))) -eq 0 ]; then
      continue
    fi

    echo -e "\nNode ${node}:"
    echo "vmalloc(MB) virtual address range of the area, size in bytes, caller information of the creator, ..."
    cat $VMALLOCINFO.$node | grep -vw ioremap | awk '{ printf "%7.2f %s\n", $2/1024/1024, $0 }' | sort -nr | head -$count
  done
}

process_ps_auxw()
{
  local KEY=$1 # Column# in "ps auxw" output

  for node in `seq 0 7`; do
    if [ $((online & (1 << node))) -eq 0 ]; then
      continue
    fi

    echo -e "\nNode ${node}:"
    echo "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND"
    cat $PS_AUXW.$node | sort -nrk${KEY} | head -$count
  done
}

process_ps_auxw_rss_total()
{
  for node in `seq 0 7`; do
    if [ $((online & (1 << node))) -eq 0 ]; then
      continue
    fi

    awk -v node=$node '{
      RSSSIZE_total[$11]+=$6
      COMM_count[$11]++
    } END {
      printf "\nNode %d:\n", node
      printf "%-24s %5s %10s\n", "COMMAND", "count", "RSS_SIZE_Total"
      sort="sort -nrk3"
      for (elem in RSSSIZE_total) {
        printf "%-24s %5s %14d\n", elem, COMM_count[elem], RSSSIZE_total[elem] | sort
      }
      close(sort)
    }' $PS_AUXW.$node | head -$count
  done
}

process_proc_swap()
{
  for node in `seq 0 7`; do
    if [ $((online & (1 << node))) -eq 0 ]; then
      continue
    fi

    echo -e "\nNode ${node}:"
    echo "Name                          Pid  Threads       VSZ       RSS      Swap"
    cat $PROC_STATUS.$node | awk '/^Name|^Pid|^VmSize|^VmRSS|^VmSwap|^Threads/ {
        switch ($1) {
	case "Name:"   : Name=$2
		break

        case "Pid:"    : Pid=$2
		break

	case "VmSize:" : VSZ=$2
		break

        case "VmRSS:"  : RSS=$2
		break

	case "VmSwap:" : Swap=$2
		break

	case "Threads:": Threads=$2
		if (VSZ>0)
		  printf "%-24s %8d %8d %9d %9d %9d\n", Name, Pid, Threads, VSZ, RSS, Swap
		Name=""; Pid=""; Threads=""; VSZ=0; RSS=0; Swap=0
		break
	}
      }' | sort -nrk6 | head -$count
  done
}

usage()
{
  local SCRIPT_NAME=$(basename $0)

  echo -e "Usage: $SCRIPT_NAME               # Memory status for every node"
  echo -e "       $SCRIPT_NAME -s [-c Count] # Top <count> Slabs"
  echo -e "       $SCRIPT_NAME -m [-c Count] # Top <count> Vmalloc"
  echo -e "       $SCRIPT_NAME -v [-c Count] # Top <count> VSZ processes"
  echo -e "       $SCRIPT_NAME -r [-c Count] # Top <count> RSS processes"
  echo -e "       $SCRIPT_NAME -p [-c Count] # Top <count> Swap used processes\n"

  echo -e "\t-s        : Slab data for each node"
  echo -e "\t-m        : Vmalloc data for each node"
  echo -e "\t-v        : Process VSZ data for each node"
  echo -e "\t-r        : Process RSS data for each node"
  echo -e "\t-p        : Process Swap usage for each node"
  echo -e "\t-c Count  : Top count slabs/VSZ/RSS for each node (Default: $count)"
  exit 1
}

count=10
vmalloc=0
slabinfo=0
proc_vsz=0
proc_rss=0
proc_swap=0
log=1
while getopts c:hsvrpm arg; do
    case "$arg" in
    m)   vmalloc=1; log=0;;

    s)   slabinfo=1; log=0;;

    v)   proc_vsz=1; log=0;;

    r)   proc_rss=1; log=0;;

    p)	 proc_swap=1; log=0;;

    c)   count="$OPTARG";;

    h)   usage;;

    [?]) usage;;
    esac
done

if [ $count -le 0 ]; then
  count=10
fi

opt_total=$((slabinfo + proc_vsz + proc_rss + proc_swap + vmalloc))
if [ $opt_total -gt 1 ]; then
  echo "ERROR: -m, -s, -v, -r and -p options are mutually exclusive" >&2
  exit 1
fi

TPD=$(showversion -b | grep "Release version" | awk '{ print $3 }')
echo -e "- You are using script version=$Version, TPD=$TPD and running it on $(date)"
echo -e "- clwait: $(clwait)"

#trap cleanup INT QUIT TERM
trap cleanup 0 1 2 3 4 5 6 7 9 15       # handle signals

$(clwait --bash)
NUM_CNT=1

get_meminfo_data $MEMINFO
get_slabinfo_data $SLABINFO
get_ps_auxw $PS_AUXW
get_vmallocinfo $VMALLOCINFO

if [[ $slabinfo -eq 1 || $log -eq 1 ]]; then
  echo -e "\n($((NUM_CNT++))) Top $count slab(s) for each node"
  process_slabinfo
fi

if [[ $vmalloc -eq 1 || $log -eq 1 ]]; then
  echo -e "\n($((NUM_CNT++))) Top $count vmalloc for each node"
  process_vmallocinfo
fi

if [[ $proc_vsz -eq 1 || $log -eq 1 ]]; then
  echo -e "\n($((NUM_CNT++))) Top $count VSZ (Virtual Memory Size) processes for each node"
  process_ps_auxw 5
fi

if [[ $proc_rss -eq 1 || $log -eq 1 ]]; then
  echo -e "\n($((NUM_CNT++))) Top $count RSS (Resident Set Size) processes for each node"
  get_ps_auxw $PS_AUXW
  process_ps_auxw 6

  echo -e "\n($((NUM_CNT++))) Top $count RSS (KB) total size processes on each node basis:"
  process_ps_auxw_rss_total
fi

if [[ $proc_swap -eq 1 || $log -eq 1 ]]; then
  echo -e "\n($((NUM_CNT++))) Top $count Swap usage processes for each node"
  get_proc_status $PROC_STATUS
  process_proc_swap
fi

process_meminfo

exit
