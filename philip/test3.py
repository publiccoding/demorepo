#!/usr/bin/python

import logging
import optparse
import os
import re
import subprocess
import binascii

import computeNode

def getFirmwareDict(csurData):
	started = False
	firmwareDict = {}

	log("Begin Getting Firmware Dictionary", "info")

	for data in csurData:
		if not re.match(r'Firmware.*', data) and not started:
			continue
		elif re.match(r'Firmware.*', data):
			started = True
			continue
		elif re.match(r'\s*$', data):
			break
		else:
			firmwareList = data.split('|')
			firmwareDict[firmwareList[0].strip()] = firmwareList[1].strip()

	log("firmwareDict = " + str(firmwareDict), "debug")
	log("End Getting Firmware Dictionary", "info")
	return firmwareDict
#End getFirmwareDict(csurData)

def getStorageFirmwareInventory(firmwareDict, updateList):
	count = 0
	hardDriveModels = []
	hardDriveDict = {}
	hardDriveUpdateDict = {}

	fh = open(gapAnalysisFile, 'w')
	
	log("Begin Getting Storage Firmware Inventory", "info")
	log("firmwareDict = " + str(firmwareDict), "debug")
	log("updateList = " + ":".join(updateList), "debug")

	fh.write(conversion("Firmware:\n"))

	#hpacucli has been replaced by hpssacli so we need to check in case we are on an older system.
	if os.path.isfile('/usr/sbin/hpssacli'):
		arrayCfgUtilFile = '/usr/sbin/hpssacli'
	else:
		arrayCfgUtilFile = '/usr/sbin/hpacucli'

	log("arrayCfgUtilFile = " + arrayCfgUtilFile, "debug")

	#Get list of storage controllers.
	command = arrayCfgUtilFile + " ctrl all show status|egrep -o \"P.*Slot\s*[0-9]{1,2}\"|awk '{print $1\":\"$NF}'"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if err != '':
		log(err, "error")	
	log("out = " + out, "debug")
	
	controllerList = out.splitlines()	

	for controller in controllerList:
		controllerModel = controller[0:controller.index(':')]
		controllerSlot = controller[controller.index(':')+1:len(controller)]

		csurFirmwareVersion = firmwareDict.get(controllerModel)

		command = arrayCfgUtilFile + " ctrl slot=" + controllerSlot + " show |grep \"Firmware Version\"|awk '{print $3}'"

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			log(err, "error")	
		log("out = " + out, "debug")

		installedFirmwareVersion = out.strip()
		
                if installedFirmwareVersion != csurFirmwareVersion:
			updateList.append(controllerModel)

		fh.write(conversion(controllerModel + "|" + csurFirmwareVersion + "|" + installedFirmwareVersion + "\n"))

		if controllerModel == 'P812':
			csurFirmwareVersion = firmwareDict.get('D2700')
			command = arrayCfgUtilFile + " ctrl slot=" + controllerSlot + " enclosure all show  detail|grep -m 1  \"Firmware Version\"|awk '{print $3}'"
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if err != '':
				log(err, "error")	
			log("out = " + out, "debug")

			installedFirmwareVersion = out.strip()
			
			if installedFirmwareVersion != csurFirmwareVersion:
				updateList.append('D2700')

			fh.write(conversion("D2700|" + csurFirmwareVersion + "|" + installedFirmwareVersion + "\n"))
		
		#Get a list of all hard drives and thier firmware version.
		command = arrayCfgUtilFile + " ctrl slot=" + controllerSlot + " pd all show detail|grep -A 2 --no-group-separator \"Firmware Revision\"|grep -v Serial|sed -e '$!N;s/\\n/ /'|awk '{print $6, $3}'|sort -k1"

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			log(err, "error")	
		log("out = " + out, "debug")

		hardDriveList = out.splitlines()

		#Get a unique list of hard drives managed by the controller.
		for hd in hardDriveList:
			hardDriveData = hd.split()

			if count == 0:
				hardDriveModels.append(hardDriveData[0].strip())
				tmpHardDriveModel = hardDriveData[0]
				count += 1
			elif hardDriveData[0] != tmpHardDriveModel:
				hardDriveModels.append(hardDriveData[0].strip())
                        	tmpHardDriveModel = hardDriveData[0]

		#Now check each hard drive's firmware version.
		for hardDriveModel in hardDriveModels:
			count = 0	

			csurFirmwareVersion = firmwareDict.get(hardDriveModel)

			#This acounts for the cases where the CSUR did not include a hard drive's firmware.
			if csurFirmwareVersion is None:
				if not hardDriveDict.has_key(hardDriveModel):
					hardDriveDict[hardDriveModel] = ''
					csurFirmwareVersion = 'Missing'
					fh.write(conversion(hardDriveModel + "|" + csurFirmwareVersion + "| \n"))
				continue
	
			for hd in hardDriveList:
				hardDriveData = hd.split()
				if hardDriveData[0].strip() == hardDriveModel:
					if hardDriveData[1].strip() != csurFirmwareVersion:
						if not hardDriveDict.has_key(hardDriveModel):
							hardDriveDict[hardDriveModel] = ''
							if not hardDriveUpdateDict.has_key(hardDriveModel):
								updateList.append(hardDriveModel)	
							fh.write(conversion(hardDriveModel + "|" + csurFirmwareVersion + "|" + hardDriveData[1].strip() + "\n"))
							count += 1
						break

			if count == 0:
				if not hardDriveDict.has_key(hardDriveModel):
					hardDriveDict[hardDriveModel] = ''
					fh.write(conversion(hardDriveModel + "|" + csurFirmwareVersion + "|" + driveData[1].strip() + "\n"))

		#Clear the list for the next iteration.
		hardDrives = []
	fh.close()
	log("End Getting Storage Firmware Inventory", "info")
