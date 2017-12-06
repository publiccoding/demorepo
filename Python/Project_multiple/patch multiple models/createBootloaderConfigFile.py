#!/usr/bin/python

from spUtils import RED, RESETCOLORS
import subprocess
import logging
import os
import shutil
import re
import datetime


'''
This function is used to configure the system's bootloader.
The function returns True on success and False on a failure.
'''
def configureBootLoader(loggerName):
	
	logger = logging.getLogger(loggerName)

	logger.info("Configuring the system's bootloader.")

	#This command should work for all flavors of installations regardless of hardware or OS.
	command = 'rpm -qa kernel-bigsmp-base kernel-default-base kernel'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to get a list of installed kernels was: " + out.strip())

	if result.returncode != 0:
		logger.error("Unable to get the system's installed kernel information.\n" + err)
		return 'Failure'
	else:
		out = out.strip()
		kernelList = out.split()

	logger.debug("The installed kernel list was determined to be: " + str(kernelList))

	try:
		#Get the bootloader type being used (grub or elilo).
                with open('/etc/sysconfig/bootloader') as f:
			 for line in f:
				if "LOADER_TYPE" in line:
					loader = re.match("^.*=\"\s*([a-z,A-Z]+)\".*", line).group(1)
					#Just in case the loader information is not lowercase.
					loader = loader.lower()
					break
        except IOError as err:
		logger.error("Unable to determine the system's loader type.\n" + str(err))
		return 'Failure'
	
	logger.debug("The bootloader type was determined to be: " + loader)

	if loader == 'grub':
		if not configureGrubBootLoader(kernelList, loggerName):
			logger.error("Unable to configure the system's bootloader.")
			return 'Failure'
	else:
		if not configureEliloBootLoader(kernelList, loggerName):
			logger.error("Unable to configure the system's bootloader.")
			return 'Failure'

	logger.info("Done configuring the system's bootloader.")

	return 'Success'

#End configureBootLoader(loggerName):


'''
This function takes the list of installed kernel RPMs which is then used to create 
the bootloader configuration for the grub bootloader.
'''
def configureGrubBootLoader(kernelList, loggerName):

	logger = logging.getLogger(loggerName)

	#Use date to create a time specific backup of the bootloader configuration file.
	dateTimestamp = (datetime.datetime.now()).strftime('%Y%m%d%H%M%S')

	#Make a backup of the current bootloader configuration.
	try:
		shutil.copy2('/boot/grub/menu.lst', '/boot/grub/menu.lst.' + dateTimestamp)
	except IOError as err:
                logger.error("Unable to make a backup of the system's bootloader configuration file.\n" + str(err))
		return False

        #Get the currently used kernel which is used to get the kernel line from the booloader configuration file.
        command = 'uname -r'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to get the currently used kernel was: " + out.strip())

        if result.returncode != 0:
                logger.error("Unable to get the system's current kernel version.\n" + err)
                return False
        else:
                currentKernel = out.strip()

	kernelVersionList = []

	#Strip off the kernel name portion from the kernel package information so we are left with only the version information, e.g. (3.0.101-0.47.55.1).
	for kernelPackage in kernelList:
		kernelVersionList.append(re.match('([a-z]+-){1,4}(.*)', kernelPackage).group(2))

	#This will be a list of the two installed kernels with the highest version.
	finalKernelList = kernelSort(kernelVersionList)

	logger.debug("The final kernel list was determined to be: " + str(finalKernelList))
	
	vmlinuzList = []	
	initrdList = []

	#Format for entries in the bootloader configuration file.
	for kernelVersion in finalKernelList:
		vmlinuzList.append('vmlinuz-' + re.match("([3-5]{1}.*-[0-9]{1,2}(.[0-9]{1,2}){1,2}).[1-9]{1}", kernelVersion).group(1) + '-default')
		initrdList.append('initrd-' + re.match("([3-5]{1}.*-[0-9]{1,2}(.[0-9]{1,2}){1,2}).[1-9]{1}", kernelVersion).group(1) + '-default')

	bootloaderConfig = ['default 0', 'timeout 15']
	gfxmenu = ''

	failsafeResources = 'ide=nodma apm=off noresume edd=off powersaved=off nohz=off highres=off processsor.max+cstate=1 nomodeset x11failsafe'

	try:
		#Get the kernel, initrd and gfxmenu information that is currently being used, which will be used to create the new bootloader configuration file.
                with open('/boot/grub/menu.lst') as f:
			 for line in f:
				line = line.strip()

				logger.debug("The current line of menu.lst = " + line)

				if 'gfxmenu' in line:
					gfxmenu = line
				elif 'kernel' in line and 'resume' in line and currentKernel in line:
					#Remove extra spaces before assigning.
					kernel = re.sub(' +', ' ', line)
					failsafeKernel = re.sub(r'resume=(/[a-z,0-9,-,_]*)+\s+', " " + failsafeResources + " ", kernel)

					#Remove any duplicate entries if present.
					failsafeKernelList = failsafeKernel.split()
					tmpList = []
					objects = set()

					for object in failsafeKernelList:
						if object not in objects:
							tmpList.append(object)
							objects.add(object)

					failsafeKernel = ' '.join(tmpList)
				elif 'initrd' in line:
					initrd = re.sub(' +', ' ', line)

				try:
					if gfxmenu != '' and kernel and initrd:
						break
				except NameError:
					#Ignore the NameError, since it means the variable is not yet defined.
					pass
        except IOError as err:
		logger.error("Unable to access the system's bootloader.\n" + str(err))
                return False

	if gfxmenu != '':
		bootloaderConfig.append(gfxmenu)

	for i in range(2):
			bootloaderConfig.append('')
			bootloaderConfig.append('')
			bootloaderConfig.append('title SAP HANA kernel(' + vmlinuzList[i] + ')')
			bootloaderConfig.append('\t' + re.sub('vmlinuz.*-default', vmlinuzList[i], kernel))
			bootloaderConfig.append('\t' + re.sub('initrd-.*-default', initrdList[i], initrd))
			bootloaderConfig.append('')
			bootloaderConfig.append('title Failsafe SAP HANA kernel(' + vmlinuzList[i] + ')')
			bootloaderConfig.append('\t' + re.sub('vmlinuz.*-default', vmlinuzList[i], failsafeKernel))
			bootloaderConfig.append('\t' + re.sub('initrd-.*-default', initrdList[i], initrd))

	logger.debug("The final grub bootloader configuration was determined to be: " + str(bootloaderConfig))

	#Write out new bootloader configuration file.
	try:
		f = open('/boot/grub/menu.lst', 'w')

		for item in bootloaderConfig:
			f.write(item + '\n')
	except IOError as err:
                logger.error("Unable to write the system's bootloader configuration file.\n" + str(err))
		return False

	f.close()

	return True

