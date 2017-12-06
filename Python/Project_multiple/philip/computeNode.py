import re
import socket
import os
import subprocess
import datetime
import csurUtils


#This is the main compute node class from which other compute nodes can be instantiated as necessary.
class ComputeNode():

	def __init__(self, systemModel, OSDistLevel, gapAnalysisFile):
		self.systemModel = systemModel
		self.OSDistLevel = OSDistLevel
		self.gapAnalysisFile = gapAnalysisFile

		if os.path.isfile(self.gapAnalysisFile):
			try:
				os.remove(self.gapAnalysisFile)
			except IOError, e:
                		print csurUtils.RED + "Unable to delete " + self.gapAnalysisFile + " .\n, e" + csurUtils.RESETCOLORS
                		exit(1)

		#Variables used to determine status of gap analysis stage data collection.
		self.firmwareError = False
		self.driverError = False
		self.softwareError = False
	#End __init__(self, systemModel, OSDistLevel)


	def getFirmwareDict(self, csurData):
		started = False
		firmwareDict = {}

		csurUtils.log("Begin Getting Firmware Dictionary", "info")

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

		csurUtils.log("firmwareDict = " + str(firmwareDict), "debug")
		csurUtils.log("End Getting Firmware Dictionary", "info")
		return firmwareDict
	#End getFirmwareDict(csurData)


	def getStorageFirmwareInventory(self, firmwareDict, updateList):
		fh = open(self.gapAnalysisFile, 'a')

		csurUtils.log("Begin Getting Storage Firmware Inventory", "info")
		csurUtils.log("firmwareDict = " + str(firmwareDict), "debug")
		csurUtils.log("updateList = " + ":".join(updateList), "debug")

		#hpacucli has been replaced by hpssacli so we need to check in case we are on an older system.
		if os.path.isfile('/usr/sbin/hpssacli'):
			arrayCfgUtilFile = '/usr/sbin/hpssacli'
		else:
			arrayCfgUtilFile = '/usr/sbin/hpacucli'

		csurUtils.log("arrayCfgUtilFile = " + arrayCfgUtilFile, "debug")

		#Get list of storage controllers.
		command = arrayCfgUtilFile + " ctrl all show status|egrep -o \"P.*Slot\s*[0-9]{1,2}\"|awk '{print $1\":\"$NF}'"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			csurUtils.log(err, "error")
			self.firmwareError = True
		csurUtils.log("out = " + out, "debug")

		controllerList = out.splitlines()

		hardDriveList = [] #This is a complete list of hard drives from all controllers combined.

		for controller in controllerList:
			controllerModel = controller[0:controller.index(':')]
			controllerSlot = controller[controller.index(':')+1:len(controller)]

			csurFirmwareVersion = firmwareDict.get(controllerModel)

			command = arrayCfgUtilFile + " ctrl slot=" + controllerSlot + " show |grep \"Firmware Version\"|awk '{print $3}'"

			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if err != '':
				csurUtils.log(err, "error")
				self.firmwareError = True
			csurUtils.log("out = " + out, "debug")

			installedFirmwareVersion = out.strip()

			if installedFirmwareVersion != csurFirmwareVersion:
				updateList.append(controllerModel)

			fh.write(csurUtils.conversion("| " + controllerModel.ljust(25) + "| " + csurFirmwareVersion.ljust(25) + "| " + installedFirmwareVersion.ljust(23) + "|" + "\n"))

			if (controllerModel == 'P812') or (controllerModel == 'P431'):
				csurFirmwareVersion = firmwareDict.get('D2700')
				command = arrayCfgUtilFile + " ctrl slot=" + controllerSlot + " enclosure all show  detail|grep -m 1  \"Firmware Version\"|awk '{print $3}'"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if err != '':
					csurUtils.log(err, "error")
					self.firmwareError = True
				csurUtils.log("out = " + out, "debug")

				installedFirmwareVersion = out.strip()

				if installedFirmwareVersion != csurFirmwareVersion:
					updateList.append('D2700')

				fh.write(csurUtils.conversion("| " + "D2700".ljust(25) + "| " + csurFirmwareVersion.ljust(25) + "| " + installedFirmwareVersion.ljust(23) + "|" + "\n"))

			#Get a list of all hard drives and thier firmware version.
			command = arrayCfgUtilFile + " ctrl slot=" + controllerSlot + " pd all show detail|grep -A 2 --no-group-separator \"Firmware Revision\"|grep -v Serial|sed -e '$!N;s/\\n/ /'|awk '{print $6, $3}'|sort -k1"

			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if err != '':
				csurUtils.log(err, "error")
				self.firmwareError = True
			csurUtils.log("out = " + out, "debug")

			hardDriveList.extend(out.splitlines()) #out is an array of hard drives and their firmware version, e.g. 'EG0600FBVFP HPDC'

		#Sort the hard drive list since it may not be sorted due to multiple controllers.
		hardDriveList.sort()

		#Get a unique list of hard drives managed by the controllers.
		hardDriveModels = []
		count = 0
		
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

			#This accounts for the cases where the CSUR did not include a hard drive's firmware.
			if csurFirmwareVersion is None:
				csurFirmwareVersion = 'Missing'
				fh.write(csurUtils.conversion("| " + hardDriveModel.ljust(25) + "| " + csurFirmwareVersion.ljust(25) + "| ".ljust(25, ' ') + "|" + "\n"))
				continue

			#Now check every hard drive's firmware version that matches the current hardDriveModel.
			for hd in hardDriveList:
				hardDriveData = hd.split()

				if hardDriveData[0].strip() == hardDriveModel:
					hardDriveFirmwareVersion = hardDriveData[1].strip()

					'''
					If the hard drive version does not match the CSUR version then add it to the updateList.
					We only care about a one time occurance of a firmware mis-match.
					'''
					if hardDriveFirmwareVersion != csurFirmwareVersion:
						updateList.append(hardDriveModel)
						fh.write(csurUtils.conversion("| " + hardDriveModel.ljust(25) + "| " + csurFirmwareVersion.ljust(25) + "| " + hardDriveFirmwareVersion.ljust(23) + "|" + "\n"))
						count += 1
						break

			#If all the hard drives for the given model have firmware matching the CSUR then count will be 0.
			if count == 0:
				fh.write(csurUtils.conversion("| " + hardDriveModel.ljust(25) + "| " + csurFirmwareVersion.ljust(25) + "| " + hardDriveFirmwareVersion.ljust(23) + "|" + "\n"))
		fh.close()
		csurUtils.log("End Getting Storage Firmware Inventory", "info")
	#End getStorageFirmwareInventory(firmwareDict, updateList)


	def getNICFirmwareInventory(self, firmwareDict, updateList):
		nicCardModels = []
		count = 0

		csurUtils.log("Begin Getting NIC Firmware Inventory", "info")
		csurUtils.log("firmwareDict = " + str(firmwareDict), "debug")
		csurUtils.log("updateList = " + ":".join(updateList), "debug")

		nicBusList = self.getNicBusList()

		#Get a unique list of nic card models.
		for nd in nicBusList: #['03:00.0 HP331FLR', '44:00.0 HP560SFP', '47:00.0 HP560SFP']
			nicCardData = nd.split()

			if count == 0:
				nicCardModels.append(nicCardData[1].strip())
				tmpNicCardModel = nicCardData[1]
				count += 1
			elif nicCardData[1] != tmpNicCardModel:
				nicCardModels.append(nicCardData[1].strip())
				tmpNicCardModel = nicCardData[1]

		#Get nic card list which will be used to map nic card bus to nic device.
		command = "ifconfig -a|egrep -v \"^\s+|^bond|^lo|^\s*$\"|awk '{print $1}'"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			csurUtils.log(err, "error")
			self.firmwareError = True
		csurUtils.log("out = " + out, "debug")

		nicCardList = out.splitlines() #['em0', 'em1', 'em2', 'em3', 'p4p1', 'p4p2', 'p5p1', 'p5p2', 'p7p1', 'p7p2', 'p8p1', 'p8p2']

		fh = open(self.gapAnalysisFile, 'a')

		#Loop through all nic cards to check thier firmware.  Only record one occcurance of a mismatch.
		for nicCardModel in nicCardModels: #['HP331FLR', 'HP560SFP']
			count = 0
			csurNicCardFirmwareVersion = firmwareDict.get(nicCardModel)

			for data in nicBusList:
				nicCardData = data.split()

				nicBus = nicCardData[0].strip()
				installedNicCardModel = nicCardData[1].strip()

				if installedNicCardModel == nicCardModel:
					for nic in nicCardList:
						command = "ethtool -i " + nic + "|grep " + nicBus
						result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
						out, err = result.communicate()

						if err != '':
							csurUtils.log(err, "error")
							self.firmwareError = True
						csurUtils.log("out = " + out, "debug")

						if result.returncode != 0:
							continue
						else:
							nicDevice = nic

						command = "ethtool -i " + nicDevice + "|grep firmware-version|awk '{print $NF}'"
						result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
						out, err = result.communicate()

						if err != '':
							csurUtils.log(err, "error")
							self.firmwareError = True
						csurUtils.log("out = " + out, "debug")

						installedFirmwareVersion = out.strip()

						if installedFirmwareVersion != csurNicCardFirmwareVersion and count == 0:
							updateList.append(nicCardModel)
							fh.write(csurUtils.conversion("| " + nicCardModel.ljust(25) + "| " + csurNicCardFirmwareVersion.ljust(25) + "| " + installedFirmwareVersion.ljust(23) + "|" + "\n"))
							count += 1
						break #We only get here if a nic card matched the nicBus we are looking at.
				else:
					continue
	
				if count == 1:
					break
			if count == 0:
				fh.write(csurUtils.conversion("| " + nicCardModel.ljust(25) + "| " + csurNicCardFirmwareVersion.ljust(25) + "| " + installedFirmwareVersion.ljust(23) + "|" + "\n"))
		fh.close()
		csurUtils.log("End Getting NIC Firmware Inventory", "info")
	#End getNICFirmwareInventory(firmwareDict, updateList)


	def getNicBusList(self):
		nicBusList = []
		commands = []
		count = 0

		if self.systemModel == 'DL580G7' or self.systemModel =='DL980G7' or self.systemModel =='BL680cG7':
			commands.append("lspci -v|grep -B1 NC --no-group-separator|sed -e '$!N;s/\\n/ /'|uniq -w 2|egrep -io \".{2}:.{2}\.[0-9]{1}|NC[0-9]+[a-z]{1,3}\"|sed -e '$!N;s/\\n/ /'| sort -k2")
		elif self.systemModel == 'DL580Gen8':
			commands.append("lspci -v|grep 'NetXtreme BCM5719'|uniq -w 2|egrep -io \".{2}:.{2}\.[0-9]{1}\"") #HP 331FLR
			commands.append("HP331FLR")
			commands.append("lspci -v|grep 'Intel Corporation 82599'|uniq -w 2|egrep -io \".{2}:.{2}\.[0-9]{1}\"") #HP 560SFP+
			commands.append("HP560SFP")
		elif self.systemModel == 'DL380pGen8':
			commands.append("lspci -v|grep -B1 NC --no-group-separator|sed -e '$!N;s/\\n/ /'|uniq -w 2|egrep -io \".{2}:.{2}\.[0-9]{1}|NC[0-9]+[a-z]{1,3}\"|sed -e '$!N;s/\\n/ /'| sort -k2") #NC552SFP
			commands.append("lspci -v|grep 'NetXtreme BCM5719'|uniq -w 2|egrep -io \".{2}:.{2}\.[0-9]{1}\"") #HP 331FLR
			commands.append("HP331FLR")

		while count < len(commands):
			command = commands[count]
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if err != '':
				csurUtils.log(err, "error")
				self.firmwareError = True
			csurUtils.log("out = " + out, "debug")

			if len(commands) == 1:
				nicBusList = out.splitlines()
			else:
				tmpList = out.splitlines()
				nicBusList.extend(x + ' ' + commands[count + 1] for x in tmpList)

			count += 2

		return nicBusList
	#End getNicBusList():


	def getCommonFirmwareInventory(self, firmwareDict, updateList):
		biosFirmwareType = "BIOS" + self.systemModel
			
		fh = open(self.gapAnalysisFile, 'a')

		csurUtils.log("Begin Getting Compute Node Common Firmware Inventory", "info")
		csurUtils.log("firmwareDict = " + str(firmwareDict), "debug")
		csurUtils.log("updateList = " + ":".join(updateList), "debug")

		#BIOS
		command = "dmidecode -s bios-release-date"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			csurUtils.log(err, "error")
			self.firmwareError = True
		csurUtils.log("out = " + out, "debug")

		biosFirmwareDate = out.strip()
		biosFirmwareDateList = biosFirmwareDate.split('/')
		installedFirmwareVersion = biosFirmwareDateList[2] + '.' + biosFirmwareDateList[0] + '.' + biosFirmwareDateList[1]

		csurFirmwareVersion = firmwareDict.get(biosFirmwareType)

		if installedFirmwareVersion != csurFirmwareVersion:
			updateList.append(biosFirmwareType)

		fh.write(csurUtils.conversion("| " + biosFirmwareType.ljust(25) + "| " + csurFirmwareVersion.ljust(25) + "| " + installedFirmwareVersion.ljust(23) + "|" + "\n"))

		#iLO
		command = "hponcfg -g|grep \"Firmware Revision\"|awk '{print $4}'"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			csurUtils.log(err, "error")
			self.firmwareError = True
		csurUtils.log("out = " + out, "debug")

		installedFirmwareVersion = out.strip()

		if installedFirmwareVersion != firmwareDict.get('iLO'):
			updateList.append('iLO')

		fh.write(csurUtils.conversion("| " + 'iLO'.ljust(25) + "| " + firmwareDict.get('iLO').ljust(25) + "| " + installedFirmwareVersion.ljust(23) + "|" + "\n"))
		fh.close()
		csurUtils.log("End Getting Compute Node Common Firmware Inventory", "info")
	#End getCommonFirmwareInventory(firmwareDict, updateList)

	def getComputeNodeSpecificFirmwareInventory(self, firmwareDict, updateList):
		pass
	#End getComputeNodeSpecificFirmwareInventory(self, firmwareDict, updateList)

	def getDriverInventory(self, csurData):
		started = False
		updateDriverList = []

		csurUtils.log("Begin Getting Driver Inventory", "info")
		csurUtils.log("csurData = " + ":".join(csurData), "debug")

		fh = open(self.gapAnalysisFile, 'a')

		regex = self.OSDistLevel + ".*" + self.systemModel + ".*"
	
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

				command = "modinfo " + csurDriver + "|grep -i ^version|awk '{print $2}'"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if err != '':
					csurUtils.log(err, "error")
					self.driverError = True
				csurUtils.log("out = " + out, "debug")

				installedDriverVersion = out.strip()

				fh.write(csurUtils.conversion("| " + csurDriver.ljust(25) + "| " + csurDriverVersion.ljust(25) + "| " + installedDriverVersion.ljust(23) + "|" + "\n"))

				if installedDriverVersion != csurDriverVersion:
					updateDriverList.append(csurDriver)
		fh.close()

		csurUtils.log("updateDriverList = " + ":".join(updateDriverList), "debug")
		csurUtils.log("End Getting Driver Inventory", "info")
		return updateDriverList
	#End getDriverInventory(csurData)


        def getSoftwareInventory(self, csurData):
                started = False
                softwareFound = False
                updateSoftwareList = []

                csurUtils.log("Begin Getting Software Inventory", "info")
                csurUtils.log("csurData = " + ":".join(csurData), "debug")

                fh = open(self.gapAnalysisFile, 'a')

		regex = ".*" + self.OSDistLevel + ".*" + self.systemModel + ".*"

                for data in csurData:
                        if not re.match('Software.*', data) and not softwareFound:
                                continue
                        elif re.match('Software.*', data):
                                softwareFound = True
                                continue
                        elif not re.match(regex, data) and not started:
                                continue
                        elif re.match(regex, data):
                                started = True
                                continue
                        elif re.match(r'\s*$', data):
                                break
                        else:
                                csurSoftwareList = data.split('|')
                                csurSoftware = csurSoftwareList[0].strip()
                                csurSoftwareEpoch = csurSoftwareList[1].strip()
                                csurSoftwareVersion = csurSoftwareList[2].strip()

                                command = "rpm -q --queryformat=\"%{buildtime} %{version}-%{release}\" " + csurSoftware + " 2> /dev/null"
                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()

                                if err != '':
                                        csurUtils.log(err, "error")
					self.softwareError = True
                                csurUtils.log("out = " + out, "debug")

                                if result.returncode != 0:
					fh.write(csurUtils.conversion("| " + csurSoftware.ljust(25) + "| " + csurSoftwareVersion.ljust(25) + "| Missing".ljust(25, ' ') + "|" + "\n"))
                                        updateSoftwareList.append(csurSoftware)
                                        continue

                                installedSoftware = out.strip()
                                installedSoftwareList = installedSoftware.split()
                                installedSoftwareEpoch = installedSoftwareList[0]
                                installedSoftwareVersion = installedSoftwareList[1]

				fh.write(csurUtils.conversion("| " + csurSoftware.ljust(25) + "| " + csurSoftwareVersion.ljust(25) + "| " + installedSoftwareVersion.ljust(23) + "|" + "\n"))
                                if re.match(regex, csurSoftware):
                                        continue

                                if installedSoftwareEpoch < csurSoftwareEpoch:
                                        updateSoftwareList.append(csurSoftware)
                fh.close()

                csurUtils.log("updateSoftwareList = " + ":".join(updateSoftwareList), "debug")
                csurUtils.log("End Getting Software Inventory", "info")
                return updateSoftwareList
        #End getSoftwareInventory(csurData)


	def getFirmwareStatus(self):
		return self.firmwareError
	#End getFirmwareStatus():


	def getDriverStatus(self):
		return self.driverError
	#End getDriverStatus():


	def getSoftwareStatus(self):
		return self.softwareError
	#End getSoftwareStatus():