#End getStorageFirmwareInventory(firmwareDict, updateList)


def getNICFirmwareInventory(firmwareDict, updateList):
	nicCardModels = []
	count = 0

	log("Begin Getting NIC Firmware Inventory", "info")
	log("firmwareDict = " + str(firmwareDict), "debug")
	log("updateList = " + ":".join(updateList), "debug")

	command = "lspci -v|grep -B1 NC --no-group-separator|sed -e '$!N;s/\\n/ /'|uniq -w 2|egrep -io \".{2}:.{2}\.[0-9]{1}|NC[0-9]+[a-z]{1,3}\"|sed -e '$!N;s/\\n/ /'| sort -k2"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	if err != '':
		log(err, "error")	
	log("out = " + out, "debug")

        nicCardList = out.splitlines()

	#Get a unique list of nic cards.
	for nd in nicCardList:
		nicCardData = nd.split()

		if count == 0:
			nicCardModels.append(nicCardData[1].strip())
			tmpNicCardModel = nicCardData[1]
			count += 1
		elif nicCardData[1] != tmpNicCardModel:
			nicCardModels.append(nicCardData[1].strip())
			tmpNicCardModel = nicCardData[1]

	#Get hwinfo which will be used to map nic card bus to nic device.
	fh = open("hwinfo.log", 'w')
	subprocess.call(["hwinfo", "--network"], stdout=fh)
	fh.close()

	fh = open(gapAnalysisFile, 'a')

	#Loop through all nic cards to check thier firmware.  Only recoed one occcurance of a mismatch.
	for nicCardModel in nicCardModels:
		count = 0
		csurNicCardFirmwareVersion = firmwareDict.get(nicCardModel)

		for data in nicCardList:
			nicCardData = data.split()

			nicBus = nicCardData[0].strip()
			installedNicCardModel = nicCardData[1].strip()

			if installedNicCardModel == nicCardModel: 

				command = "grep -A 5 " + nicBus + " hwinfo.log|grep \"Device File\"|awk '{print $3}'"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if err != '':
					log(err, "error")	
				log("out = " + out, "debug")

				nicDevice = out.strip()

				command = "ethtool -i " + nicDevice + "|grep firmware-version|awk '{print $NF}'"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if err != '':
					log(err, "error")	
				log("out = " + out, "debug")
			
				installedFirmwareVersion = out.strip()
	
				if installedFirmwareVersion != csurNicCardFirmwareVersion and count == 0:
					updateList.append(nicCardModel)
					fh.write(conversion(nicCardModel + "|" + csurNicCardFirmwareVersion + "|" + installedFirmwareVersion + "\n"))
					count += 1
					break

		if count == 0:
			fh.write(conversion(nicCardModel + "|" + csurNicCardFirmwareVersion + "|" + installedFirmwareVersion + "\n"))
	os.remove("hwinfo.log")
	fh.close()
	log("End Getting NIC Firmware Inventory", "info")
