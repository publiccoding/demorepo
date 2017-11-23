import re
import os
import subprocess
import logging


#This is the main compute node inventory class from which other compute node inventory classes can be instantiated as necessary.
class ComputeNodeInventory:

	def __init__(self, computeNodeDict, noPMCFirmwareUpdateModels, computeNodeResources, **kwargs):
		self.systemModel = computeNodeDict['systemModel']
		self.osDistLevel = computeNodeDict['osDistLevel']
		self.noPMCFirmwareUpdateModels = noPMCFirmwareUpdateModels
		self.computeNodeResources = computeNodeResources

		'''
		Gen 1.x compute nodes use the same iLO firmware except the NFS nodes which use iLO 4 firmware, since 
		the DL380p is a Gen8 system whereas the other compute nodes are G7.  Therefore, thier resource value
		has to be set appropriately.
		'''
		if 'systemGeneration' in kwargs and self.systemModel == 'DL380pGen8' and kwargs['systemGeneration'] == 'Gen1.x':
			self.iLOFirmwareType = 'iLODL380pGen8'
		else:
			self.iLOFirmwareType = 'iLO'

		#This is used to identify if a system had external storage attached.
		self.externalStoragePresent = False

		loggerName = computeNodeDict['loggerName']

		hostname = computeNodeDict['hostname']

		#This gets the main compute node's log file logger.
		self.logger = logging.getLogger(loggerName)

		#This gets the version information log file logger.
		self.versionInformationLogger = logging.getLogger('versionInformationLog')

		self.versionInformationLogger.info('{0:40}'.format('Version information for Compute Node ' + hostname + ':') + '\n')

		#Variable used to determine status of getting update inventory.
		self.inventoryError = False

		#This dictionary contains the CSUR firmware inventory.
		self.firmwareDict = {}

		#The following dictionary contains the components that need to be updated.
		self.componentUpdateDict = {'Firmware' : {}, 'Drivers' : {}, 'Software' : {}}

		#Status messages for csur and installed version match.  FAIL means that the versions do not match and PASS means that versions match.
		self.notVersionMatchMessage = 'FAIL'
		self.versionMatchMessage = 'PASS'

		#This message is used when a software component is not installed.
		self.versionMatchWarningMessage = 'WARNING'

	#End __init__(self, computeNodeDict, noPMCFirmwareUpdateModels, computeNodeResources):


	'''
	This function retrieves the list of firmware from the computeNodeResources resource list and 
	returns the component identifier and its associated firmware version and update image.
	It is expected that the firmware section begins with the word Firmware and that 
	there are no blank lines until the next section in the resource file is encounterd.
	'''
	def __getFirmwareDict(self):
		started = False

		self.logger.info("Getting the firmware dictionary.")

		for data in self.computeNodeResources:
			#Remove spaces if any are present.
			data = data.replace(' ', '')

			if not re.match('Firmware.*', data) and not started:
				continue
			elif re.match('Firmware.*', data):
				started = True
				continue
			elif re.match(r'\s*$', data):
				break
			else:
				firmwareList = data.split('|')
				self.firmwareDict[firmwareList[0]] = [firmwareList[1], firmwareList[2]]

		self.logger.debug("The firmware dictionary contents was determined to be: " + str(self.firmwareDict) + ".")

		self.logger.info("Done getting the firmware dictionary.")

	#End __getFirmwareDict(self):


	'''
	This function calls the firmware, driver, and software inventory functions which update thier
	cooresponding dictionary with the components that need to be updated.
	'''
	def getComponentUpdateInventory(self):
		componentHeader = 'Component'
		componentUnderLine = '---------'

		csurVersionHeader = 'CSUR Version'
		csurVersionUnderLine = '------------'

		currentVersionHeader = 'Current Version'
		currentVersionUnderLine = '---------------'

		statusHeader = 'Status'
		statusUnderLine = '------'

		self.__getFirmwareDict()

		self.versionInformationLogger.info('{0:40}'.format('Firmware Versions:') + '\n')
		self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentHeader, csurVersionHeader, currentVersionHeader, statusHeader))
		self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentUnderLine, csurVersionUnderLine, currentVersionUnderLine, statusUnderLine))
		
		if self.__getLocalStorage() == 'Present':
			self.__getStorageFirmwareInventory()
			
		self.__getNICFirmwareInventory()
		self.__getCommonFirmwareInventory()
		self._getComputeNodeSpecificFirmwareInventory()

		self.versionInformationLogger.info('\n' + '{0:40}'.format('Driver Versions:') + '\n')
		self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentHeader, csurVersionHeader, currentVersionHeader, statusHeader))
		self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentUnderLine, csurVersionUnderLine, currentVersionUnderLine, statusUnderLine))

		self.__getDriverInventory()
		self._getComputeNodeSpecificDriverInventory()

		self.versionInformationLogger.info('\n' + '{0:40}'.format('Software Versions:') + '\n')
		self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentHeader, csurVersionHeader, currentVersionHeader, statusHeader))
		self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentUnderLine, csurVersionUnderLine, currentVersionUnderLine, statusUnderLine))

		self.__getSoftwareInventory()
		self._getComputeNodeSpecificSoftwareInventory()

	#End getComponentUpdateInventory(self):


	'''
	This function is used to get the local OS hard drive inventory.
	'''
	def getLocalHardDriveFirmwareInventory(self):
		hardDrivesLocal = None

		self.__getFirmwareDict()

		if self.__getLocalStorage() == 'Present':
			hardDrivesLocal = True
			self.__getLocalOSHardDriveFirmwareInventory()
		elif self.__getLocalStorage() == 'Absent':
			hardDrivesLocal = False
		
		return hardDrivesLocal

	#End getLocalHardDriveFirmwareInventory(self):


	#End getLocalStorageFirmwareInventory(self):

	'''
	This function gets the storage components (contoller, hard drive, enclosure) needing a firmware update.
	'''
	def __getStorageFirmwareInventory(self):
		self.logger.info("Getting the storage firmware inventory.")

		#hpacucli has been replaced by hpssacli so we need to check in case we are on an older system.
		if os.path.isfile('/usr/sbin/hpssacli'):
			arrayCfgUtilFile = '/usr/sbin/hpssacli'
		else:
			arrayCfgUtilFile = '/usr/sbin/hpacucli'

		#Get list of storage controllers.
		command = arrayCfgUtilFile + " ctrl all show"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to get the list of storage controllers was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Failed to get the list of storage controllers.\n" + err)
			self.inventoryError = True
			return

		controllerList = re.findall('P\d{3}i*\s+in\s+Slot\s+\d{1}', out, re.MULTILINE|re.DOTALL)

		self.logger.debug("The controller list was determined to be: " + str(controllerList) + ".")

		hardDriveList = [] #This is a complete list of hard drives from all controllers combined. An example element is 'EG0600FBVFP HPDC'.

		'''
		Get the firmware version informaiton for the storage components based on the controller list.
		An example controllerList is ['P431 in Slot 2', 'P830i in Slot 0'].
		'''
		for controller in controllerList:
			controllerModel = controller.split()[0]
			controllerSlot = controller.split()[-1]

			#Get the controller's firmware version that the csur contains.
			csurControllerFirmwareVersion = (self.firmwareDict[controllerModel])[0]

			command = arrayCfgUtilFile + " ctrl slot=" + controllerSlot + " show"

			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			self.logger.debug("The output of the command (" + command + ") used to get the storage controllers firmware version was: " + out.strip())

			if result.returncode != 0:
				self.logger.error("Failed to get the list of storage controllers.\n" + err)
				self.inventoryError = True
				return
			
			installedControllerFirmwareVersion = re.match('.*Firmware Version:\s+(\d+\.\d+).*', out, re.MULTILINE|re.DOTALL).group(1)

			self.logger.debug("The controller's firmware version was determined to be: " + installedControllerFirmwareVersion + ".")

			if installedControllerFirmwareVersion != csurControllerFirmwareVersion:
				self.componentUpdateDict['Firmware'][controllerModel] = (self.firmwareDict[controllerModel])[1]
				self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(controllerModel, csurControllerFirmwareVersion, installedControllerFirmwareVersion, self.notVersionMatchMessage))
			else:
				self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(controllerModel, csurControllerFirmwareVersion, installedControllerFirmwareVersion, self.versionMatchMessage))

			#Check enclosure firmware if attached. Currently our HANA compute nodes only use the P812 and P431 controllers for external storage.
			if (controllerModel == 'P812') or (controllerModel == 'P431'):
				if self.systemModel != 'DL580Gen9':
                                        csurEnclosureFirmwareVersion = (self.firmwareDict['D2700'])[0]
                                        enclosure = 'D2700'
                                else:
                                        csurEnclosureFirmwareVersion = (self.firmwareDict['D3700'])[0]
                                        enclosure = 'D3700'

				self.externalStoragePresent = True

				command = arrayCfgUtilFile + " ctrl slot=" + controllerSlot + " enclosure all show detail"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				self.logger.debug("The output of the command (" + command + ") used to get the storage controllers enclosure firmware version was: " + out.strip())

				if result.returncode != 0:
					self.logger.error("Failed to get the storage contoller's details.\n" + err)
					self.inventoryError = True
					return

				installedEnclosureFirmwareVersion = re.match('.*Firmware Version:\s+(\d+\.\d+|\d+).*', out, re.MULTILINE|re.DOTALL).group(1)
	
				self.logger.debug("The controller's enclosure firmware version was determined to be: " + installedEnclosureFirmwareVersion + ".")

				if installedEnclosureFirmwareVersion != csurEnclosureFirmwareVersion:
					self.componentUpdateDict['Firmware'][enclosure] = (self.firmwareDict[enclosure])[1]
					self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(enclosure, csurEnclosureFirmwareVersion, installedEnclosureFirmwareVersion, self.notVersionMatchMessage))
				else:
					self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(enclosure, csurEnclosureFirmwareVersion, installedEnclosureFirmwareVersion, self.versionMatchMessage))

			#Get a list of all hard drives and thier firmware version.
			command = arrayCfgUtilFile + " ctrl slot=" + controllerSlot + " pd all show detail"
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			self.logger.debug("The output of the command (" + command + ") used to get the hard drive list and their firmware version was: " + out.strip())
	
			if result.returncode != 0:
				self.logger.error("Failed to get hard drive versions.\n" + err)
				self.inventoryError = True
				return

			#Separate each hard drive into an element in a list.
			hardDriveDataList = re.findall('Firmware\s+Revision:\s+[0-9,A-Z]{4}\s+Serial\s+Number:\s+[0-9,A-Z]+\s+Model:\s+HP\s+[0-9,A-Z]+', out, re.MULTILINE|re.DOTALL)

			self.logger.debug("The hard drive data list was determined to be: " + str(hardDriveDataList) + ".")

			for hardDrive in hardDriveDataList:
				hardDriveData = hardDrive.split()
				hardDriveVersion = hardDriveData[-1] + ' ' + hardDriveData[2]
				hardDriveList.append(hardDriveVersion)

		#Sort the hard drive list since it may not be sorted due to multiple controllers.
		hardDriveList.sort()

		self.logger.debug("The hard drive list was determined to be: " + str(hardDriveList) + ".")

		#Get a unique list of hard drives managed by the controllers.
		hardDriveModels = []
		count = 0
		
		for hd in hardDriveList:
			hardDriveData = hd.split()

			if count == 0:
				hardDriveModels.append(hardDriveData[0])
				tmpHardDriveModel = hardDriveData[0]
				count += 1
			elif hardDriveData[0] != tmpHardDriveModel:
				hardDriveModels.append(hardDriveData[0])
				tmpHardDriveModel = hardDriveData[0]

		self.logger.debug("The hard drive models were determined to be: " + str(hardDriveModels))

		#Now check each hard drive's firmware version.
		for hardDriveModel in hardDriveModels:
			hardDriveVersionMismatch = False

			try:
				csurHardDriveFirmwareVersion = (self.firmwareDict[hardDriveModel])[0]
			except KeyError:
				#This accounts for the cases where the CSUR did not include a hard drive's firmware.
				self.logger.error("Firmware for the hard drive model " + hardDriveModel + " is missing from the csur bundle.")
				self.inventoryError = True
				continue

			#Now check every hard drive's firmware version that matches the current hardDriveModel.
			for hd in hardDriveList:
				hardDriveData = hd.split()

				if hardDriveData[0] == hardDriveModel:
					installedHardDriveFirmwareVersion = hardDriveData[1]

					self.logger.debug("The hard drive's firmware version was determined to be: " + installedHardDriveFirmwareVersion + ".")

					'''
					If the hard drive version does not match the CSUR version then add it to the firmwareUpdateList.
					We only care about a one time occurance of a firmware mis-match.
					'''
					if installedHardDriveFirmwareVersion != csurHardDriveFirmwareVersion:
						self.componentUpdateDict['Firmware'][hardDriveModel] = (self.firmwareDict[hardDriveModel])[1]
						self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(hardDriveModel, csurHardDriveFirmwareVersion, installedHardDriveFirmwareVersion, self.notVersionMatchMessage))
						hardDriveVersionMismatch = True
						break

			if not hardDriveVersionMismatch:
				self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(hardDriveModel, csurHardDriveFirmwareVersion, installedHardDriveFirmwareVersion, self.versionMatchMessage))

		self.logger.info("Done getting the storage firmware inventory.")

	#End __getStorageFirmwareInventory(self):


	'''
	This function gets the local OS hard drives needing a firmware update.
	'''
	def __getLocalOSHardDriveFirmwareInventory(self):
		self.logger.info("Getting the local OS hard drive firmware inventory.")

		#hpacucli has been replaced by hpssacli so we need to check in case we are on an older system.
		if os.path.isfile('/usr/sbin/hpssacli'):
			arrayCfgUtilFile = '/usr/sbin/hpssacli'
		else:
			arrayCfgUtilFile = '/usr/sbin/hpacucli'

		#Get list of storage controllers, since we can't just specify internal to start with.
		command = arrayCfgUtilFile + " ctrl all show"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to get the list of attached storage controllers was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Failed to get the list of attached storage controllers.\n" + err)
			self.inventoryError = True
			return

		#Only match on the internal storage controller which is used for the OS.
		if re.match('\s*Smart\s+Array\s+P\d{3}i\s+in\s+Slot\s+\d{1}', out, re.MULTILINE|re.DOTALL):
			controllerModel = re.match('\s*Smart\s+Array\s+(P\d{3}i)\s+in\s+Slot\s+\d{1}', out, re.MULTILINE|re.DOTALL).group(1)
			controllerSlot = re.match('\s*Smart\s+Array\s+P\d{3}i\s+in\s+Slot\s+(\d{1})', out, re.MULTILINE|re.DOTALL).group(1)
		else:
			self.logger.error("Failed to get the internal storage controller's information.")
			self.inventoryError = True
			return

		self.logger.debug("The controller was determined to be: " + controllerModel + " in slot " + controllerSlot + ".")

		hardDriveList = [] #This is a complete list of hard drives from the controller. An example element is 'EG0600FBVFP HPDC'.

		#Get a list of all hard drives and thier firmware version.
		command = arrayCfgUtilFile + " ctrl slot=" + controllerSlot + " pd all show detail"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to get the hard drive list and their firmware version was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Failed to get hard drive versions.\n" + err)
			self.inventoryError = True
			return

		#Separate each hard drive into an element in a list.
		hardDriveDataList = re.findall('Firmware\s+Revision:\s+[0-9,A-Z]{4}\s+Serial\s+Number:\s+[0-9,A-Z]+\s+Model:\s+HP\s+[0-9,A-Z]+', out, re.MULTILINE|re.DOTALL)

		self.logger.debug("The hard drive data list was determined to be: " + str(hardDriveDataList) + ".")

		for hardDrive in hardDriveDataList:
			hardDriveData = hardDrive.split()
			hardDriveVersion = hardDriveData[-1] + ' ' + hardDriveData[2]
			hardDriveList.append(hardDriveVersion)

		#Sort the hard drive list since it may not be sorted.
		hardDriveList.sort()

		self.logger.debug("The hard drive list was determined to be: " + str(hardDriveList) + ".")

		#Get a unique list of hard drives managed by the controller.
		hardDriveModels = []
		count = 0
		
		for hd in hardDriveList:
			hardDriveData = hd.split()

			if count == 0:
				hardDriveModels.append(hardDriveData[0])
				tmpHardDriveModel = hardDriveData[0]
				count += 1
			elif hardDriveData[0] != tmpHardDriveModel:
				hardDriveModels.append(hardDriveData[0])
				tmpHardDriveModel = hardDriveData[0]

		self.logger.debug("The hard drive models were determined to be: " + str(hardDriveModels))

		#Now check each hard drive's firmware version.
		for hardDriveModel in hardDriveModels:
			hardDriveVersionMismatch = False

			try:
				csurHardDriveFirmwareVersion = (self.firmwareDict[hardDriveModel])[0]
			except KeyError:
				#This accounts for the cases where the CSUR did not include a hard drive's firmware.
				self.logger.error("Firmware for the hard drive model " + hardDriveModel + " is missing from the csur bundle.")
				self.inventoryError = True
				continue

			#Now check every hard drive's firmware version that matches the current hardDriveModel.
			for hd in hardDriveList:
				hardDriveData = hd.split()

				if hardDriveData[0] == hardDriveModel:
					installedHardDriveFirmwareVersion = hardDriveData[1]

					self.logger.debug("The hard drive's firmware version was determined to be: " + installedHardDriveFirmwareVersion + ".")

					'''
					If the hard drive version does not match the CSUR version then add it to the firmwareUpdateList.
					We only care about a one time occurance of a firmware mis-match.
					'''
					if installedHardDriveFirmwareVersion != csurHardDriveFirmwareVersion:
						self.componentUpdateDict['Firmware'][hardDriveModel] = (self.firmwareDict[hardDriveModel])[1]
						hardDriveVersionMismatch = True
						break

		self.logger.info("Done getting the local OS hard drive firmware inventory.")

	#End __getLocalOSHardDriveFirmwareInventory(self):


	'''
	This function gets the NIC cards needing a firmware update.
	'''
	def __getNICFirmwareInventory(self):
		nicCardModels = [] #This contains the list of NIC cards that were found, e.g. ['331FLR', '560SFP+'].
		count = 0

		self.logger.info("Getting the NIC card firmware inventory.")

		nicBusList = self.__getNicBusList()

		#Before continuing check to make sure that there wss not an issue getting the NIC bus list.
		if nicBusList == 'NICBusFailure':
			return

		#Get a unique list of NIC card models from the bus list, which has contents such as: ['03:00.0 331FLR', '44:00.0 560SFP+', '47:00.0 560SFP+'].
		for nd in nicBusList:
			nicCardData = nd.split()

			if count == 0:
				nicCardModels.append(nicCardData[1])
				tmpNicCardModel = nicCardData[1]
				count += 1
			elif nicCardData[1] != tmpNicCardModel:
				nicCardModels.append(nicCardData[1])
				tmpNicCardModel = nicCardData[1]

		self.logger.debug("The NIC card models were determined to be: " + str(nicCardModels) + ".")

		#Get NIC card list which will be used to map the NIC card bus to its associated NIC device.
		command = "ifconfig -a"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to get the NIC card list was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Failed to get the Compute Node's NIC card list.\n" + err)
			self.inventoryError = True
			return

		#The nicCardList will be similar to: ['em0', 'em1', 'em2', 'em3', 'p4p1', 'p4p2', 'p5p1', 'p5p2', 'p7p1', 'p7p2', 'p8p1', 'p8p2'].
		nicCardList = re.findall('^[empth0-9]{3,}', out, re.MULTILINE|re.DOTALL)

		self.logger.debug("The NIC card list was determined to be: " + str(nicCardList) + ".")

		'''
		Loop through all NIC cards to check thier firmware.  Only record one occcurance of a mismatch,
		since that is all that is needed to confirm a firmware update is needed.
		'''
		for nicCardModel in nicCardModels:
			nicCardVersionMismatch = False
			count = 0

			try:
				csurNicCardFirmwareVersion = (self.firmwareDict[nicCardModel])[0]
			except KeyError:
				#This accounts for the cases where the CSUR did not include a NIC card's firmware.
				self.logger.error("Firmware for the NIC card model " + nicCardModel + " is missing from the csur bundle.")
				self.inventoryError = True
				continue

			for data in nicBusList:
				nicCardData = data.split()

				nicBus = nicCardData[0]
				installedNicCardModel = nicCardData[1]

				if installedNicCardModel == nicCardModel:
					for nic in nicCardList:
						command = "ethtool -i " + nic
						result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
						out, err = result.communicate()

						self.logger.debug("The output of the command (" + command + ") used to check the NIC card firmware was: " + out.strip())

						if result.returncode != 0:
                                                        self.logger.error("Failed to get the NIC card information for (" + nic + ").\n" + err)
                                                        self.inventoryError = True
                                                        continue

                                                if nicBus in out:
                                                        nicDevice = nic
                                                else:
                                                        continue

						versionList = out.splitlines()

						for line in versionList:
							if 'firmware-version' in line:
								firmwareList = line.split()
								
								'''
								tg3 firmware versions are listed differently then other NIC cards.
								e.g. firmware-version: 5720-v1.37 NCSI v1.3.12.0
								and it is the boot code version that we want.
								'''
								if '5719-v' in line or '5720-v' in line:
									installedNicCardFirmwareVersion = re.match('\d{4}-(.*)', firmwareList[1]).group(1)
								else:
									installedNicCardFirmwareVersion = firmwareList[-1]

						self.logger.debug("The NIC card firmware version was determined to be: " + str(installedNicCardFirmwareVersion) + ".")

						if installedNicCardFirmwareVersion != csurNicCardFirmwareVersion and count == 0:
							self.componentUpdateDict['Firmware'][nicCardModel] = (self.firmwareDict[nicCardModel])[1]
							count += 1
							nicCardVersionMismatch = True
							self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(nicCardModel, csurNicCardFirmwareVersion, installedNicCardFirmwareVersion, self.notVersionMatchMessage))
						break #We only get here if a NIC card matched the nicBus we are looking at.
				else:
					continue
	
				#Break out and get the next NIC card model if a firmware mismatch was found.
				if count == 1:
					break

			if not nicCardVersionMismatch:
				self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(nicCardModel, csurNicCardFirmwareVersion, installedNicCardFirmwareVersion, self.versionMatchMessage))

		self.logger.info("Done getting the NIC card firmware inventory.")

	#End __getNICFirmwareInventory(self):


	'''
	This function is used to get the nic bus list and associated NIC card model.
	The bus list will be used to futher determine the associated ethernet device.
	'''
	def __getNicBusList(self):
		nicBusList = []
		busDict = {}
		modelCrossRefDict = {'NetXtreme BCM5719' : '331FLR', 'Intel Corporation 82599' : '560SFP+', 'Mellanox Technologies' : 'HP544QSFP'}

		self.logger.info("Getting the NIC bus list.")

		command = 'lspci -vv'

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
                        self.logger.error("Failed to get the Compute Node's NIC bus list.\n" + err)
                        self.inventoryError = True
                        return 'NICBusFailure'

		self.logger.debug("The output of the command (" + command + ") used to get the NIC card bus information was: " + out.strip())

		#This is done so that we can break the lspci results into a list for each device on the bus.
		out = re.sub('\n{2,}', '####', out)
		deviceList = out.split('####')

		for device in deviceList:
			if 'Ethernet controller' in device or 'Network controller' in device:
				if self.systemModel == 'DL580G7' or self.systemModel =='DL980G7' or self.systemModel =='BL680cG7': # NC375T, NC375i, NC550SFP
					bus = re.match('([0-9a-f]{2}:[0-9a-f]{2}\.[0-9]).*(NC[0-9]+[a-z]{1,3}).*', device, re.IGNORECASE|re.MULTILINE|re.DOTALL)
				elif self.systemModel == 'DL380pGen8':
					bus = re.match('([0-9a-f]{2}:[0-9a-f]{2}\.[0-9]).*(NetXtreme BCM5719|NC552SFP).*', device, re.MULTILINE|re.DOTALL)
				elif self.systemModel == 'DL580Gen8':
					bus = re.match('([0-9a-f]{2}:[0-9a-f]{2}\.[0-9]).*(NetXtreme BCM5719|Intel Corporation 82599).*', device, re.MULTILINE|re.DOTALL)
				elif self.systemModel == 'DL580Gen9' or self.systemModel == 'DL320eGen8v2':
					bus = re.match('([0-9a-f]{2}:[0-9a-f]{2}\.[0-9]).*Product Name:.*(331FLR|331T|544\+QSFP|560SFP\+|331T|561T|332i|332T)\s+Adapter.*', device, re.MULTILINE|re.DOTALL)

				busPrefix = bus.group(1)[:-2]

				if busPrefix not in busDict:
					busDict[busPrefix] = ''
					
					if self.systemModel == 'DL580Gen8':
						nicBusList.append(bus.group(1) + ' ' + modelCrossRefDict[bus.group(2)])
					elif self.systemModel == 'DL380pGen8':
						if bus.group(2) == 'NC552SFP':
							nicBusList.append(bus.group(1) + ' ' + bus.group(2))
						else:
							nicBusList.append(bus.group(1) + ' ' + modelCrossRefDict[bus.group(2)])
					else:
						nicBusList.append(bus.group(1) + ' ' + bus.group(2))

		nicBusList.sort(key=lambda n: n.split()[1])

		self.logger.debug("The NIC card bus list was determined to be: " + str(nicBusList) + ".")

		self.logger.info("Done getting the NIC bus list.")

		return nicBusList

	#End __getNicBusList(self):


	'''
	This function is used to get the common compute node components (BIOS, iLO)
	which need a firmware update.
	'''
	def __getCommonFirmwareInventory(self):
		biosFirmwareType = "BIOS" + self.systemModel

		self.logger.info("Getting the compute node common firmware inventory.")

		#BIOS
		command = "dmidecode -s bios-release-date"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to get the compute node's BIOS information was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Failed to get the compute node's BIOS firmware version.\n" + err)
			self.inventoryError = True
		else:
			biosFirmwareDate = out.strip()
			biosFirmwareDateList = biosFirmwareDate.split('/')
			installedBiosFirmwareVersion = biosFirmwareDateList[2] + '.' + biosFirmwareDateList[0] + '.' + biosFirmwareDateList[1]

			self.logger.debug("The compute node's bios version was determined to be: " + installedBiosFirmwareVersion + ".")

			csurBiosFirmwareVersion = (self.firmwareDict[biosFirmwareType])[0]

			if installedBiosFirmwareVersion != csurBiosFirmwareVersion:
				self.componentUpdateDict['Firmware'][biosFirmwareType] = (self.firmwareDict[biosFirmwareType])[1]
				self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('BIOS', csurBiosFirmwareVersion, installedBiosFirmwareVersion, self.notVersionMatchMessage))
			else:
				self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('BIOS', csurBiosFirmwareVersion, installedBiosFirmwareVersion, self.versionMatchMessage))

		#iLO
		command = "hponcfg -g"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to get the compute node's iLO information was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Failed to get the Compute Node's iLO firmware version.\n" + err)
			self.inventoryError = True
		else:
			installedILOFirmwareVersion = re.match('.*Firmware Revision\s+=\s+(\d+\.\d+).*', out, re.MULTILINE|re.DOTALL).group(1)

			self.logger.debug("The compute node's iLO version was determined to be: " + installedILOFirmwareVersion + ".")

			csurILOFirmwareVersion = (self.firmwareDict[self.iLOFirmwareType])[0]

			if installedILOFirmwareVersion != csurILOFirmwareVersion:
				self.componentUpdateDict['Firmware']['iLO'] = (self.firmwareDict[self.iLOFirmwareType])[1]
				self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('iLO', csurILOFirmwareVersion, installedILOFirmwareVersion, self.notVersionMatchMessage))
			else:
				self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('iLO', csurILOFirmwareVersion, installedILOFirmwareVersion, self.versionMatchMessage))

		#HBA
                #Check if the system has any HBAs that need to be updated.

                #First check if the system has HBAs and if so check their firmware version as well.
                command = 'systool -c scsi_host -v'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()

                self.logger.debug("The output of the command (" + command + ") used to get the compute node's HBA information was: " + out.strip())

                if result.returncode != 0:
                        self.logger.error("Failed to get compute node's HBA information.\n" + err)
                        self.inventoryError = True
                else:
                        if re.search('HBA', out, re.MULTILINE|re.DOTALL) != None:
                                hostList = out.split('Device = "')
                                for host in hostList:
                                        if re.search('HBA', host, re.MULTILINE|re.DOTALL) != None:
                                                installedHBAFirmwareVersion = ''
                                                hbaModel = ''
                                                hostDataList = host.splitlines()

                                                for data in hostDataList:
                                                        if re.match('\s+fw_version', data) != None:
                                                                installedHBAFirmwareVersion = re.match('\s*fw_version\s+=\s+"(.*)\s+\(', data).group(1)
                                                                self.logger.debug("The HBA's firmware version was determined to be: " + installedHBAFirmwareVersion + ".")

                                                        if re.match('\s*model_name', data) != None:
                                                                hbaModel = re.match('\s*model_name\s+=\s+"(.*)"', data).group(1)
                                                                self.logger.debug("The HBA's model was determined to be: " + hbaModel + ".")

                                                        if installedHBAFirmwareVersion != '' and hbaModel != '':
                                                                try:
                                                                        csurHBAFirmwareVersion = (self.firmwareDict[hbaModel])[0]
                                                                except KeyError:
                                                                        #This accounts for the cases where the CSUR did not include a HBA's firmware.
                                                                        self.logger.error("Firmware for the HBA model " + hbaModel + " is missing from the csur bundle.")
                                                                        self.inventoryError = True
                                                                        break

                                                                if installedHBAFirmwareVersion != csurHBAFirmwareVersion:
                                                                        if not hbaModel in self.componentUpdateDict['Firmware']:
                                                                                self.componentUpdateDict['Firmware'][hbaModel] = (self.firmwareDict[hbaModel])[1]

									self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(hbaModel, csurHBAFirmwareVersion, installedHBAFirmwareVersion, self.notVersionMatchMessage))
								else:
									self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(hbaModel, csurHBAFirmwareVersion, installedHBAFirmwareVersion, self.versionMatchMessage))

                                                                break

                #PMC
                '''
                Check if the system's Power Management Controller needs to be updated.
                '''
                if not self.systemModel in self.noPMCFirmwareUpdateModels:
			installedPMCFirmwareVersion = ''

                        command = "dmidecode"
                        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        out, err = result.communicate()

                        self.logger.debug("The output of the command (" + command + ") used to get the compute node's dmidecode information was: " + out.strip())

                        if result.returncode != 0:
                                self.logger.error("Failed to get compute node's dmidecode information needed to determine the Power Management Contoller's firmware version.\n" + err)
                                self.inventoryError = True
                        else:
                                dmidecodeList = out.splitlines()
                                found = False

                                for data in dmidecodeList:
                                        if not found and (re.match('^\s*Power Management Controller Firmware\s*$', data) != None):
                                                found = True
                                                continue
                                        elif found:
                                                installedPMCFirmwareVersion = data.strip()
						self.logger.debug("The Power Management Controller's firmware version was determined to be: " + installedPMCFirmwareVersion + ".")
                                                break
                                        else:
                                                continue

				#This means the PMC's firmware version was present in the dmidecode output.
				if installedPMCFirmwareVersion != '':
					pmcCSURReference = 'PMC' + self.systemModel

					try:
						csurPMCFirmwareVersion = (self.firmwareDict[pmcCSURReference])[0]
					except KeyError:
						#This accounts for the cases where the CSUR did not include a PMC's firmware.
						self.logger.error("Firmware for the Power Management Controller is missing from the csur bundle.")
						self.inventoryError = True
					else:
						if installedPMCFirmwareVersion != csurPMCFirmwareVersion:
							self.componentUpdateDict['Firmware'][pmcCSURReference] = (self.firmwareDict[pmcCSURReference])[1]
							self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('PMC', csurPMCFirmwareVersion, installedPMCFirmwareVersion, self.notVersionMatchMessage))
						else:
							self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('PMC', csurPMCFirmwareVersion, installedPMCFirmwareVersion, self.versionMatchMessage))
				else:
					#This accounts for the cases where the output of dmidecode did not include a PMC's firmware version.
					self.logger.error("The Power Management Controller's firmware version was not found in the output of dmidecode.")
					self.inventoryError = True

		self.logger.info("Done getting the compute node common firmware inventory.")

	#End __getCommonFirmwareInventory(self):


	'''
	This function is used to get the list of drivers which need to be updated.
	'''
	def __getDriverInventory(self):
		started = False
                driversFound = False
		updateDriverList = []

		'''
		Keep track of Mellanox driver count, since systems can have one or the other.  Thus, it
		will fail on one of them, but as long as one of them is found things are ok.
		'''
		mlnxCount = 0

		self.logger.info("Getting the driver inventory.")

		'''
		Don't start the comparison until the section in the csur data is found for the correct
		compute node model and OS version.  It loops until a blank line is encountered which 
		represents the end of the driver section.
		'''
            	for data in self.computeNodeResources:
                        #Remove spaces if any are present.
                        data = data.replace(' ', '')

                        if not 'Drivers' in data and not driversFound:
                                continue
                        elif 'Drivers' in data:
                                driversFound = True
                                continue
                        elif not ((self.osDistLevel in data) and (self.systemModel in data)) and not started:
                                continue
                        elif (self.osDistLevel in data) and (self.systemModel in data):
                                started = True
                                continue
                        elif re.match(r'\s*$', data):
                                break
                        else:
                                csurDriverList = data.split('|')
				csurDriver = csurDriverList[0]
				csurDriverVersion = csurDriverList[1]

				command = "modinfo " + csurDriver
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				self.logger.debug("The output of the command (" + command + ") used to get the driver information was: " + out.strip())

				if result.returncode != 0:
					if (csurDriver == 'mlx4_en' or csurDriver == 'mlnx') and mlnxCount == 0:
						self.logger.warn("The first Mellanox driver checked (" + csurDriver + ") appears not to be the driver being used.\n" + err)
						mlnxCount += 1
						continue
					else:
						self.logger.error("Failed to get the Compute Node's driver version for driver " + csurDriver + ".\n" + err)
						self.inventoryError = True
			
				#Need to use a list to search for the version, since different drivers have a different format.
				driverDataList = out.splitlines()

				for data in driverDataList:
					if re.match('version:\s+.*', data) != None:
						versionList = data.split()
						installedDriverVersion = versionList[1]
						break

				self.logger.debug("The driver version was determined to be: " + installedDriverVersion + ".")

				if installedDriverVersion != csurDriverVersion:
					self.componentUpdateDict['Drivers'][csurDriver] = csurDriverList[2]
					self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurDriver, csurDriverVersion, installedDriverVersion, self.notVersionMatchMessage))
				else:
					self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurDriver, csurDriverVersion, installedDriverVersion, self.versionMatchMessage))

		self.logger.info("Done getting the driver inventory.")

	#End __getDriverInventory(self):


	'''
	This function is used to get the list of software packages which need to be updated.
	The package epoch date is used to determine if an update is needed.
	'''
        def __getSoftwareInventory(self):
                started = False
                softwareFound = False
                updateSoftwareList = []

		self.logger.info("Getting the software inventory.")

                for data in self.computeNodeResources:
			#Remove spaces if any are present.
			data = data.replace(' ', '')

                        if not 'Software' in data and not softwareFound:
                                continue
                        elif 'Software' in data:
                                softwareFound = True
                                continue
                        elif not ((self.osDistLevel in data) and (self.systemModel in data)) and not started:
                                continue
                        elif (self.osDistLevel in data) and (self.systemModel in data):
                                started = True
                                continue
                        elif re.match(r'\s*$', data):
                                break
                        else:
                                csurSoftwareList = data.split('|')
                                csurSoftware = csurSoftwareList[0]
                                csurSoftwareEpoch = csurSoftwareList[1]
				csurSoftwareVersion = csurSoftwareList[2]

                                command = "rpm -q --queryformat=%{buildtime}':'%{version}'-'%{release} " + csurSoftware
                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()

				self.logger.debug("The output of the command (" + command + ") used to get the software epoch and version information was: " + out.strip())

                                if result.returncode != 0:
					if "is not installed" in out:
						self.componentUpdateDict['Software'][csurSoftware] = csurSoftwareList[3]
						self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurSoftware, csurSoftwareVersion, 'Not Installed', self.versionMatchWarningMessage))
						continue
					else:
						self.logger.error("Failed to get the Compute Node's software version for software " + csurSoftware + ".\n" + err)
						self.inventoryError = True
						continue

				rpmInformationList = out.strip().split(':')

                                installedSoftwareEpoch = rpmInformationList[0]
				installedSoftwareVersion = rpmInformationList[1]

				self.logger.debug("The software epoch date was determined to be: " + installedSoftwareEpoch + ".")

                                if installedSoftwareEpoch < csurSoftwareEpoch:
					self.componentUpdateDict['Software'][csurSoftware] = csurSoftwareList[3]
					self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurSoftware, csurSoftwareVersion, installedSoftwareVersion, self.notVersionMatchMessage))
				else:
					self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurSoftware, csurSoftwareVersion, installedSoftwareVersion, self.versionMatchMessage))

		self.logger.info("Done getting the software inventory.")

        #End __getSoftwareInventory(self):


	'''
	This function is used to check if storage is local, since systems with external storage 
	also have internal storage.  Otherwise, SAN storage is used.
	'''
	def __getLocalStorage(self):
		self.logger.info("Checking to see if there is any local storage.")

                #hpacucli has been replaced by hpssacli so we need to check in case we are on an older system.
                if os.path.isfile('/usr/sbin/hpssacli'):
                        arrayCfgUtilFile = '/usr/sbin/hpssacli'
                else:
                        arrayCfgUtilFile = '/usr/sbin/hpacucli'

                #Get list of storage controllers.
                command = arrayCfgUtilFile + " ctrl all show"
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()

                self.logger.debug("The output of the command (" + command + ") used to check if storage is local was: " + out.strip())

                if result.returncode != 0:
			#Make sure the command did not have issues before returning 'Absent'.
			if 'No controllers detected' in out:
				self.logger.warn("There were no controllers detected.\n" + err)
				return 'Absent'
			else:
				self.logger.error("Failed to get the list of storage controllers.\n" + err)
				self.inventoryError = True
				return 'Error'
		else:
			return 'Present'

		self.logger.info("Done checking to see if there is any local storage.")

	#End __getLocalStorage(self):


	'''
	This function returns the dictionary containing the components that need to be updated.
	'''
	def getComponentUpdateDict(self):
		return self.componentUpdateDict
	#End getComponentUpdateDict(self):


	'''
	This function is used to determine if there were any issues getting the component update inventory information.
	'''
	def getInventoryStatus(self):
		return self.inventoryError
	#End getInventoryStatus(self):


	'''
	This function is an interface that classes that subclass this class can implement.
	'''
	def _getComputeNodeSpecificFirmwareInventory(self):
		pass
	#End _getComputeNodeSpecificFirmwareInventory(self):


	'''
	This function is an interface that classes that subclass this class can implement.
	'''
	def _getComputeNodeSpecificDriverInventory(self):
		pass
	#End _getComputeNodeSpecificDriverInventory(self):


	'''
	This function is an interface that classes that subclass this class can implement.
	'''
	def _getComputeNodeSpecificSoftwareInventory(self):
		pass
	#End _getComputeNodeSpecificSoftwareInventory(self):
	

	'''
	This function is used to identify whether or not external storage was present
	since external storage requires power to be removed and re-applied in order for
	a firmware update to take affect.
	'''
	def isExternalStoragePresent(self):
		return self.externalStoragePresent
	#End isExternalStoragePresent(self):

