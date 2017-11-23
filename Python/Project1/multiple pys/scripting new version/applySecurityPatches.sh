#!/bin/bash


#######################################################################################
#This script is called by autoyast as a post install script to install the
#the current security patches and HPE addon RPMs.
#We will change the name of the script on the next version.
#######################################################################################


#Log file for this script. This is the location of other logs stored by autoyast.
log="/var/adm/autoinstall/logs/securityPatchUpdate.log"

#Always start with a new log in case the application is rerun.
rm -rf $log
touch $log

#Automatically send stdout and stderr to the log file.
exec 2> $log 
exec 1> $log 

#Mount the image depot from the crash cart.
#The IP used below must be the current IP used by the crash cart
#to interface with the system being installed.
imagedepot="10.23.11.104:/imagedepot"
echo "imagedepot location = ${imagedepot}."

#We try three times to mount, since we have seen issues with mounting.
count=1

while [ true ]; do
	result=$(mount -t nfs -o soft,timeo=30,retrans=2 ${imagedepot} /mnt 2>&1)

	if [[ $? -ne 0 ]]; then
		echo "$result"
		echo "Failed to mount ${imagedepot}, will try again."
		echo "This was attempt number ${count}."
	else
		echo "Successfully mounted ${imagedepot}."
		break
	fi

	((count++))

	if [[ $count -gt 3 ]]; then
		echo "Failed to mount ${imagedepot} after three attempts."
		echo "Application of security patches and additional HPE RPMs failed."
		exit 1
	fi

	sleep 5
done

#Added sleep, since there seem to be some timing issues.
sleep 5

#Location of security patches and add on images.
securityPatchDir="/mnt/SLES_SP3/securityPatches"
addOnRPMsDir="/mnt/SLES_SP3/addOnRPMs"

securityPatchBundlePath=$(ls ${securityPatchDir}/*.tgz)
echo "Security patch bundle path = ${securityPatchBundlePath}."
securityPatchBundle=${securityPatchBundlePath##/*/}

echo "Security patch bundle = ${securityPatchBundle}."

#We try twice to copy images to /tmp.
count=1

while [ true ]; do
	result=$(cp $securityPatchBundlePath /tmp 2>&1)

	if [[ $? -ne 0 ]]; then
		echo "$result"
		echo "Failed to copy ${securityPatchBundlePath} to /tmp."
		echo "This was attempt number ${count}."
	else
		echo "Successfully copied ${securityPatchBundlePath} to /tmp."
		break
	fi

	((count++))

	if [[ $count -gt 2 ]]; then
		echo "Failed to copy ${securityPatchBundlePath} to /tmp after two attempts."
		echo "Application of security patches and additional HPE RPMs failed."
		exit 1
	fi
done

addOnRPMBundlePath=$(ls ${addOnRPMsDir}/*.tgz)
echo "HPE addon RPM bundle path = ${addOnRPMBundlePath}."
addOnRPMBundle=${addOnRPMBundlePath##/*/}

echo "HPE addon RPM patch bundle = ${addOnRPMBundle}."

count=1

while [ true ]; do
	result=$(cp $addOnRPMBundlePath /tmp 2>&1)

	if [[ $? -ne 0 ]]; then
		echo "$result"
		echo "Failed to copy ${addOnRPMBundlePath} to /tmp."
		echo "This was attempt number ${count}."
	else
		echo "Successfully copied ${addOnRPMBundlePath} to /tmp."
		break
	fi

	((count++))

	if [[ $count -gt 2 ]]; then
		echo "Failed to copy ${addOnRPMBundlePath} to /tmp after two attempts."
		echo "Application of security patches and additional HPE RPMs failed."
		exit 1
	fi
done

umount /mnt

cd /tmp

#Location of extracted security RPMs.
addOnRPMDir="/tmp/addOnRPMs"
securityPatchDir="/tmp/securityPatches"

result=$(tar -zxf $addOnRPMBundle 2>&1)

if [[ $? -ne 0 ]]; then
	echo "$result"
	echo "Failed to extract ${addOnRPMBundle}."
	echo "Application of security patches and additional HPE RPMs failed."
	exit 1
else
	echo "Successfully extracted ${addOnRPMBundle}."
fi

result=$(tar -zxf $securityPatchBundle 2>&1)

if [[ $? -ne 0 ]]; then
	echo "$result"
	echo "Failed to extract ${securityPatchBundle}."
	echo "Application of security patches and additional HPE RPMs failed."
	exit 1
else
	echo "Successfully extracted ${securityPatchBundle}."
fi

#Create the patch repository.
result=$(zypper ar -t plaindir $addOnRPMDir addOnRPMs 2>&1)

if [[ $? -ne 0 ]]; then
	echo "$result"
	echo "Failed to add addOnRPMs repository."
	echo "Application of security patches and additional HPE RPMs failed."
	exit 1
else
	echo "Successfully added addOnRPMs repository."
fi

result=$(zypper ar -t plaindir $securityPatchDir securityPatches 2>&1)

if [[ $? -ne 0 ]]; then
	echo "$result"
	echo "Failed to add securityPatches repository."
	echo "Application of security patches and additional HPE RPMs failed."
	exit 1
else
	echo "Successfully added securityPatches repository."
fi

#Update the server with the security patches.
echo "Applying the security patches and HPE addon RPMs to the server."

result=$(zypper -q -n --non-interactive-include-reboot-patches in addOnRPMs:* 2>&1)

if [[ $? -ne 0 ]]; then
	echo "$result"
	echo "Failed to install the HPE addon RPMs."
	echo "Application of security patches and additional HPE RPMs failed."
	exit 1
else
	echo "Successfully installed the HPE addon RPMs."
fi

sleep 5

result=$(zypper -q -n --non-interactive-include-reboot-patches up securityPatches:* 2>&1)

if [[ $? -ne 0 ]]; then
	echo "$result"
	echo "Failed to install the Security Patches."
	echo "Application of security patches and additional HPE RPMs failed."
	exit 1
else
	echo "Successfully installed the Security Patches."
fi

sleep 10

echo "Application of security patches and additional HPE RPMs succeeded."