#End ComputeNode()


class Gen1ScaleUpComputeNode(ComputeNode):

	def getComputeNodeSpecificFirmwareInventory(self, firmwareDict, updateList):
		fh = open(self.gapAnalysisFile, 'a')

		csurUtils.log("Begin Getting Compute Node Specific Firmware Inventory", "info")
		csurUtils.log("firmwareDict = " + str(firmwareDict), "debug")
		csurUtils.log("updateList = " + ":".join(updateList), "debug")

		#Fusion-IO
		command = "fio-status|grep -i -m 1 firmware|awk '{sub(/,/,\"\"); sub(/v/, \"\");print $2\".\"$4}'"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			csurUtils.log(err, "error")
			self.firmwareError = True
		csurUtils.log("out = " + out, "debug")

		installedFirmwareVersion = out.strip()

		fh.write(csurUtils.conversion("| " + 'FusionIO'.ljust(25) + "| " + firmwareDict.get('FusionIO').ljust(25) + "| " + installedFirmwareVersion.ljust(23) + "|" + "\n"))

		fh.close()
		csurUtils.log("End Getting Compute Node Specific Firmware Inventory", "info")
	#End getComputeNodeSpecificFirmwareInventory(firmwareDict, updateList)


	def getFusionIODriverInventory(self, csurData):
		started = False
		updateDriverList = []

		csurUtils.log("Begin Getting FusionIO Driver Inventory", "info")
		csurUtils.log("csurData = " + ":".join(csurData), "debug")

		fh = open(self.gapAnalysisFile, 'a')

		regex = r"^FusionIODriver.*"

		for data in csurData:
			if not re.match(regex, data) and not started:
				continue
			elif re.match(regex, data):
				started = True
				continue
			else:
				csurDriverList = data.split('|')
				csurDriver = csurDriverList[0].strip()
				csurDriverVersion = csurDriverList[1].strip()

				command = "fio-status -v|awk '{print $1}'|egrep -o \"^[0-9]{1}\.[0-9]{1}\.[0-9]{1}\""
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if err != '':
					csurUtils.log(err, "error")
					self.driverError = True
				csurUtils.log("out = " + out, "debug")

				installedDriverVersion = out.strip()

				fh.write(csurUtils.conversion("| " + csurDriver.ljust(25) + "| " + csurDriverVersion.ljust(25) + "| " + installedDriverVersion.ljust(23) + "|" + "\n"))
	
				break
		fh.close()
		csurUtils.log("End Getting FusionIO Driver Inventory", "info")
	#End getFusionIODriverInventory(csurData)


	def getFusionIOSoftwareInventory(self, csurData):
		started = False
		updateSoftwareList = []
		regex = r"^FusionIOSoftware.*"

		csurUtils.log("Begin Getting FusionIO Software Inventory", "info")
		csurUtils.log("csurData = " + ":".join(csurData), "debug")

		fh = open(self.gapAnalysisFile, 'a')

		for data in csurData:
			if not re.match(regex, data) and not started:
				continue
			elif re.match(regex, data):
				started = True
				continue
			else:
				csurSoftwareList = data.split('|')
				csurSoftware = csurSoftwareList[0].strip()
				csurSoftwareEpoch = csurSoftwareList[1].strip()
				csurSoftwareVersion = csurSoftwareList[2].strip()

				command = "rpm -q --queryformat=\"%{buildtime} %{version}-%{release}\" " + csurSoftware + " 2> /dev/null"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if err != '':
					csurUtils.log(err, "error")
					self.softwareError = True
				csurUtils.log("out = " + out, "debug")

				if result.returncode != 0:
					fh.write(csurUtils.conversion("| " + csurSoftware.ljust(25) + "| " + csurSoftwareVersion.ljust(25) + "| Missing".ljust(25, ' ') + "|" + "\n"))
					updateSoftwareList.append(csurSoftware + "-")
					continue

				installedSoftware = out.strip()
				installedSoftwareList = installedSoftware.split()
				installedSoftwareEpoch = installedSoftwareList[0]
				installedSoftwareVersion = installedSoftwareList[1]

				fh.write(csurUtils.conversion("| " + csurSoftware.ljust(25) + "| " + csurSoftwareVersion.ljust(25) + "| " + installedSoftwareVersion.ljust(23) + "|" + "\n"))
		fh.close()

		csurUtils.log("End Getting Software Inventory", "info")
	#End getFusionIOSoftwareInventory(csurData)