#End getNICFirmwareInventory(firmwareDict, updateList)


def getRemainingFirmwareInventory(firmwareDict, updateList, systemModel):
	fh = open(gapAnalysisFile, 'a')

	log("Begin Getting Remaining Firmware Inventory", "info")
	log("firmwareDict = " + str(firmwareDict), "debug")
	log("updateList = " + ":".join(updateList), "debug")
	
	#BIOS
	command = "dmidecode -s bios-release-date"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if err != '':
		log(err, "error")	
	log("out = " + out, "debug")
			
	biosFirmwareDate = out.strip()
	biosFirmwareDateList = biosFirmwareDate.split('/')
	installedFirmwareVersion = biosFirmwareDateList[2] + '.' + biosFirmwareDateList[0] + '.' + biosFirmwareDateList[1]

	if systemModel == 'DL580':
		firmwareType = 'BIOSDL580'
		csurFirmwareVersion = firmwareDict.get(firmwareType)	
	elif systemModel == 'DL980':
		firmwareType = 'BIOSDL980'
		csurFirmwareVersion = firmwareDict.get(firmwareType)	
	elif systemModel == 'BL680c':
		firmwareType = 'BIOSBL680c'
		csurFirmwareVersion = firmwareDict.get(firmwareType)	

	if installedFirmwareVersion != csurFirmwareVersion:
		updateList.append(firmwareType)

	fh.write(conversion(firmwareType + "|" + csurFirmwareVersion + "|" + installedFirmwareVersion + "\n"))

	#iLO
	command = "hponcfg -g|grep \"Firmware Revision\"|awk '{print $4}'"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if err != '':
		log(err, "error")	
	log("out = " + out, "debug")

	installedFirmwareVersion = out.strip()
		
	if installedFirmwareVersion != firmwareDict.get('iLO'):
		updateList.append('iLO')

	fh.write(conversion('iLO' + "|" + firmwareDict.get('iLO') + "|" + installedFirmwareVersion + "\n"))

	#Fusion-IO
	if systemModel != 'BL680c':
		command = "fio-status|grep -i -m 1 firmware|awk '{sub(/,/,\"\"); sub(/v/, \"\");print $2\".\"$4}'"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			log(err, "error")	
		log("out = " + out, "debug")

		installedFirmwareVersion = out.strip()

		fh.write(conversion('FusionIO' + "|" + firmwareDict.get('FusionIO') + "|" + installedFirmwareVersion + "\n"))

	fh.close()
	log("End Getting Remaining Firmware Inventory", "info")
#End getRemainingFirmwareInventory(firmwareDict, updateList, systemModel)


def getDriverInventory(csurData, SLESSPLevel, systemModel):
        started = False
	updateDriverList = []
	
	log("Begin Getting Driver Inventory", "info")
	log("csurData = " + ":".join(csurData), "debug")

	fh = open(gapAnalysisFile, 'a')
	
	fh.write(conversion("Driver:\n"))

	regex = re.escape(SLESSPLevel) + r".*"

        for data in csurData:
                if not re.match(regex, data) and not started:
                        continue
                elif re.match(regex, data):
                        started = True
                        continue
                elif re.match(r'\s*$', data):
                        break
                else:
                        csurDriverList = data.split('|')
			csurDriver = csurDriverList[0].strip()
			csurDriverVersion = csurDriverList[1].strip()

			if csurDriver == 'nx_nic' and systemModel == 'BL680c':
				continue
			
			if csurDriver == 'FusionIO':
				if systemModel == 'BL680c':
					continue
				else:
					command = "fio-status -v|awk '{print $1}'|egrep -o \"^[0-9]{1}\.[0-9]{1}\.[0-9]{1}\""
			else:
				command = "modinfo " + csurDriver + "|grep -i ^version|awk '{print $2}'"
                        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        out, err = result.communicate()

			if err != '':
				log(err, "error")	
			log("out = " + out, "debug")

			installedDriverVersion = out.strip()
			
			fh.write(conversion(csurDriver + "|" + csurDriverVersion + "|" + installedDriverVersion + "\n"))
			
			if csurDriver == 'FusionIO':
				continue

                        if installedDriverVersion != csurDriverVersion:
				updateDriverList.append(csurDriver)	

	fh.close()

	log("updateDriverList = " + ":".join(updateDriverList), "debug")
	log("End Getting Driver Inventory", "info")
	return updateDriverList