#End class ComputeNodeInventory:


'''
This is a subclass of ComputeNode for the Gen1 compute nodes, which is used for getting Gen1
FusionIO configuration information.
'''
class Gen1ScaleUpComputeNodeInventory(ComputeNodeInventory):

	def __init__(self, computeNodeDict, noPMCFirmwareUpdateModels, computeNodeResources, fusionIOSoftwareInstallPackageList):
                ComputeNodeInventory.__init__(self, computeNodeDict, noPMCFirmwareUpdateModels, computeNodeResources)

		#self.busList contains the list of ioDIMM buses that require a firmware update.
                self.busList = []

		self.fusionIOSoftwareInstallPackageList = fusionIOSoftwareInstallPackageList

	#End __init__(self, computeNodeDict, noPMCFirmwareUpdateModels, computeNodeResources, fusionIOSoftwareInstallPackageList):


	'''
	This function is used to add the FusionIO to the firmware update list if it needs to be updated.
	Additionally, it updates the busList with the bus id of the ioiDIMM needing to be updated.
	'''
	def _getComputeNodeSpecificFirmwareInventory(self):
		self.logger.info("Getting the compute node's FusionIO firmware inventory.")

		#Fusion-IO
		command = "fio-status"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to get the FusionIO firmware information was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Failed to get the FusionIO status information needed to determine the FusionIO firmware version information.\n" + err)
			self.inventoryError = True
			return

		fioStatusList = out.splitlines()

		count = 0
		ioDIMMStatusDict = {}

		firmwareUpdateRequired = 'no'
		csurFusionIOFirmwareVersion = (self.firmwareDict['FusionIO'])[0]

		for line in fioStatusList:
			line = line.strip()

			'''
			Each ioDIMM section contains the firmware and bus information for each ioDIMM on seperate lines.
			Thus, it takes a two counts to find them both.
			'''
			if "Firmware" in line or re.search('PCI:[0-9a-f]{2}:[0-9]{2}\.[0-9]{1}', line):
				if "Firmware" in line:
					ioDIMMStatusDict['Firmware'] = re.match("Firmware\s+(v([0-9]\.){2}[0-9]{1,2})", line).group(1)
					self.logger.debug("The ioDIMM firmware version was determined to be: " + ioDIMMStatusDict['Firmware'] + ".")
				else:
					ioDIMMStatusDict['bus'] = re.match('.*([0-9a-f]{2}:[0-9]{2}\.[0-9]{1})', line).group(1)
					self.logger.debug("The ioDIMM bus was determined to be: " + ioDIMMStatusDict['bus'] + ".")
				count += 1

			if count == 2:
				if ioDIMMStatusDict['Firmware'] != csurFusionIOFirmwareVersion:
					self.busList.append(ioDIMMStatusDict['bus'])

					if firmwareUpdateRequired == 'no':
                                                self.componentUpdateDict['Firmware']['FusionIO'] = (self.firmwareDict['FusionIO'])[1]
						firmwareUpdateRequired = 'yes'

					self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('FusionIOBus: ' + ioDIMMStatusDict['bus'], csurFusionIOFirmwareVersion, ioDIMMStatusDict['Firmware'], self.notVersionMatchMessage))
				else:
					self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('FusionIOBus: ' + ioDIMMStatusDict['bus'], csurFusionIOFirmwareVersion, ioDIMMStatusDict['Firmware'], self.versionMatchMessage))

				ioDIMMStatusDict.clear()
				count = 0

		self.logger.info("Done getting the compute node's FusionIO firmware inventory.")

	#End _getComputeNodeSpecificFirmwareInventory(self)


	'''
	This function is used to add the FusionIO to the driver update dictionary if it needs to be updated.
	'''
	def _getComputeNodeSpecificDriverInventory(self):
		started = False
		updateDriverList = []

		self.logger.info("Getting the compute node's FusionIO driver inventory.")

		#Get the csur driver version and then the installed driver version.
		for data in self.computeNodeResources:
			#Remove spaces if any are present.
			data = data.replace(' ', '')

			if not re.match('FusionIODriver', data) and not started:
				continue
			elif re.match('FusionIODriver', data):
				started = True
				continue
			else:
				csurDriverList = data.split('|')
				csurDriverVersion = csurDriverList[1]

				command = "modinfo iomemory_vsl"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				self.logger.debug("The output of the command (" + command + ") used to get the FusionIO driver information was: " + out.strip())

				if result.returncode != 0:
					self.logger.error("Failed to get the FusionIO driver information.\n" + err)
					self.inventoryError = True
				else:
					installedDriverVersion = re.match('.*srcversion:\s+([1-3][^\s]+)', out, re.MULTILINE|re.DOTALL).group(1)

					self.logger.debug("The FusionIO driver version was determined to be: " + installedDriverVersion + ".")

					if installedDriverVersion != csurDriverVersion:
						self.componentUpdateDict['Drivers']['iomemory_vsl'] = csurDriverList[2]
						self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('iomemory_vsl', csurDriverVersion, installedDriverVersion, self.notVersionMatchMessage))
					else:
						self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('iomemory_vsl', csurDriverVersion, installedDriverVersion, self.versionMatchMessage))

				break

		self.logger.info("Done getting the compute node's FusionIO driver inventory.")
 
	#End _getComputeNodeSpecificDriverInventory(self):


	'''
	This function is used to add the FusionIO software to the software update dictionary if it needs to be updated.
	The title FusionIOSoftware begins the FusionIO software section in the resource file and ends when
	a blank line is encountered.
	Additionally, we will update all FusionIO software if one package is found to be out of date or missing, which
	also implies that we will remove all FusionIO software as well so that we start with a clean baseline.
	'''
	def _getComputeNodeSpecificSoftwareInventory(self):
		softwareFound = False
		updateRequired = False

		self.logger.info("Getting the compute node's FusionIO software inventory.")

		#The loop will be broken out of as soon as one package is found to be out of date or missing.
		for data in self.computeNodeResources:
			#Remove spaces if any are present.
			data = data.replace(' ', '')

			if not re.match('FusionIOSoftware', data) and not softwareFound:
				continue
			elif re.match('FusionIOSoftware', data):
				softwareFound = True
				continue
			elif re.match(r'\s*$', data):
				break
			else:
				csurSoftwareList = data.split('|')
				csurSoftware = csurSoftwareList[0]
				csurSoftwareEpoch = csurSoftwareList[1]
				csurSoftwareVersion = csurSoftwareList[2]

                                command = "rpm -q --queryformat=%{buildtime}':'%{version}'-'%{release} " + csurSoftware
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				self.logger.debug("The output of the command (" + command + ") used to get the software epoch information was: " + out.strip())

				if result.returncode != 0:
					#If I recall correctly this message has been seen in both STDERR and STDOUT.
					if "is not installed" in err or "is not installed" in out:
						if not updateRequired:
							updateRequired = True

						self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurSoftware, csurSoftwareVersion, 'Not Installed', self.versionMatchWarningMessage))
						continue
					else:
						self.logger.error("Failed to get the Compute Node's software version for software " + csurSoftware + ".\n" + err)
						self.inventoryError = True
						continue

				rpmInformationList = out.strip().split(':')

                                installedSoftwareEpoch = rpmInformationList[0]
				installedSoftwareVersion = rpmInformationList[1]

				self.logger.debug("The software epoch date was determined to be: " + installedSoftwareEpoch + ".")

                                if installedSoftwareEpoch < csurSoftwareEpoch:
					if not updateRequired:
						updateRequired = True

					self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurSoftware, csurSoftwareVersion, installedSoftwareVersion, self.notVersionMatchMessage))
				else:
					self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurSoftware, csurSoftwareVersion, installedSoftwareVersion, self.versionMatchMessage))

		if updateRequired:
			#Remove commas and extra whitespace from the original RPM list.
			updateSoftwareList = re.sub(',\s*', ' ', self.fusionIOSoftwareInstallPackageList)

			self.componentUpdateDict['Software']['FusionIO'] = updateSoftwareList

		self.logger.info("Done getting the compute node's FusionIO software inventory.")

	#End _getComputeNodeSpecificSoftwareInventory(self):


	'''
	This function is used to return the bus list of the FusionIO DIMMs that 
	require a firmware update.
	'''
	def getFusionIOBusList(self):
                return self.busList
	#End getFusionIOBusList(self):

#End class Gen1ScaleUpComputeNode(ComputeNodeInventory):