#End configureGrubBootLoader(kernelList, loggerName):
	

'''
This function takes the list of installed kernel RPMs which is then used to create 
the bootloader configuration for the elilo bootloader.
'''
def configureEliloBootLoader(kernelList, loggerName):

	logger = logging.getLogger(loggerName)

	#Use date to create a time specific backup of the bootloader configuration file.
	dateTimestamp = (datetime.datetime.now()).strftime('%Y%m%d%H%M%S')

	#Make a backup of the current bootloader configuration.
	try:
		shutil.copy2('/etc/elilo.conf', '/etc/elilo.conf.' + dateTimestamp)
	except IOError as err:
                logger.error("Unable to make a backup of the system's bootloader configuration file.\n" + str(err))
		return False

        #Get the currently used kernel which is used to determine the kernel suffix and current kernel that may be listed in elilo.conf.
        command = 'uname -r'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to get the currently used kernel was: " + out.strip())

        if result.returncode != 0:
                logger.error("Unable to get the system's current kernel version.\n" + err)
                return False
        else:
                currentKernel = out.strip()

	#Get suffix of kernel, since Superdome has -bigsmp and other systems have -default.
	kernelSuffix = re.match('.*(-default|-bigsmp)', currentKernel).group(1)

	#Now rename to the vmlinuz name. Also, note that /boot/vmlinuz will be a link to the current kernel.
	currentKernel = 'vmlinuz-' + currentKernel

	kernelVersionList = []

	#Strip off the kernel name portion from the kernel package information so we are left with only the version information, e.g. (3.0.101-0.47.55.1).
	for kernelPackage in kernelList:
		kernelVersionList.append(re.match('([a-z]+-){1,4}(.*)', kernelPackage).group(2))

	#This will be a list of the two installed kernels with the highest version.
	finalKernelList = kernelSort(kernelVersionList)

	logger.debug("The final kernel list was determined to be: " + str(finalKernelList))
	
	vmlinuzList = []	
	initrdList = []

	#Format for entries in the bootloader configuration file.
	for kernelVersion in finalKernelList:
		vmlinuzList.append('vmlinuz-' + re.match("([3-5]{1}.*-[0-9]{1,2}(.[0-9]{1,2}){1,2}).[1-9]{1}", kernelVersion).group(1) + kernelSuffix)
		initrdList.append('initrd-' + re.match("([3-5]{1}.*-[0-9]{1,2}(.[0-9]{1,2}){1,2}).[1-9]{1}", kernelVersion).group(1) + kernelSuffix)

	logger.debug("The kernel list was determined to be: " + str(vmlinuzList))
	logger.debug("The initrd list was determined to be: " + str(initrdList))

	bootloaderConfig = ['timeout = 150', 'secure-boot = on', 'prompt']

	failsafeResources = 'ide=nodma apm=off noresume edd=off powersaved=off nohz=off highres=off processsor.max+cstate=1 nomodeset x11failsafe'

	#Read elilo.conf into an array, since we have to search for the kernel twice.
	try:
                f = open('/boot/efi/EFI/SuSE/elilo.conf', 'r')
		eliloConfData = f.readlines()
		f.close()
        except IOError as err:
		logger.error("Unable to access the system's bootloader.\n" + str(err))
                return False

	logger.debug("The elilo.conf data was determined to be: " + str(eliloConfData))

	kernelPresent = 'no'

	for line in eliloConfData:
		if 'image' in line and currentKernel in line:
			kernelPresent = 'yes'

	#This means that the kernel's full name was not present.  Thus, the kernel must be referenced by 'vmlinuz'.
	if kernelPresent == 'no':
		currentKernel = 'vmlinuz'

	logger.debug("The current kernel reference in elilo.conf was determined to be: " + currentKernel)

	currentKernelPattern = re.compile(currentKernel + '\s*$')

	#Get the kernel, and initrd information that is currently being used, which will be used to create the new bootloader configuration file.
	for line in eliloConfData:
		line = line.strip()

		if 'image' in line and re.search(currentKernelPattern, line):
			#Remove extra spaces before assigning.
			kernel = re.sub(' +', ' ', line)
		elif 'initrd' in line:
			initrd = re.sub(' +', ' ', line)
		elif 'root' in line and not 'append' in line:
			root = re.sub(' +', ' ', line)
		elif 'append' in line and not 'noresume' in line:
			append = re.sub(' +', ' ', line)
			#Remove the extra space around the quotes at the beginning and end of append line.
			append = re.sub('" ', '"', append)
			append = re.sub(' "$', '"', append)
			failsafeAppend = re.sub(r'resume=(/[a-z,0-9,-,_]*)+\s+', " " + failsafeResources + " ", append)

			#Remove any duplicate entries if present.
			failsafeAppendList = failsafeAppend.split()
			tmpList = []
			objects = set()

			for object in failsafeAppendList:
				if object not in objects:
					tmpList.append(object)
					objects.add(object)

			failsafeAppend = ' '.join(tmpList)
		try:
			if kernel and initrd and root and append:
				break
		except NameError:
			#Ignore the NameError, since it means the variable is not yet defined.
			pass

	for i in range(2):
			bootloaderConfig.append('')
			bootloaderConfig.append('')
			bootloaderConfig.append(re.sub('vmlinuz.*', vmlinuzList[i], kernel))
			bootloaderConfig.append('\tlabel = Linux_' + str(i+1))
			bootloaderConfig.append('\tdescription = "SAP HANA kernel(' + vmlinuzList[i] + ')"')
			bootloaderConfig.append('\t' + append)
			bootloaderConfig.append('\t' + re.sub('= initrd.*', '= /boot/' + initrdList[i], initrd))
			bootloaderConfig.append('\t' + root)
			bootloaderConfig.append('')
			bootloaderConfig.append(re.sub('vmlinuz.*', vmlinuzList[i], kernel))
			bootloaderConfig.append('\tlabel = Linux_Failsafe_' + str(i+1))
			bootloaderConfig.append('\tdescription = "Failsafe SAP HANA kernel(' + vmlinuzList[i] + ')"')
			bootloaderConfig.append('\t' + failsafeAppend)
			bootloaderConfig.append('\t' + re.sub('= initrd.*', '= /boot/' + initrdList[i], initrd))
			bootloaderConfig.append('\t' + root)

	logger.debug("The final elilo bootloader configuration was determined to be: " + str(bootloaderConfig))

	#Write out new bootloader configuration file.
	try:
		f = open('/etc/elilo.conf', 'w')

		for item in bootloaderConfig:
			f.write(item + '\n')
	except IOError as err:
                logger.error("Unable to write the system's bootloader configuration file.\n" + str(err))
		return False

	f.close()

        #Install the new elilo configuration.
        command = '/sbin/elilo'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to install the new elilo bootloader was: " + out.strip())

        if result.returncode != 0:
                logger.error("Unable to install/update the system's bootloader.\n" + err)
                return False

	return True