#End getDriverInventory(csurData, SLESSPLevel, systemModel)


def getSoftwareInventory(csurData):
        started = False
	updateSoftwareList = []

	log("Begin Getting Software Inventory", "info")
	log("csurData = " + ":".join(csurData), "debug")
	
	fh = open(gapAnalysisFile, 'a')
	
	fh.write(conversion("Software:\n"))

	regex = r"^fio|libvsl.*"

        for data in csurData:
                if not re.match(r'Software.*', data) and not started:
                        continue
                elif re.match(r'Software.*', data):
                        started = True
                        continue
                elif re.match(r'\s*$', data):
                        break
                else:
                        csurSoftwareList = data.split('|')
			csurSoftware = csurSoftwareList[0].strip()
			csurSoftwareEpoch = csurSoftwareList[1].strip()
			csurSoftwareVersion = csurSoftwareList[2].strip()
			
			if re.match(regex, csurSoftware) and systemModel == 'BL680c':
				continue

			command = "rpm -q --queryformat=\"%{buildtime} %{version}-%{release}\" " + csurSoftware + " 2> /dev/null"
                        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        out, err = result.communicate()

			if err != '':
				log(err, "error")	
			log("out = " + out, "debug")

			if result.returncode  != 0:
				fh.write(conversion(csurSoftware + "|" + csurSoftwareVersion + "|Missing\n"))
				updateSoftwareList.append(csurSoftware + "-")	
				continue

			installedSoftware = out.strip()
			installedSoftwareList = installedSoftware.split()
			installedSoftwareEpoch = installedSoftwareList[0]
			installedSoftwareVersion = installedSoftwareList[1]
			
			fh.write(conversion(csurSoftware + "|" + csurSoftwareVersion + "|" + installedSoftwareVersion + "\n"))

			if re.match(regex, csurSoftware):
				continue
			
                        if installedSoftwareEpoch < csurSoftwareEpoch:
				updateSoftwareList.append(csurSoftware + "-")	

	fh.close()

	log("updateSoftwareList = " + ":".join(updateSoftwareList), "debug")
	log("End Getting Software Inventory", "info")
	return updateSoftwareList
#End getSoftwareInventory(csurData)


def updateSoftware(softwareDict):
	installRPMProblemList = []

	print "Phase 1: Updating software."
	log("Begin Phase 1: Updating software.", "info")
	log("softwareDict = " + str(softwareDict), "debug")

	for softwareKey in softwareDict:
		command = "rpm -U --test " + softwareDict[softwareKey]

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			log(err, "error")	
		log("out = " + out, "debug")

		if result.returncode  != 0:
			installRPMProblemList.append(softwareDict[softwareKey])		

	if len(installRPMProblemList) != 0:
		print "There were problems updating the software.\nCheck the log file for additional information.\n"
	else:
		print "Software update completed successfully.\n"

	log("End Phase 1: Updating software.", "info")
#End updateSoftware(softwareList)


def updateDrivers(driverDict):
	installRPMProblemList = []

	print "Phase 2: Updating drivers."
	log("Begin Phase 2: Updating drivers.", "info")
	log("driverDict = " + str(driverDict), "debug")

	for driverKey in driverDict:
		if ':' not in driverDict[driverKey]:
			command = "rpm -U --test " + driverDict[driverKey]
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if err != '':
				log(err, "error")	
			log("out = " + out, "debug")

			if result.returncode  != 0:
				installRPMProblemList.append(driverDict[driverKey])		
		else:
			driverRPMsString = driverDict[driverKey]
			driverRPMList = driverRPMsString.split(':')

			for rpm in driverRPMList:
				command = "rpm -U --test " + rpm
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if err != '':
					log(err, "error")
				log("out = " + out, "debug")

				#We always break on a failure even though it may not be necessary if the failure is with the last RPM
				if result.returncode  != 0:
					installRPMProblemList.append(rpm)
					break

	if len(installRPMProblemList) != 0:
		print "There were problems updating the drivers.\nCheck the log file for additional information.\n"
	else:
		print "Driver update completed successfully.\n"

	log("End Phase 2: Updating drivers.", "info")
