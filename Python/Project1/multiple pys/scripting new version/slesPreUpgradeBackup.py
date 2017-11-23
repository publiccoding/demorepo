#!/usr/bin/python

import math
import subprocess
import re
import os
import shutil
import datetime
import logging
import time


RED = '\033[31m'
PURPLE = '\033[35m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BOLD = '\033[1m'
RESETCOLORS = '\033[0m'


'''
The purpose of this script is to do a backup of certain directories before
the SLES 12.1 upgrade is performed so that the backup can be used afterwards
to restore the server's configuration.

Author Bill Neumann
'''

'''
This function is used to check the following:
	1. The program is being ran by root.
	2. The SAP HANA application is not running and /hana/shared is umounted.
	3. There is a enough space for the backup.
'''
def backupPreparation(upgradeWorkingDir, programParentDir):
        logger = logging.getLogger('coeOSUpgradeLogger')

	processor = checkProcessorType()

	#This dictionary holds the resource files resources.
        upgradeResourceDict = {}

        #Get the upgrade resource file data and save it to a dictionary (hash).
        try:
                with open('upgradeResourceFile') as f:
                        for line in f:
                                line = line.strip()

                                #Ignore commented and blank lines.
                                if len(line) == 0 or re.match("^\s*#", line) or re.match('^\s+$', line):
                                        continue
                                else:
					#Remove quotes from resources.
					line = re.sub('[\'"]', '', line)

                                        (key, val) = line.split('=')
                                        key = key.strip()
                                        upgradeResourceDict[key] = re.sub('\s+', '', val)
        except IOError as err:
                logger.error('Unable to access the application\'s resource file \'upgradeResourceFile\'.\n' + str(err))
                print(RED + 'Unable to access the application\'s resource file \'upgradeResourceFile\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                exit(1)
	
	try:
		archiveBackup = upgradeResourceDict['archiveBackup'].split(',')
		
		restorationBackup = upgradeResourceDict['slesRestorationBackup'].split(',')

		sapBackup = upgradeResourceDict['sapBackup'].split(',')

		fstabHANAEntries = upgradeResourceDict['fstabHANAEntries'].split(',')
	except KeyError as err:
		logger.error('The resource key \'' + str(err) + '\' was not present in the application\'s resource file.')
		print(RED + 'The resource key \'' + str(err) + '\' was not present in the application\'s resource file; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                exit(1)

	#The first time through we copy the hpe utility RPMs needed for the post-upgrade to the pre-upgrade working directory.
	hpeUtilitySoftwareRPMDir = upgradeWorkingDir + '/hpeUtilitySoftwareRPMS'

	if not os.path.exists(hpeUtilitySoftwareRPMDir):
		try:
			hpeUtilitySoftwareRPMSDir =  programParentDir + '/hpeUtilitySoftwareRPMS'
			shutil.copytree(hpeUtilitySoftwareRPMSDir, hpeUtilitySoftwareRPMDir)
		except OSError as err:
			logger.error('Unable to copy the utility RPMs from \'' + hpeUtilitySoftwareRPMSDir + '\' to \'' +  hpeUtilitySoftwareRPMDir + '\'.\n' + str(err))
			print(RED + 'Unable to copy the post-upgrade script files from \'' + hpeUtilitySoftwareRPMSDir + '\' to \'' +  hpeUtilitySoftwareRPMDir + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

	#The first time through we copy the add-on file archive needed for the post-upgrade to the pre-upgrade working directory.
	addOnFileArchiveDir = upgradeWorkingDir + '/addOnFileArchive'

	if not os.path.isdir(addOnFileArchiveDir):
		try:
			os.mkdir(addOnFileArchiveDir)

			if processor == 'ivybridge':
				addOnFileArchive = programParentDir + '/addOnFileArchives/' + upgradeResourceDict['ivyBridgeAddOnFileArchive']
			else:
				addOnFileArchive = programParentDir + '/addOnFileArchives/' + upgradeResourceDict['haswellAddOnFileArchive']

			shutil.copy2(addOnFileArchive, addOnFileArchiveDir)
		except OSError as err:
			logger.error('Unable to copy the add on files archive \'' + addOnFileArchive + '\' to \'' +  addOnFileArchiveDir + '\'.\n' + str(err))
			print(RED + 'Unable to copy the add on files archive \'' + addOnFileArchive + '\' to \'' +  addOnFileArchiveDir + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

	#The first time through we copy the conrep file needed for the post-upgrade to the pre-upgrade working directory.
	conrepDir = upgradeWorkingDir + '/conrepFile'

	if not os.path.isdir(conrepDir):
		getConrepFile(programParentDir, conrepDir, processor)

	#Get the server's model, since we don't check SAP HANA related tasks on Serviceguard servers.
	command = 'dmidecode -s system-product-name'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()
	out = out.strip()

	if result.returncode != 0:
		logger.error('Unable to get the server\'s model information.\n' + err + '\n' + out)
		print(RED + 'Unable to get the server\'s model information; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	logger.info('The server\'s model was determined to be: ' + out + '.')

	try:
		systemModel = (re.match('[a-z,0-9]+\s+(.*)', out, re.IGNORECASE).group(1)).replace(' ', '')
	except AttributeError as err:
		logger.error('There was a server model match error when trying to match against \'' + out + '\'.\n' + str(err))
		print(RED + 'There was a server model match error when trying to match against \'' + out + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	#On servers that are not Serviceguard we check if SAP HANA is running and copy the custom global.ini files to subdirectories in the working directory.
	if not ('DL380' in systemModel or 'DL320' in systemModel or 'DL360' in systemModel):
		sidList = checkSAPHANA(upgradeWorkingDir)

	'''
	Save out the server's hostname on servers running SLES, since the way 
	in which the hostname is set has changed.
	'''
	getHostname(upgradeWorkingDir)

	'''
	Save out SAP user information. Also, if sapadm is present and their home 
	directory is present then add their home directory to the restoration 
	archive.
	'''
	if getSAPUserLoginData(upgradeWorkingDir, sidList):
		restorationBackup.append('/home/sapadm')

	#Save out HANA fstab data.
	getHANAFstabData(upgradeWorkingDir, fstabHANAEntries)

	'''
	Only check size of additional directories/files if they exist and 
	add them to the list of directories/files to be restored.
	'''
	for item in sapBackup:
		if os.path.exists(item):
			restorationBackup.append(item)

	#Check to make sure there is enough disk space for the backup.
	backupItems = ' '.join(restorationBackup) + ' ' + ' '.join(archiveBackup)
	checkDiskspace(backupItems)

	#Save out network information.
	createNetworkInformationFiles(upgradeWorkingDir)

	return [restorationBackup, archiveBackup]

#End backupPreparation(upgradeWorkingDir, programParentDir):


'''
This function copies the appropriate conrep file to be used to update the server's BIOS
after the upgrade.
'''
def getConrepFile(programParentDir, conrepDir, processor):
        logger = logging.getLogger('coeOSUpgradeLogger')

        logger.info('Getting the conrep file that will be used during the post-upgrade to update the server\'s BIOS.')
	print(GREEN + 'Getting the conrep file that will be used during the post-upgrade to update the server\'s BIOS.' + RESETCOLORS)

        '''
        Haswell Scale-out and Scale-up use different conrep files, so we need to determine the configuration.
        Haswell Scale-out sytems do not have a controller.
        '''
        if not processor == 'ivybridge':
                command = 'ssacli ctrl all show'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()

                if result.returncode != 0:
                        if re.search('No controllers detected', out, re.MULTILINE|re.DOTALL) == None:
                                logger.error('Could not get the server\'s controller information.\n' + err + '\n' + out)
                        	print(RED + 'Could not get the server\'s  controller information; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                        else:
                                conrepFile = programParentDir + '/conrepFiles/' + processor + '/conrepSU.dat'
                else:
                        conrepFile = programParentDir + '/conrepFiles/' + processor + '/conrepSO.dat'
        else:
                conrepFile = programParentDir + '/conrepFiles/' + processor + '/conrep.dat'

	logger.info('The conrep file was determined to be: ' + conrepFile + '.')

	try:
		renamedConrepFile = conrepDir + '/conrep.dat'
		os.mkdir(conrepDir)
		shutil.copy2(conrepFile, renamedConrepFile)
	except OSError as err:
		logger.error('Unable to copy the conrep file \'' + renamedConrepFile + '\' to \'' +  conrepDir + '\'.\n' + str(err))
		print(RED + 'Unable to copy the conrep file \'' + renamedConrepFile + '\' to \'' +  conrepDir + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

        logger.info('Done getting the conrep file that will be used during the post-upgrade to update the server\'s BIOS.')

#End getConrepFile(programParentDir, conrepDir, processor):


'''
This function save out SAP User login information for restoration after the upgrade.
'''
def getSAPUserLoginData(upgradeWorkingDir, sidList):
        userLoginDataDir = upgradeWorkingDir + '/userLoginData'
	sapadmHomePresent = False	#This is used to determine whether or not /home/sapadm will need to be restored after the upgrade.

        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Getting SAP HANA user account login data.')
	print(GREEN + 'Getting SAP HANA user account login data.' + RESETCOLORS)

	#The user login data is stored in a seperate directory.
        if not os.path.isdir(userLoginDataDir):
                try:
                        os.mkdir(userLoginDataDir)
                except OSError as err:
                        logger.error('Unable to create the pre-upgrade user login data directory \'' + userLoginDataDir + '\'.\n' + str(err))
                        print(RED + 'Unable to create the pre-upgrade user login data directory \'' + userLoginDataDir + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                        exit(1)

	passwordFile = userLoginDataDir + '/passwd'
	shadowFile = userLoginDataDir + '/shadow'
	groupFile = userLoginDataDir + '/group'

	command = 'cat /etc/passwd'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	#Get password file data.
	if result.returncode != 0:
		logger.error('There was a problem getting the password information from /etc/passwd.\n' + err + '\n' + out)
		print(RED + 'There was a problem getting the password information from /etc/passwd; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	passwordList = out.splitlines()

	#This dictionary holds the password information with the user's name as the key to thier password data.
	passwordDict = dict((x.split(':')[0], [x, x.split(':')[3]]) for x in passwordList)

	#Add the sapadm user to the sid list if it is present so that their account data is collected.
	if 'sapadm' in passwordDict:
		sidList.append('SAP')

		logger.info('The SID list was determined to be: ' + str(sidList) + '.')

		#Their home directory should be /home/sapadm and it should be present, but we check its presence just in case.
		if os.path.isdir('/home/sapadm'):
			sapadmHomePresent = True

	#Get shadow file data.
	command = 'cat /etc/shadow'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('There was a problem getting the shadow information from /etc/shadow.\n' + err + '\n' + out)
		print(RED + 'There was a problem getting the shadow information from /etc/shadow; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	shadowList = out.splitlines()

	#This dictionary holds the shadow information with the user's name as the key to thier shadow data.
	shadowDict = dict((x.split(':')[0], x) for x in shadowList)

	#Get group file data.
	command = 'cat /etc/group'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('There was a problem getting the group information from /etc/group.\n' + err + '\n' + out)
		print(RED + 'There was a problem getting the group information from /etc/group; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	groupList = out.splitlines()
	#This dictionary holds the group information with the group ID as the key to the group data.
	groupDict = dict((x.split(':')[2], x) for x in groupList)

	try:
		passwd = open(passwordFile, 'w')
		shadow = open(shadowFile, 'w')
		group = open(groupFile, 'w')

		groupAddedDict = {}

		for sid in sidList:
			sidadm = sid.lower() + 'adm'

			if sidadm in passwordDict:
				passwd.write(passwordDict[sidadm][0] + '\n')
				shadow.write(shadowDict[sidadm] + '\n')

				if not passwordDict[sidadm][1] in groupAddedDict:
					group.write(groupDict[passwordDict[sidadm][1]] + '\n')
					groupAddedDict[passwordDict[sidadm][1]] = None
			else:
				logger.info('The login account information was missing for: ' + sidadm + '.')
				print(RED + 'The login account information was missing for: ' + sidadm + '; fix the problem and try again; exiting program execution.' + RESETCOLORS)
	except IOError as err:
		logger.error('Could not write user account login data.\n' + str(err))
		print(RED + 'Could not write user account login data; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	passwd.close()
	shadow.close()
	group.close()

	logger.info('Done getting SAP HANA user account login data.')

	return sapadmHomePresent
	
#End getSAPUserLoginData(upgradeWorkingDir, sidList):


'''
This function gets the hana related data (/hana/{shared, log, data}...) from /etc/fstab
to be restored after the upgrade.
'''
def getHANAFstabData(upgradeWorkingDir, fstabHANAEntries):
        fstabDataDir = upgradeWorkingDir + '/fstabData'

        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Getting SAP HANA related partition data from \'/etc/fstab\'.')
	print(GREEN + 'Getting SAP HANA related partition data from \'/etc/fstab\'.' + RESETCOLORS)

        if not os.path.isdir(fstabDataDir):
                try:
                        os.mkdir(fstabDataDir)
                except OSError as err:
                        logger.error('Unable to create the pre-upgrade fstab data directory \'' + fstabDataDir + '\'.\n' + str(err))
                        print(RED + 'Unable to create the pre-upgrade fstab data directory \'' + fstabDataDir + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                        exit(1)

	fstabFile = fstabDataDir + '/fstab'

	#Get SAP HANA parition data from /etc/fstab.
	command = 'cat /etc/fstab'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('There was a problem getting the SAP HANA partition data from /etc/fstab.\n' + err + '\n' + out)
		print(RED + 'There was a problem getting the SAP HANA partition data from /etc/fstab; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	fstabDataList = out.splitlines()

	try:
		f = open(fstabFile, 'w')

		for line in fstabDataList:

			if any(fstabHANAEntry in line for fstabHANAEntry in fstabHANAEntries):
				#Skip lines if they are commented out.
				if re.match('\s*#', line) == None:
					f.write(line + '\n')
	except IOError as err:
		logger.error('Could not write HANA fstab data to \'' + fstabFile + '\'.\n' + str(err))
		print(RED + 'Could not write HANA fstab data to \'' + fstabFile + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	f.close()

	logger.info('Done getting SAP HANA related partition data from \'/etc/fstab\'.')
	
#End getHANAFstabData(upgradeWorkingDir, fstabHANAEntries):


'''
This function gets the server's hostname on servers running SLES.
'''
def getHostname(upgradeWorkingDir):
        hostnameDir = upgradeWorkingDir + '/hostnameData'
	hostnameFile = hostnameDir + '/hostname'

        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Getting the server\'s hostname.')
	print(GREEN + 'Getting the server\'s hostname.' + RESETCOLORS)

	hostname = os.uname()[1]

	logger.info('The server\'s hostname was determined to be: ' + hostname + '.')

        if not os.path.isdir(hostnameDir):
                try:
                        os.mkdir(hostnameDir)
                except OSError as err:
                        logger.error('Unable to create the pre-upgrade hostname data directory \'' + hostnameDir + '\'.\n' + str(err))
                        print(RED + 'Unable to create the pre-upgrade hostname data directory \'' + hostnameDir + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                        exit(1)

	try:
		f = open(hostnameFile, 'w')
		f.write(hostname)
	except IOError as err:
		logger.error('Could not write the server\'s hostname \'' + hostname + '\' to \'' + hostnameFile + '\'.\n' + str(err))
		print(RED + 'Could not write server\'s hostname \'' + hostname + '\' to \'' + hostnameFile + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	f.close()

	logger.info('Done getting the server\'s hostname.')
	
#End getHostname(upgradeWorkingDir):


'''
This function confirms that the server being upgraded is an Ivy Bridge or Haswell server.
It also returns the processor type (haswell or ivybridge).
'''
def checkProcessorType():
        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Checking the processor type to ensure it is an Ivy Bridge or Haswell processor.')
	print(GREEN + 'Checking the processor type to ensure it is an Ivy Bridge or Haswell processor.' + RESETCOLORS)

        processorDict = {'62' : 'ivybridge', '63' : 'haswell'}

        command = 'cat /proc/cpuinfo'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('There was a problem getting the cpu information.\n' + err + '\n' + out)
                print(RED + 'There was a problem getting the cpu information; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                exit(1)

        cpudata = out.splitlines()

        for line in cpudata:
                if re.match('\s*model\s+:\s+[2-9]{2}', line) != None:
                        try:
                                processor = processorDict[re.match('\s*model\s+:\s+([2-9]{2})', line).group(1)]
                        except AttributeError as err:
                                logger.error('There was a match error when trying to match against \'' + line + '\'.\n' + str(err))
                                print(RED + 'There was a match error when trying to match against \'' + line + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                                exit(1)
                        except KeyError as err:
                                logger.error('The resource key \'' + str(err) + '\' was not present in the processor dictionary.')
                                print(RED + 'The resource key \'' + str(err) + '\' was not present in the processor dictionar, which means the server is unsupported; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                                exit(1)

                        break

	logger.info('The processor type was determined to be: ' + processor + '.')

	logger.info('Done checking the processor type to ensure it is an Ivy Bridge or Haswell processor.')

	return processor

#End checkProcessorType():


'''
This function checks that there is enough disk space for the backup.
'''
def checkDiskspace(backupItems):
        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Checking to ensure that there is enough disk space for the backup and the backup ISO image and that the overall backup archive does not exceed 3GB.')
	print(GREEN + 'Checking to ensure that there is enough disk space for the backup and the backup ISO image and that the overall backup archive does not exceed 3GB.' + RESETCOLORS)

	#Get the root file system's usage.
	command = 'df /'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	out = out.strip()

	if result.returncode != 0:
		logger.error('Unable to get the root file system\'s usage information.\n' + err + '\n' + out)
		print(RED + 'Unable to get the root file system\'s usage information; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	try:
		#This holds the available disk space reported by 'df' (1K blocks) before it is converted to GB.
		tmpVar = re.match('(.*\s+){3}([0-9]+)\s+', out).group(2)
	except AttributeError as err:
		logger.error('There was a match error when trying to match against \'' + out + '\'.\n' + str(err))
		print(RED + 'There was a match error when trying to match against \'' + out + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	#Available disk space in GB.
	availableDiskSpace = int(math.floor(float(tmpVar)/float(1024*1024)))

	#This gets the disk space used in GB.
	command = 'du -BG -sc ' + backupItems
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		#If this fails it means that a problem other than the file or directory was not present.
		if re.search('No such file or directory', err, re.MULTILINE|re.DOTALL) == None:
			logger.error('Could not get the total disk space used by \'' + backupItems + '\'.\n' + err + '\n' + out)
			print(RED + 'Could not get the total disk space used by the directories/files being backed up; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

	if re.match('.*\s+([0-9]+)G\s+total', out, re.DOTALL|re.IGNORECASE|re.MULTILINE) != None:
		try:
			#Total used is twice the size since there will be a tar image and an ISO image using the space.
			totalUsed = int(re.match('.*\s+([0-9]+)G\s+total', out, re.DOTALL|re.IGNORECASE|re.MULTILINE).group(1)) * 2
		except AttributeError as err:
			logger.error('There was a match error when trying to match against \'' + out + '\'.\n' + str(err))
			print(RED + 'There was a match error when trying to match against \'' + out + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)
	else:
		logger.error('Could not get the total disk space used by \'' + backupItems + '\'.\n' + out)
		print(RED + 'Could not get the total disk space used by the directories/files being backed up; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	#Exit out if the backup is greater than 3GB.
	backupSize = totalUsed/2

	if backupSize > 3:
		logger.error('The current size \'' + str(backupSize) + '\'GB of the backup of \'' + backupItems + '\'; is greater than 3GB.')
		print(RED + 'The current size \'' + str(backupSize) + '\'GB of the backup of \'' + backupItems + '\'; exceeds 3GB; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	#Exit out if the amount of disk space left over is less than 3GB.
	if availableDiskSpace - totalUsed < 3:
		logger.error('There is not enough disk space to make a backup of \'' + backupItems + '\'; available disk space \'' + str(availableDiskSpace) + '\' minus backup total \'' + str(totalUsed) + '\' used is less than 3GB.')
		print(RED + 'There is not enough disk space to make a backup of the directories/files being backed up; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	logger.info('Done checking to ensure that there is enough disk space for the backup and the backup ISO image and that the overall backup archive does not exceed 3GB.')

#End checkDiskspace(backupItems):


'''
This function checks to see if SAP HANA is still running and if /hana/shared
is still mounted.
It also returns a list of active SIDs. 
'''
def checkSAPHANA(upgradeWorkingDir):
        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Checking SAP HANA related components.')
	print(GREEN + 'Checking SAP HANA related components.' + RESETCOLORS)

	#Check if any hdb processes are running, which would indicate that the SAP HANA application is still running.
	command = 'ps -C hdbnameserver,hdbcompileserver,hdbindexserver,hdbpreprocessor,hdbxsengine,hdbwebdispatcher'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode == 0:
		logger.error('SAP HANA is still running.\n' + out)
		print(RED + 'It appears that SAP HANA is still running; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	#Check if /hana/shared is mounted.
	command = 'mount'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('Unable to check if the /hana/shared partition is mounted.\n' + err + '\n' + out)
		print(RED + 'Unable to check if the /hana/shared partition is mounted; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	if re.search('/hana/shared', out, re.MULTILINE|re.DOTALL) == None:
		logger.error('The /hana/shared partition is not mounted.\n' + out)
		print(RED + 'The /hana/shared partition is not mounted; please mount it and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	sidList = getGlobalIniFiles(upgradeWorkingDir)

	#Once the global.ini files are saved out /hana/shared will be unmounted.
	unMountHANAShared()

	logger.info('Done checking SAP HANA related components.')

	return sidList

#End checkSAPHANA(upgradeWorkingDir):


'''
This function gets the global.ini files for the active SAP HANA databases, which is determined by the entries
in /usr/sap/sapservices.
'''
def getGlobalIniFiles(upgradeWorkingDir):
        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Getting the global.ini files for the currently active SIDs from \'/usr/sap/sapservices\'.')

	sidList = []
	sidDirList = []

	#Get /usr/sap/sapservices data, which will be used to identify the SAP HANA SIDs.
	command = 'cat /usr/sap/sapservices'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('Unable to get the SAP HANA SID information.\n' + err + '\n' + out)
		print(RED + 'Unable to get the SAP HANA SID information; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	sapServicesData = out.splitlines()

	for data in sapServicesData:
		if re.match('\s*LD_LIBRARY_PATH\s*=\s*/usr/sap', data):
			try:
				sid = (re.match('\s*LD_LIBRARY_PATH\s*=\s*/usr/sap.*([a-z0-9]{3})adm$', data).group(1)).upper()
			except AttributeError as err:
				logger.error('There was a match error when trying to match against \'' + data + '\'.\n' + str(err))
				print(RED + 'There was a match error when trying to match against \'' + data + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
				exit(1)

			globalIni = '/usr/sap/' + sid + '/global/hdb/custom/config/global.ini'

			sidDir = upgradeWorkingDir + '/' + sid

			if os.path.isfile(globalIni):
				if not os.path.isdir(sidDir):
					try:
						os.mkdir(sidDir)
					except OSError as err:
						logger.error('Unable to create the backup global.ini SID directory \'' + sidDir + '\'.\n' + str(err))
						print(RED + 'Unable to create the backup global.ini SID directory \'' + sidDir + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
						exit(1)

				try:
					shutil.copy2(globalIni, sidDir)
				except OSError as err:
					logger.error('Unable to copy the global.ini to \'' + sidDir + '\'.\n' + str(err))
					print(RED + 'Unable to copy the global.ini to \'' + sidDir + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
					exit(1)
			else:
				logger.warn('A custom global.ini \'' + globalIni + '\' was not present for SID ' + sid + '.')
				print(YELLOW + 'A custom global.ini \'' + globalIni + '\' was not present for SID ' + sid + '.' + RESETCOLORS)

			sidList.append(sid)

	logger.info('The active SID list as determined by \'/etc/services\' was: ' + str(sidList) + '.')

	logger.info('Done getting the global.ini files for the currently active SIDs from \'/usr/sap/sapservices\'.')


	return sidList
				
#End getGlobalIniFiles(upgradeWorkingDir):


'''
This function attempts to unmount /hana/shared.
'''
def unMountHANAShared():
        logger = logging.getLogger('coeOSUpgradeLogger')

	#Check if sapinit is running and shut it down.	
	command = 'service sapinit status'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		if re.search('No process running', out, re.MULTILINE|re.DOTALL|re.IGNORECASE) == None:
			logger.error('Unable to get the status of sapinit.\n' + err + '\n' + out)
			print(RED + 'Unable to get the status of sapinit; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

	if re.search('No process running', out, re.MULTILINE|re.DOTALL|re.IGNORECASE) == None:
		command = 'service sapinit stop'
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			logger.error('Unable to stop the sapinit process.\n' + err + '\n' + out)
			print(RED + 'Unable to stop the sapinit process; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

	#Kill hdbrsutil processes if there are any running.
	command = 'ps -fC hdbrsutil'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	#This means that it was running and needs to be killed.
	if result.returncode == 0:
		command = 'killall -v hdbrsutil'
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			logger.error('Problems were encountered when trying to kill hdbrsutil.\n' + err + '\n' + out)
			print(RED + 'Problems were encountered when trying to kill hdbrsutil; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)
	
	#Need a sleep so that everything is cleaned up before trying to unmount /hana/shared.  Otherwise, it may fail to umount due to a timing issue.
	time.sleep(10.0)

	#Unmount /hana/shared.
	command = 'umount /hana/shared'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('Unable to unmount /hana/shared.\n' + err + '\n' + out)
		print(RED + 'Unable to unmount /hana/shared (Note, /hana/shared needs to be mounted initially when the program runs); fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

#End unMountHANAShared():


'''
This function is used to create NIC data cross reference files that will be used for reference after the
upgrade to make sure the NIC mapping is correct.
'''
def createNetworkInformationFiles(upgradeWorkingDir):
	nicDataFilesDir = upgradeWorkingDir + '/nicDataFiles'

        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Creating the NIC data cross reference files that will be used for reference after the upgrade.')
	print(GREEN + 'Creating the NIC data cross reference files that will be used for reference after the upgrade.' + RESETCOLORS)

	if not os.path.exists(nicDataFilesDir):
		try:
			os.mkdir(nicDataFilesDir)
		except OSError as err:
			logger.error('Unable to create the NIC data directory \'' + nicDataFilesDir + '\'.\n' + str(err))
			print(RED + 'Unable to create the NIC data directory \'' + nicDataFilesDir + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

	#Get the interface and mac address mapping of all NIC cards.
	command = 'ifconfig -a'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('Unable to get NIC card information.\n' + err + '\n' + out)
		print(RED + 'Unable to get NIC card information; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	nicDataList = out.splitlines()

	#This dictionary maps MAC addresses to NIC card names, e.g. {'9c:b6:54:95:74:e8': 'eth0', '9c:b6:54:95:74:ea': 'eth3', '9c:b6:54:95:74:e9': 'eth1'}.
	nicDict = {}

	for data in nicDataList:
		if 'HWaddr' in data:
			try:
				nicList = re.match('\s*([a-z0-9]+)\s+.*HWaddr\s+([a-z0-9:]+)', data, re.IGNORECASE).groups()
			except AttributeError as err:
				logger.error('There was a match error when trying to match against \'' + data + '\'.\n' + str(err))
				print(RED + 'There was a match error when trying to match against \'' + data + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
				exit(1)

			nicDict[nicList[1].lower()] = nicList[0]

	logger.info('The NIC dictionary was determined to be: ' + str(nicDict) + '.')

	#Get the list of bond configuration files.
	command = 'ls /etc/sysconfig/network/ifcfg-bond[0-9]'
		
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('Unable to get bond NIC card configuration files.\n' + err + '\n' + out)
		print(RED + 'Unable to get bond NIC card configuration files; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	nicConfigurationFiles = out.strip().split()

	bondDict = {}

	#Get the bond slave interface information and update the nicDict with corrected mac addresses.
	for configurationFile in nicConfigurationFiles:
		try:
			bondName = re.match('.*(bond[0-9])', configurationFile).group(1)
		except AttributeError as err:
			logger.error('There was a match error when trying to match against \'' + configurationFile + '\'.\n' + str(err))
			print(RED + 'There was a match error when trying to match against \'' + configurationFile + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

		#Get the bond information from proc, which has the actual NIC MAC address informaiton.
		command = 'cat /proc/net/bonding/' + bondName
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			logger.error('Unable to get bond information for \'' + bondName + '\' from proc.\n' + err + '\n' + out)
			print(RED + 'Unable to get bond information \'' + bondName + '\' from proc; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

		procBondingData = out.splitlines()

		#Get the bond's slave interface information.
		command = 'cat ' + configurationFile

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			logger.error('Unable to get NIC card configuration information.\n' + err + '\n' + out)
			print(RED + 'Unable to get NIC card configuration information; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

		configurationData = out.splitlines()

		count = 0 

		for data in configurationData:
			if 'BONDING_SLAVE0' in data:
				slaveZero = re.match('.*=[\s\'"]*([a-z0-9]+)', data).group(1)
				count += 1
			
			if 'BONDING_SLAVE1' in data:
				slaveOne = re.match('.*=[\s\'"]([a-z0-9]+)', data).group(1)
				count += 1

			if count == 2:
				break

		if count != 2:
			logger.error('Unable to get NIC card configuration information, since \'' + bondName + '\' appears to be misconfiured; there should be two slaves configured.')
			print(RED + 'Unable to get NIC card configuration information, since \'' + bondName + '\' appears to be misconfiured; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

		bondDict[bondName] = {} 

		count = 0 

		#Get the bond's interfaces MAC addresses.
		for data in procBondingData:
			if 'Slave Interface' in data:
				slaveInterface = re.match('.*:\s+([a-z0-9]+)', data).group(1)
				continue

			if 'Permanent HW addr' in data:
				macAddress = re.match('.*:\s+([a-z0-9:]+)', data).group(1)
		
				if slaveInterface == slaveZero:
					bondDict[bondName]['BONDING_SLAVE0'] = slaveInterface
				elif slaveInterface == slaveOne:
					bondDict[bondName]['BONDING_SLAVE1'] = slaveInterface
				else:
					logger.error('Unable to get NIC card configuration information, since \'' + bondName + '\' proc information does not match its configuration file.\n' + procBondingData)
					print(RED + 'Unable to get NIC card configuration information, since \'' + bondName + '\' proc information does not match its configuration file; fix the problem and try again; exiting program execution.' + RESETCOLORS)
					exit(1)

				#The NIC dictionary is updated with bond mac addresses, since ifconfig will not report the correct mac address for bonded interfaces.
				nicDict[macAddress] = slaveInterface

				count += 1

		if count != 2:
			logger.error('Unable to get NIC card configuration information, since \'' + bondName + '\' is not reporting two bonded NIC cards.\n' + procBondingData)
			print(RED + 'Unable to get NIC card configuration information, since \'' + bondName + '\' is not reporting two bonded NIC cards; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

	logger.info('The bond dictionary was determined to be: ' + str(bondDict) + '.')

	logger.info('The updated NIC dictionary was determined to be: ' + str(nicDict) + '.')

	#Write out mac address information.
	try:
		macAddressDataFile = nicDataFilesDir + '/macAddressData.dat' 

		f = open(macAddressDataFile, 'w')

		for macAddress in nicDict:
			f.write(nicDict[macAddress] + '|' + macAddress + '\n')
	except IOError as err:
		logger.error('Could not write NIC card mac address information to \'' + macAddressDataFile + '\'.\n' + str(err))
		print(RED + 'Could not write NIC card mac address information to \'' + macAddressDataFile + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	f.close()

	#Write out network bond configuration information.
	count = 0

	try:
		bondConfigurationDataFile = nicDataFilesDir + '/bondConfigurationData.dat' 

		f = open(bondConfigurationDataFile, 'w')

		for bond in bondDict:
			bondData = bond

			for slave in bondDict[bond]:
				bondData += '\n' + slave + '|' +  bondDict[bond][slave]

			if count == 0:
				f.write(bondData + '\n')
				count += 1
			else:
				f.write('\n' + bondData + '\n')
	except IOError as err:
		logger.error('Could not write the bond configuration information to \'' + bondConfigurationDataFile + '\'.\n' + str(err))
		print(RED + 'Could not write the bond configuration information to \'' + bondConfigurationDataFile + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
		exit(1)

	f.close()

	logger.info('Done creating the NIC data cross reference files that will be used for reference after the upgrade.')
	
#End createNetworkInformationFiles(nicDataFilesDir):
	

'''
This function creates the tar arvhive backup of the directories identified
in the backupList variable (List). It is expected that the List contains the
restorationBackupList followed by the archiveBackupList.
'''
def createBackup(backupList, upgradeWorkingDir):
        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Creating the backup archive ISO image.')
	print(GREEN + 'Creating the backup archive ISO image.' + RESETCOLORS)

	archiveDir = upgradeWorkingDir + '/archiveImages'

        if not os.path.isdir(archiveDir):
                try:
                        os.mkdir(archiveDir)
                except OSError as err:
                        logger.error('Unable to create the pre-upgrade archive directory \'' + archiveDir + '\'.\n' + str(err))
                        print(RED + 'Unable to create the pre-upgrade archive directory \'' + archiveDir + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                        exit(1)
	else:
                try:
                        #Always start with an empty archive directory.
                        archiveList = os.listdir(archiveDir)

                        for archive in archiveList:
                                os.remove(archiveDir + '/' + archive)
                except OSError as err:
                        logger.error('Unable to remove old archives in \'' + archiveDir + '\'.\n' + str(err))
                        print(RED + 'Unable to remove old archives in \'' + archiveDir + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                        exit(1)

	hostname = os.uname()[1]
        dateTimestamp = (datetime.datetime.now()).strftime('%d%H%M%b%Y')

	restorationBackupList = [archiveDir + '/' + hostname + '_Restoration_Backup_For_SLES_Upgrade_' + dateTimestamp + '.tar', archiveDir + '/' + hostname + '_Restoration_Backup_For_SLES_Upgrade_' + dateTimestamp + '.tar.gz', archiveDir + '/' + hostname + '_Restoration_Backup_For_SLES_Upgrade_' + dateTimestamp, 'restoration']

	archiveBackupList = [archiveDir + '/' + hostname + '_Archive_Backup_For_SLES_Upgrade_' + dateTimestamp + '.tar', archiveDir + '/' + hostname + '_Archive_Backup_For_SLES_Upgrade_' + dateTimestamp + '.tar.gz', archiveDir + '/' + hostname + '_Archive_Backup_For_SLES_Upgrade_' + dateTimestamp, 'archive']

	count = 0
	#Create a backup image of the directories/files to be restored.
	for backupData in backupList:
		if count == 0:
			backupReferenceList = restorationBackupList
		else:
			backupReferenceList = archiveBackupList

		command = 'tar -cWf ' + backupReferenceList[0] + ' ' + ' '.join(backupData) + ' -C / > /dev/null 2>&1'

		logger.info('The command used to create the \'' + backupReferenceList[3] + '\' tar archive was: ' + command + '.')
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			logger.error('A problem was encountered while creating the pre-upgrade ' + backupReferenceList[3] + ' backup \'' + backupReferenceList[0] + '\' archive.\n' + err + '\n' + out)
			print(RED + 'A problem was encountered while creating the pre-upgrade ' + backupReferenceList[3] + ' backup \'' + backupReferenceList[0] + '\' archive; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

		command = 'gzip ' + backupReferenceList[0]
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			logger.error('A problem was encountered while compressing the pre-upgrade ' + backupReferenceList[3] + ' backup \'' + backupReferenceList[0] + '\' archive.\n' + err + '\n' + out)
			print(RED + 'A problem was encountered while compressing the pre-upgrade ' + backupReferenceList[3] + ' backup \'' + backupReferenceList[0] + '\' archive; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

		count += 1

	count = 0

	for i in range(2):
		if count == 0:
			backupReferenceList = restorationBackupList
		else:
			backupReferenceList = archiveBackupList

		backupMd5sumFile = backupReferenceList[2] + '.md5sum'

		command = 'md5sum ' + backupReferenceList[1] + '> ' + backupMd5sumFile
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			logger.error('Unable to get the md5sum of the backup archive \'' + backupReferenceList[1] + '\'.\n' + err + '\n' + out)
			print(RED + 'Unable to get the md5sum of the backup archive \'' + backupReferenceList[1] + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

		count += 1

	backupISO = upgradeWorkingDir + '/' + hostname + '_Archive_Backup_For_SLES_Upgrade_' + dateTimestamp + '.iso'
	backupISOMd5sumFile = upgradeWorkingDir + '/' + hostname + '_Archive_Backup_For_SLES_Upgrade_' + dateTimestamp + '.md5sum'

        command = 'genisoimage -R -o ' + backupISO + ' ' + upgradeWorkingDir
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('A problem was encountered while creating the pre-upgrade backup \'' + backupISO + '\' ISO image.\n' + err + '\n' + out)
                print(RED + 'A problem was encountered while creating the pre-upgrade backup  \'' + backupISO + '\' ISO image; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                exit(1)

        command = 'md5sum ' + backupISO + ' > ' + backupISOMd5sumFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('A problem was encountered while getting the md5sum of the pre-upgrade backup \'' + backupISO + '\' ISO image.\n' + err + '\n' + out)
                print(RED + 'A problem was encountered while getting the md5sum of the pre-upgrade backup \'' + backupISO + '\' ISO image; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                exit(1)

	logger.info('Done creating the backup archive ISO image.')

	return backupISO

#End createBackup(backupList, upgradeWorkingDir):


'''
This is the main function that calls the other functions to prepare and perform
the pre-upgrade backup.
'''
def main():
	programVersion = '2017.05-rc1'

	#The program can only be ran by root.
	if os.geteuid() != 0:
		print(RED + 'You must be root to run this program; exiting program execution.' + RESETCOLORS)
		exit(1)

        #Change into directory containing the program, which should be the mount point of the ISO image containing the files needed for the upgrade configuration/update.
        try:
                programParentDir = ''

                cwd = os.getcwd()

                programParentDir = os.path.dirname(os.path.realpath(__file__))

                if cwd != programParentDir:
                        os.chdir(programParentDir)
        except OSError as err:
                print(RED + 'Unable to change into the programs parent directory \'' + programParentDir + '\'; fix the problem and try again; exiting program execution.\n' + str(err) + RESETCOLORS)
                exit(1)

	#Get the server's OS distribution version information.
	command = 'cat /proc/version'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		print(RED + 'Unable to get the server\'s OS distribution information; fix the problem and try again; exiting program execution.\n' + err + '\n' + out + RESETCOLORS)
		exit(1)

	#Change version information to lowercase before checking for OS type.
	versionInfo = out.lower()

        if not 'suse' in versionInfo:
                print(RED + 'The OS distribution \'' + versionInfo + '\' is not supported; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                exit(1)

	upgradeWorkingDir = '/tmp/CoE_SAP_HANA_SLES_Upgrade_Working_Dir'

	#The first time through we copy the post-upgrade script files needed for the post-upgrade to the pre-upgrade working directory.
	if not os.path.exists(upgradeWorkingDir):
		try:
			postUpgradeScriptDir = programParentDir + '/postUpgradeScriptFiles'
			shutil.copytree(postUpgradeScriptDir, upgradeWorkingDir)
		except OSError as err:
			print(RED + 'Unable to copy the post-upgrade script files from \'' + postUpgradeScriptDir + '\' to \'' +  upgradeWorkingDir + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
			exit(1)

        #Configure logging.
        dateTimestamp = (datetime.datetime.now()).strftime('%d%H%M%b%Y')

        #Set and create the upgrade working directory if it does not exist.
        logDir = upgradeWorkingDir + '/log'

        if not os.path.isdir(logDir):
                try:
                        os.mkdir(logDir)
                except OSError as err:
                        print(RED + 'Unable to create the pre-upgrade log directory \'' + logDir + '\'; fix the problem and try again; exiting program execution.\n' + str(err) + RESETCOLORS)
                        exit(1)

        #Configure logging.
        dateTimestamp = (datetime.datetime.now()).strftime('%d%H%M%b%Y')

	logFile = logDir + '/SLES_Pre-Upgrade_' + dateTimestamp + '.log'

        handler = logging.FileHandler(logFile)

        logger = logging.getLogger('coeOSUpgradeLogger')

        logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

	logger.info('The program\'s version is: ' + programVersion + '.')

	#The backupList consists of the restoration backup and the archive backup.
	backupList = backupPreparation(upgradeWorkingDir, programParentDir)

	backupISO = createBackup(backupList, upgradeWorkingDir)

	print(GREEN + 'The pre-upgrade backup successfully completed.  Save the file \'' + backupISO + '\' and its md5sum file to another system, since it will be used to restore the server\'s configuration after the upgrade.' + BOLD + PURPLE + '\n\n**** Make sure to copy the ISO in binary format to avoid corrupting the ISO; you should also double check the ISO and its contents before continuing with the upgrade. ****' + RESETCOLORS)

#End main():
	
main()
