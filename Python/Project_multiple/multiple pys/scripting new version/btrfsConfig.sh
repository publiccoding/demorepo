#!/bin/bash


#######################################################################################
#This script is called by autoyast as a post partitioning script to updated fstab
#and modify the btrfs configuration.
#######################################################################################


#Log file for this script. This is the location of other logs stored by autoyast.
log="/var/adm/autoinstall/logs/btrfsConfig.log"

#Always start with a new log in case the application is rerun.
rm -rf $log
touch $log

#Automatically send stdout and stderr to the log file.
exec 2> $log 
exec 1> $log 


##############################################
echo "Getting the root filesystem UUID"
rootUUID=`btrfs filesystem show|awk 'match($0, /uuid:\s+(.+)/, arr) { print arr[1] }'`
echo "The root filesystem UUID = $rootUUID"


##############################################
echo "Getting the by-id reference for /dev/sda4."
disk=`egrep -o -m 1 '/dev/disk/by-id/scsi.+-part' /etc/fstab`"4"
echo "The root filesystem disk = $disk"


##############################################
echo "Updating /etc/fstab so that the btrfs format matches the factory image."
fstabPartitionUpdate="$disk / btrfs defaults 1 1\nUUID=$rootUUID /srv btrfs subvol=@/srv 0 0\nUUID=$rootUUID /opt btrfs subvol=@/opt 0 0\nUUID=$rootUUID /tmp btrfs subvol=@/tmp 0 0\nUUID=$rootUUID /var/spool btrfs subvol=@/var/spool 0 0\nUUID=$rootUUID /var/run btrfs subvol=@/var/run 0 0\nUUID=$rootUUID /var/log btrfs subvol=@/var/log 0 0\nUUID=$rootUUID /var/crash btrfs subvol=@/var/crash 0 0\nUUID=$rootUUID /var/tmp btrfs subvol=@/var/tmp 0 0"

sed -i "s|^\s*UUID.*0\s*$|${fstabPartitionUpdate}|" /etc/fstab

if [[ $? -ne 0 ]]; then
	echo "Failed to update /etc/fstab."
else
	echo "Successfully updated /etc/fstab."
fi


##############################################
#Write out the default file used for snapper.
cat << DEFAULT >/tmp/default
# subvolume to snapshot
SUBVOLUME="/opt"

# filesystem type
FSTYPE="btrfs"

# run daily number cleanup
NUMBER_CLEANUP="yes"

# limit for number cleanup
NUMBER_MIN_AGE="1800"
NUMBER_LIMIT="20"       # don't need 100 snapshots

# create hourly snapshots
TIMELINE_CREATE="yes"

# cleanup hourly snapshots after some time
TIMELINE_CLEANUP="yes"

# limits for timeline cleanup
TIMELINE_MIN_AGE="1800"
TIMELINE_LIMIT_HOURLY="10"
TIMELINE_LIMIT_DAILY="2"   # daily snapshots for two days
TIMELINE_LIMIT_MONTHLY="0" # don't need any monthly
TIMELINE_LIMIT_YEARLY="0"  # don't need yearly

# cleanup empty pre-post-pairs
EMPTY_PRE_POST_CLEANUP="yes"

# limits for empty pre-post-pair cleanup
EMPTY_PRE_POST_MIN_AGE="1800"
DEFAULT


##############################################
#Replace /etc/snapper/config-templates/default.
echo "Replacing /etc/snapper/config-templates/default so that it matches the factory image."

cp -f /tmp/default /etc/snapper/config-templates/default

if [[ $? -ne 0 ]]; then
	echo "Failed to replace /etc/snapper/config-templates/default."
else
	echo "Successfully replaced /etc/snapper/config-templates/default."
fi


##############################################
#Replace /etc/snapper/configs/root with the new template.
echo "Replacing /etc/snapper/configs/root so that it matches the factory image."

cp -f /etc/snapper/config-templates/default /etc/snapper/configs/root

if [[ $? -ne 0 ]]; then
	echo "Failed to replace /etc/snapper/configs/root."
else
	echo "Successfully replaced /etc/snapper/configs/root."
fi


##############################################
#Update /etc/sysconfig/snapper to also snaphost /opt.
echo "Updating /etc/sysconfig/snapper so that snapper also takes a snapshot of /opt."
snapper -c opt create-config /opt

if [[ $? -ne 0 ]]; then
	echo "Failed to add /opt to the snapper configuration."
else
	echo "Successfully added /opt to the snapper configuration."
fi

echo "Done running btrfs filesystem related update tasks."