#End Gen1ScaleUpComputeNode(ComputeNode)


class DL580Gen8ComputeNode(ComputeNode):

	def getComputeNodeSpecificFirmwareInventory(self, firmwareDict, updateList):
		fh = open(self.gapAnalysisFile, 'a')

		csurUtils.log("Begin Getting Compute Node Specific Firmware Inventory", "info")
		csurUtils.log("firmwareDict = " + str(firmwareDict), "debug")
		csurUtils.log("updateList = " + ":".join(updateList), "debug")

		#Power Management Controller
		fh2 = open("dmidecode.log", 'w')
		subprocess.call(["dmidecode"], stdout=fh2)
		fh2.close()

		command = "egrep -A 1 \"^\s*Power Management Controller Firmware\s*$\" dmidecode.log |grep -v Power |sed -e 's/^[ \t]*//'"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			csurUtils.log(err, "error")
			self.firmwareError = True
		csurUtils.log("out = " + out, "debug")

		installedFirmwareVersion = out.strip()

		fh.write(csurUtils.conversion("| " + 'PMCDL580Gen8'.ljust(25) + "| " + (firmwareDict.get('PMCDL580Gen8')).ljust(25) + "| " + installedFirmwareVersion.ljust(23) + "|" + "\n"))

		fh.close()

		os.remove("dmidecode.log")
		csurUtils.log("End Getting Compute Node Specific Firmware Inventory", "info")
	#End getComputeNodeSpecificFirmwareInventory(firmwareDict, updateList)
#End DL580Gen8ComputeNode(ComputeNode)
