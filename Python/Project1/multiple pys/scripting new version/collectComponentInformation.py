#!/usr/bin/python


import re
import getpass
import logging
from networkSwitch import NetworkSwitch
from sanSwitch import SANSwitch
from threePar import ThreePAR
from computeNodeInitialize import ComputeNodeInitialize
from csurUpdateUtils import (TimeFeedbackThread, RED, RESETCOLORS)
from computeNodeInventory import (ComputeNode, Gen1ScaleUpComputeNode)



class GetComponentInformation:
	def __init__(self, csurResourceDict):
		self.csurResourceDict = csurResourceDict
	#End __init__(self, csurResourceDict):


	def getComponentInformation(self):
		systemTypeDict = self.csurResourceDict['systemType']
		logBaseDir = self.csurResourceDict['logBaseDir']
		logLevel = self.csurResourceDict['logLevel']
		
		componentListDict = {'computeNodeList' : [], 'networkSwitchList' : [], 'sanSwitchList' : [], 'storeServList' : []}

		logger = logging.getLogger('mainApplicationLogger')

		if 'Scale-up' in systemTypeDict:
			systemType = 'Scale-up'	
			scaleUpConfiguration = systemTypeDict['Scale-up']
		else:
			systemType = 'Scale-out'	
			
			'''
			This is an example of the scaleOutDict contents: 
			systemConfigurationDict['systemType'] = {'Scale-out' : {'scaleOutType' : 'CS500', 'generation' : generation, 'componentList' : componentList}}
			'''
			scaleOutDict = systemTypeDict['Scale-out']
			generation = scaleOutDict['generation']
			componentList = scaleOutDict['componentList']
			scaleOutConfiguration = scaleOutDict['scaleOutType']

			#Get the component resources from the respective resource files for the components that were selected for an update.
			componentResourceList = self.__getComponentResources(componentList)

			if componentResourceList[0]:
				print RED + "\nAn error occurred while collecting component resources; check the application's log file for errors; exiting program execution." +  RESETCOLORS
				exit(1)

		if systemType == 'Scale-up':
			pass
		else:
			#When compute nodes are being updated we check to see if the local host is included to be updated.
			if componentList[0] == 'Compute Node':
				while 1:
					skipUpdate = False

					response = raw_input("Is the local host being updated [y|n]: ")
					response = response.strip().lower()

					if len(response) != 1:
						print "\tA valid response is y|n.  Please try again."
						continue

					if not re.match('y|n', response):
						print "\tA valid response is y|n.  Please try again."
						continue

					if response == 'y':
						try:
							computeNode = ComputeNode(self.csurResourceDict.copy())
						except KeyError as err:
							logger.error("The resource key (" + str(err) + ") was not present in the application's resource file.")
							print RED + "\nA resource key was not present in the application's resource file; check the application's log file for errors; exiting program execution." +  RESETCOLORS
							exit(1)
						except OSError as err:
							logger.error("Could not get the local host's hostname:\n" + str(err))
							print RED + "\nCould not get the local host's hostname; check the application's log file for errors; exiting program execution." +  RESETCOLORS
							exit(1)

						computeNodeDict = computeNode.computeNodeInitialize(componentResourceList[1]['ComputeNodeResources'][:])

						if len(computeNodeDict['errorMessages']) != 0:
							if self.__tryAgainQuery('Compute Node', computeNodeDict['errorMessages']):
								continue
						else:
							try:
								noPMCFirmwareUpdateModels = self.csurResourceDict['noPMCFirmwareUpdateModels']
							except KeyError as err:
								pass
								
							#Instantiate a compute node, which is used to get the compute node's inventory of components needing to be updated.
							computeNode = ComputeNode(computeNodeDict.copy(), noPMCFirmwareUpdateModels, self.csurResourceDict['csurData'])

							while 1:
								try:
									timeFeedbackThread = TimeFeedbackThread(componentMessage="\tRetrieving the compute node's component inventory")
									timeFeedbackThread.daemon = True
									timeFeedbackThread.start()

									computeNode.getComponentUpdateInventory()
								except KeyboardInterrupt:
									#****************************
									#Look at changing this from exiting to intercepting.
									exit(1)
								finally:
									timeFeedbackThread.stopTimer()

								#****************************
								#Look at making the error more verbose.
								if computeNode.getInventoryStatus():
									print RED + "\n\n\tThere were errors while performing the local compute node's inventory." +  RESETCOLORS

									while True:
										response = raw_input("\n\tDo you want to skip ('s') updating the local compute node or fix ('f') the problem and try again [s|f]: ")
										response = response.strip().lower()

										if len(response) != 1:
											print "\tA valid response is s|f.  Please try again."
											continue

										if not re.match('s|f', response):
											print "A valid response is s|f.  Please try again."
											continue
										elif(response == 's'):
											skipUpdate = True
											break
										else:
											break

									if skipUpdate:
										break
								else:
									break
			
							if not skipUpdate:
								componentUpdateDict = computeNode.getComponentUpdateDict()
								updateNeeded = False

								'''
								This gets a list of the dictionary sizes (Software, Drivers, Firmwware) so that
								it can be determined whether or not an update is needed.
								'''
								componentDictSizes = [len(dict) for dict in componentUpdateDict.values()]

								if any(x != 0 for x in componentDictSizes):
									componentListDict['computeNodeList'].append({'localhost' : {'computeNodeDict' : computeNodeDict, 'componentUpdateDict' : componentUpdateDict}})
								else:
									print "The local host is already up to date; skipping."

					break

			#Now go through the list of components that were selected to be updated and initialize them for the update.
			for component in componentList:
				while 1:
					invalidResponse = False
					tryAgain = False

					ip = raw_input("Enter the IP address of the " + component + " to be updated or enter to continue: ")

					ip = ip.strip()

					'''
					An empty string indicates the current component selection is done.
					Otherwise do some basic checking of the IP to see that its format is valid.
					'''
					if ip != '':
						if not self.__checkIP(ip):
							continue

						username = raw_input("Enter the admin user name for the " + component + ": ")
						username = username.strip()

						password = getpass.getpass(prompt = 'Enter the password for ' + username + ':')

						'''
						Give a chance to confirm the input before moving on to test/update.
						Since the SAN switch requires additional inputs we will check it later.
						'''
						if component != 'SAN Switch':
							if not self.__confirmInput(component, ip, username=username):
								continue

						if component == 'Compute Node':
							pass
						elif component == 'Network Switch':
							networkSwitch = NetworkSwitch(ip, username, password, logBaseDir, logLevel)

							resultDict = networkSwitch.checkSwitch(generation, componentResourceList[1]['NetworkSwitchResources'][:])

							if len(resultDict['errorMessages']) != 0:
								'''
								if 'resource' in resultDict['errorMessages']:
									print RED + resultDict['errorMessage'] + " Fix the problem and try again; exiting program execution." + RESETCOLORS
									exit(1)

								'''
								if self.__tryAgainQuery(component, resultDict['errorMessages']):
									continue
							else:
								if resultDict['updateNeeded']:
									componentListDict['networkSwitchList'].append(networkSwitch)
								else:
									logger.info("An update for network switch '" + ip + "' was not needed, since it is already up to date.")
						elif component == 'SAN Switch':
							while 1:
								localhostIP = raw_input("Enter the management IP address of the local system: ")
								localhostIP = localhostIP.strip()

								if self.__checkIP(localhostIP):
									break
							
							scpUsername = raw_input("Enter the user name of a user that can scp to/from this system: ")
							scpUsername = scpUsername.strip()

							scpPassword = getpass.getpass(prompt = 'Enter the password for ' + scpUsername + ':')

							if not self.__confirmInput(component, ip, localhostIP=localhostIP, scpUsername=scpUsername):
								continue
							
							sanSwitch = SANSwitch(ip, password, localhostIP, scpUsername, scpPassword, logBaseDir, logLevel)

							resultDict = sanSwitch.checkSwitch(componentResourceList[1]['SANSwitchResources'][:], self.csurResourceDict['sanSwitchCrossReference'])

							if len(resultDict['errorMessage']) != 0:
								'''
								if 'resource' in resultDict['errorMessage']:
									print RED + resultDict['errorMessage'] + " Fix the problem and try again; exiting program execution." + RESETCOLORS
									exit(1)

								'''
								if self.__tryAgainQuery(component, resultDict['errorMessages']):
									continue
							else:
								if resultDict['updateNeeded']:
									componentListDict['sanSwitchList'].append(sanSwitch)
								else:
									logger.info("An update for SAN switch '" + ip + "' was not needed, since it is already up to date.")
						elif component == '3PAR StoreServ':
							threePAR = ThreePAR(ip, username, password)

							spVersion = '4.4.0'
							storeServVersion = '3.2.1'

							resultDict = threePAR.check3PAR(spVersion, storeServVersion)

							if resultDict['errorType'] != '':
								if self.__tryAgainQuery(component, resultDict['errorType']):
									continue
							else:
								componentListDict['storeServList'].append({ip : {'username' : username, 'password' : password}})
					else:
						break

		return componentListDict

	#End getComponentInformation(self):


	'''
	This function is used to get component resource data, e.g. model, software, firmware, drivers, etc.
	from is respective resource file.
	If a resource file key is missing or a resource file cannot be read then the errorMessage variable 
	will be set and the function returns immediately.
	'''
	def __getComponentResources(self, componentList):
		componentResourceDict = {}
		errors = False

		logger = logging.getLogger('mainApplicationLogger')

		logger.info("Getting component resource data for " + ', '.join(componentList) + ".")

		for component in componentList:
			try:
				if component == 'Compute Node':
					resourceFile = self.csurResourceDict['computeNodeResourceFile']
				elif component == 'Network Switch':
					resourceFile = self.csurResourceDict['networkSwitchResourceFile']
				elif component == 'SAN Switch':
					resourceFile = self.csurResourceDict['sanSwitchResourceFile']
				elif component == '3PAR StoreServ':
					resourceFile = self.csurResourceDict['threePARResourceFile']
			except KeyError as err:
				errors = True
				logger.error("The resource key (" + str(err) + ") was not present in the application's resource file.")
				break

			try:
				with open(resourceFile) as f:
					resources = f.read().splitlines()
			except IOError as err:
				errors = True
				logger.error("Unable to open the " + component + "'s resource file (" + resourceFile + ") for reading.\n" + str(err))
				break

			if not errors:
				componentResourceKey = re.sub('\s+', '', component) + 'Resources'
				componentResourceDict[componentResourceKey] = resources

		logger.info("Done getting component resource data for " + ', '.join(componentList) + ".")

		return [errors, componentResourceDict]

	#End __getComponentResources(self, componentList):	


	'''
	This function does a basic check of an IP address.
	It is still up to the end user to provide a valid IP 
	for connection purposes.
	'''
	def __checkIP(self, ip):
		ipList = ip.split('.')

		if len(ipList) != 4:
			print "An invalid IP was provided, please try again."
			return False

		for number in ipList:
			try:
				number = int(number)
			except ValueError:
				print "An invalid IP was provided, please try again."
				return False

			if number < 0 or number > 255: 
				print "An invalid IP was provided, please try again."
				return False

		return True

	#End __checkIP(self, ip):

	
	'''
	This function gives the user a chance to to fix an issue and try again.  However, some issues
	may require the program to be restarted in order for the fix to be recognized.  An example 
	would be a resource missing from the main application resource file, since it is read in during
	program initialization.
	'''
	def __tryAgainQuery(self, component, errorMessages):
		tryAgain = False

		print "The following error(s) was encountered while checking the " + component + ":"

		for errorMessage in errorMessages:
			print "\t" + errorMessage


		while 1:
			response = raw_input("Do you want to fix the problem and try again [y|n]: ")
			response = response.strip().lower()

			if len(response) != 1:
				print "\tA valid response is y|n.  Please try again."
				continue

			if not re.match('y|n', response):
				print "\tA valid response is y|n.  Please try again."
				continue

			if response == 'y':
				tryAgain = True						

			break

		return tryAgain

	#End __tryAgainQuery(self, component, error):


	def __confirmInput(self, component, ip, **kwargs):
		validInput = False

		print "The following information was provided for the component to be updated:"
		print "\t" + component + "IP: " + ip

		if 'username' in kwargs:
			print "\t" + component + "user name: " + kwargs['username']

		if 'localhostIP' in kwargs:
			print "\tlocal host managememt IP: " + kwargs['localhostIP']

		if 'scpUsername' in kwargs:
			print "\tlocal host scp user name: " + kwargs['scpUsername']

		while 1:
			response = raw_input("Is the above information correct [y|n]: ")
			response = response.strip().lower()

			if len(response) != 1:
				print "\tA valid response is y|n.  Please try again."
				continue

			if not re.match('y|n', response):
				print "\tA valid response is y|n.  Please try again."
				continue
			else:
				break

		if response == 'y':
			validInput = True						

		return validInput
		
	#End __confirmInput(self, component, ip, username):