#End configureEliloBootLoader(kernelList, loggerName):


'''
This function returns a list of kernels that will be used, with the highest version first in the list.
'''
def kernelSort(verList):
        versionList = []
        revisionList = []
        finalVersionList = verList

        for ver in verList:
                version, revision = re.split('-', ver)
                versionList.append(re.sub('\.', '', version))
                revisionList.append(re.sub('\.', '', revision))

        versionList = map(int, versionList)
        revisionList = map(int, revisionList)

        for j in range(len(versionList)):
                for i in range(j+1, len(versionList)):
                        if versionList[i] > versionList[j] or (versionList[i] == versionList[j] and revisionList[i] > revisionList[j]):
                                versionList[i], versionList[j] = versionList[j], versionList[i]
                                revisionList[i], revisionList[j] = revisionList[j], revisionList[i]
                                finalVersionList[i], finalVersionList[j] = finalVersionList[j], finalVersionList[i]
        del finalVersionList[2:]

	return finalVersionList

#End kernelSort(verList):


'''
#This section is for running the module standalone for debugging purposes.  Uncomment to use.
if __name__ == '__main__':

	#Setup logging.
	loggerName = 'testLogger'
	logger = logging.getLogger(loggerName)
	logFile = 'configureBootLoader.log'

        try:
                open(logFile, 'w').close()
        except IOError:
                print RED + "Unable to access " + logFile + " for writing." + RESETCOLORS
                exit(1)

        handler = logging.FileHandler(logFile)

	logger.setLevel(logging.DEBUG)
	handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

	configureBootLoader(loggerName)
'''