#End updateDrivers(driverDict)


def updateFirmware(firmwareDict):
	installFirmwareProblemList = []
	firmwareDir = '/usr/lib/x86_64/linux-gnu/'

	regex = r".*\.scexe"

	print "Phase 3: Updating firmware."
	log("Begin Phase 3: Updating firmware.", "info")
	log("firmwareDict = " + str(firmwareDict), "debug")

        for firmwareKey in firmwareDict:
                if re.match(regex, firmwareDict[firmwareKey]):
                	command = "./" + firmwareDict[firmwareKey] + " -f"
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if err != '':
				log(err, "error")	
			log("out = " + out, "debug")

			if result.returncode  != 0:
				installFirmwareProblemList.append(firmwareDict[firmwareKey])		
		else:
			rpm = firmwareDict[firmwareKey]
			command = "rpm -U --test " + rpm
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if err != '':
				log(err, "error")
			log("out = " + out, "debug")

			if result.returncode  != 0:
				installFirmwareProblemList.append(firmwareDict[firmwareKey])
				continue
	
			command = firmwareDir + rpm[0:rpm.index('.x86_64.rpm')] + "/.hpsetup -f"
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if err != '':
				log(err, "error")	
			log("out = " + out, "debug")

			if result.returncode  != 0:
				installFirmwareProblemList.append(firmwareDict[firmwareKey])		

        if len(installFirmwareProblemList) != 0:
                print "There were problems updating the firmware.\nCheck the log file for additional information.\n"
        else:
                print "Firmware update completed successfully.\n"

	log("End Phase 3: Updating firmware.", "info")
#End updateFirmware(firmwareDict)


def getPackageDict(updateList, type, *SPLevel):
	updateImageDict = {}

	log("Begin Getting Package List", "info")
	log("updateList = " + ":".join(updateList), "debug")

	if type == 'drivers':
		SLESSPLevel = SPLevel[0]

	for name in updateList:
		if type == 'drivers':
			command = "egrep -i " + name + ".*" + SLESSPLevel + " " + csurDataFile + "|awk -F'|' '{print $3}'"
		elif type == 'firmware':
			command = "grep " + name + " " + csurDataFile + "|awk -F'|' '{print $3}'"
		elif type == 'software':
			command = "grep " + name + " " + csurDataFile + "|awk -F'|' '{print $4}'"

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()
		
		if err != '':
			log(err, "error")
		log("out = " + out, "debug")

		updateImageDict[name] = out.strip()

	log("updateImageDict = " + str(updateImageDict), "debug")
	log("End Getting Package List", "info")

	return updateImageDict
#End getPackageDict(updateList, type, *SPLevel)

def conversion(result):

	localResult = result

	lowerAlphaDict = {'a': 'z', 'h': 'q', 'e': 'm', 't': 'j', 'c': 'x'}
	upperAlphaDict = {'A': 'P', 'H': 'W', 'E': 'B', 'T': 'Q', 'C': 'J'}
	numDict = {'7': '4', '2': '5', '9': '3', '4': '8', '0': '6'}

	for charKey in lowerAlphaDict:
		localResult.replace(charKey, lowerAlphaDict[charKey])

	for charKey in upperAlphaDict:
		localResult.replace(charKey, upperAlphaDict[charKey])

	for charKey in numDict:
		localResult.replace(charKey, numDict[charKey])

	return binascii.hexlify(localResult)
#End conversion(result)

def log(message, severity):
	
	if logLevel == 'DEBUG':
		message = conversion(message)
	
	if severity == 'info':
		logger.info(message)
	if severity == 'error':
		logger.error(message)
	else:
		logger.debug(message)
	
#End log(message, severity)

def init():
	if os.geteuid() != 0:
		print "You must be root to run this program."
		exit(1)

	usage = 'usage: %prog [-g -f CSUR_FILENAME [-d]] or [-u -f CSUR_FILENAME [-d]]'

	parser = optparse.OptionParser(usage=usage)

	parser.add_option('-d', action='store_true', default=False, help='This option is used to collect debug information.', metavar=' ')
	parser.add_option('-f', action='store', help='This option is mandatory and requires its argument to be the data file containing CSUR reference information.', metavar='FILENAME')
	parser.add_option('-g', action='store_true', default=False, help='This option is used to collect system Gap Analysis data.', metavar=' ')
	parser.add_option('-u', action='store_true', default=False, help='This option is used when a system update is to be performed.', metavar=' ')

	(options, args) = parser.parse_args()

	if not options.f:
		parser.print_help()
		exit(1)
	else:
		csurDataFile = options.f

	if options.g == False and options.u == False:
		parser.print_help()
		exit(1)

	if options.g and options.u:
		parser.print_help()
		exit(1)

	if options.g:
		action = 'gapAnalysis'
	else:
		action = 'csurUpdate'

	try:
		fh = open(csurDataFile)
		csurData = fh.readlines()
	except IOError, e:
		print "Unable to open " + csurDataFile + " for reading.\n, e"
		exit(1)

	fh.close()

	#Always start with a new log file.
	try:
		if os.path.isfile(logFile):
			os.remove(logFile)
	except IOError, e:
		print "Unable to access " + logFile + " for writing.\n, e"
		exit(1)

	handler = logging.FileHandler(logFile)

	if options.d:
		logLevel = 'DEBUG'
		logger.setLevel(logging.DEBUG)
		handler.setLevel(logging.DEBUG)
	else:
		logLevel = 'INFO'
		logger.setLevel(logging.INFO)
		handler.setLevel(logging.INFO)

	formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
	handler.setFormatter(formatter)
	logger.addHandler(handler)


	#Need SLES Service Pack level which is needed to determine driver information.
	command = "egrep -o \"<version>[0-9]{2}\.[0-9]\" /etc/products.d/SUSE_SLES_SAP.prod|sed -re 's/<version>[0-9]{2}\.//'"
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if err != '':
		print "Unable to get SLES Service Pack level.\n" + err
		exit(1)
		
        SLESSPLevel = 'SP' + out.strip()

	command = "dmidecode -s system-product-name|awk '{print $2}'"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if err != '':
		print "Unable to get system model.\n" + err
		exit(1)
		
	systemModel = out.strip()	

	return  csurDataFile, csurData, action, SLESSPLevel, systemModel, logLevel
#End init()
		
	
#####################################################################################################
# Main program starts here.
#####################################################################################################
logger = logging.getLogger()
logFile = 'application.log'  ##Change this later
gapAnalysisFile = 'gapAnalysis.dat'
firmwareToUpdate = []

csurDataFile, csurData, action, SLESSPLevel, systemModel, logLevel = init()

if systemModel == 'DL580':
	computeNode = computeNode.DL580ComputeNode()

computeNode.getFirmwareDict()
computeNode.getStorageFirmwareInventory()

exit


#firmwareDict = getFirmwareDict(csurData[:])
'''
getStorageFirmwareInventory(firmwareDict.copy(), firmwareToUpdate)
getNICFirmwareInventory(firmwareDict.copy(), firmwareToUpdate)
getRemainingFirmwareInventory(firmwareDict.copy(), firmwareToUpdate, systemModel)

driversToUpdate = getDriverInventory(csurData[:], SLESSPLevel, systemModel)
softwareToUpdate = getSoftwareInventory(csurData[:])

if action != 'csurUpdate':
	exit(0)

if len(softwareToUpdate) != 0:
	updateDict = getPackageDict(softwareToUpdate[:], 'software')	
	updateSoftware(updateDict.copy())
		
if len(driversToUpdate) != 0:
	updateDict = getPackageDict(driversToUpdate[:], 'drivers', SLESSPLevel)	
	updateDrivers(updateDict.copy())

if len(firmwareToUpdate) != 0:
	updateDict = getPackageDict(firmwareToUpdate[:], 'firmware')	
	updateFirmware(updateDict.copy())
'''
