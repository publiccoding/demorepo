#!/usr/bin/python


import pexpect
import re
import logging
from csurUpdateUtils import (InvalidPasswordError)


'''
This class is used for updating network switches.  
'''
class NetworkSwitch:
	'''
	The constructor sets up instance variables and initiates logging.
	'''	
	def __init__(self, ip, username, password, logBaseDir, logLevel):
		#Instance variables.
		self.ip = ip
		self.loggerName = ip + 'Logger'
		self.username = username
		self.password = password
		self.softwareImage = None
		self.switchSlotsToUpgrade = []

                #Configure logging
		switchLog = logBaseDir + 'networkSwitch_' + ip + '.log'
                handler = logging.FileHandler(switchLog)

                logger = logging.getLogger(self.loggerName)

		if logLevel == 'debug':
			logger.setLevel(logging.DEBUG)
		else:
			logger.setLevel(logging.INFO)

                formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
                handler.setFormatter(formatter)
                logger.addHandler(handler)

	#End __init__(self, ip, username, password, generation, logBaseDir, logLevel):

	'''
	This function is used to check that the switch model is supported. This is accomplished by the ability to
	get its resources from the switch resource file. Additionally, connectivity to the switch is verified as 
	well as checking to see if the switch needs to be updated and that there is enough available space if an
	update is needed. Lastly the switch is configured to act as an ftp server if it is not already configured
	so that its update image can be uploaded to the switch.
	A result dictionary is returned which indicates if an update is needed and any error messages encountered
	during initialization.
	'''
	def checkSwitch(self, generation, networkSwitchResources):
		if generation == 'Gen1.2' or generation == 'Haswell' or generation == 'Broadwell':
			switchType = '3Com'
		else:
			switchType = 'ProCurve'

		resultDict = {'updateNeeded' : False, 'errorMessages' : []}
		threeComPrompt = re.compile('<[a-zA-Z0-9-]+>')

		#This list is reset in case this method is called again when a retry is chosen.
		self.switchSlotsToUpgrade = []

                logger = logging.getLogger(self.loggerName)

		logger.info("Checking the switch's connnectivity, model, software version, and setting up its ftp server if necessary.")

		cmd = 'ssh -o PubkeyAuthentication=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + self.username + '@' + self.ip

		if switchType == '3Com':
			try:
				#We give 60 seconds to establish the connection.
				child = pexpect.spawn(cmd, timeout=60)

				#Don't think autologin is configured, but just in case we account for it.
				i = child.expect(['(?i)password:\s*', threeComPrompt])

				if i == 0:
					child.sendline(self.password)

					i = child.expect(['(?i)password:\s*', threeComPrompt])
					
					if i == 0:
						logger.error("An invalid password was provided for user " + self.username + ".")
						resultDict['errorMessages'].append('An invalid password was provided.')
						raise InvalidPasswordError("An invalid password was provided for user " + self.username + ".")

				#Need to turn off paging so that we can get all the output at once.
				child.sendline('screen-length disable')
				child.expect(threeComPrompt)

				cmd = 'display device verbose | include "^Slot[ ]+[0-9]{1,}|^Type|^Software Ver"'
				child.sendline(cmd)
				child.expect(threeComPrompt)
				deviceInformation = child.before

				logger.debug("The output of the command (" + cmd + ") used to check the switch's slot, model, and software version was: " + deviceInformation)

				'''
				This returns a list of tuples with the order being: slot, model, software version.
				'''
				switchTupleList = re.findall('Slot\s+(\d+)\s+info:|Type\s+:\s+([A-Z0-9- ]+)|Software Ver\s+:\s+([0-9A-Z]+)', deviceInformation)
				logger.debug("The switch tuple list was determined to be: " + str(switchTupleList) + ".")

				if len(switchTupleList) != 6:
					logger.error("The network switch's (" + self.ip + ") slot, model, and software version could not be determined:\n" + deviceInformation)
					resultDict['errorMessages'].append("The network switch's slot, model, and software version could not be determined.")
					logger.info("Done checking the switch's connnectivity, model, software version, and setting up its ftp server if necessary.")
					return resultDict

				#Remove the empty strings from the tuples.
				switchList = [filter(None, i) for i in switchTupleList]

				logger.debug("The switch device list was determined to be: " + str(switchList) + ".")

				switchModel = switchList[1][0]
				switchResourceList = self.__getSwitchResources(switchModel, networkSwitchResources[:])

				if switchResourceList[0]:
					errorsEncountered = True
					resultDict['errorMessages'].append("An error occurred while getting the switch's resources.")
					logger.info("Done checking the switch's connnectivity, model, software version, and setting up its ftp server if necessary.")
					return resultDict

				switchResourceDict = switchResourceList[1]

				try: 
					self.softwareImage = switchResourceDict['softwareImage']
					csurSoftwareVersion = switchResourceDict['softwareVersion']
					softwareImageSize =  switchResourceDict['softwareImageSize']
				except KeyError as err:
					resultDict['errorMessages'].append("A resource key error was encountered.")
					logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
					logger.info("Done checking the switch's connnectivity, model, software version, and setting up its ftp server if necessary.")
					return resultDict

				count = 0
				
				for i in range(0,2):
					availableSpace = None
					switchSlot = switchList[i+count][0]
					count += 2
					installedSoftwareVersion = switchList[i+count][0]
					
					if installedSoftwareVersion != csurSoftwareVersion:
						#Save a reference to which slot is not up to date.
						self.switchSlotsToUpgrade.append(switchSlot)
						
						if not resultDict['updateNeeded']:
							resultDict['updateNeeded'] = True

						#Check available space for the update.	
						cmd = 'dir slot' + switchSlot + '#flash:/ | include "KB[ ]+free)$"'
						child.sendline(cmd)
						child.expect(threeComPrompt)
						spaceInformation = child.before
						
						logger.debug("The output of the command (" + cmd + ") used to check the switch's available space was: " + spaceInformation)

						spaceInformationList = spaceInformation.splitlines()

						for line in spaceInformationList:
							if re.match('.*\((\d+)\s+KB\s+free', line) != None:
								availableSpace = re.match('.*\((\d+)\s+KB\s+free', line).group(1)
								logger.debug("The switch's available space in slot " + switchSlot + " was determined to be: " + availableSpace + " KB.")

						if availableSpace != None:
							if int(availableSpace) < switchResourceDict['softwareImageSize']:
								logger.error("The switch's available space in slot " + switchSlot + " was determined to be: " + availableSpace + " KB.")
								resultDict['errorMessages'].append('There is insufficient space on the switch for the update.')
								logger.info("Done checking the switch's connnectivity, model, software version, and setting up its ftp server if necessary.")
								return resultDict
						else:
							logger.error("The switch's available space could not be determined: " + spaceInformation)
							resultDict['errorMessages'].append("The switch's available space could not be determined")
							logger.info("Done checking the switch's connnectivity, model, software version, and setting up its ftp server if necessary.")
							return resultDict
				
				#Check and enable the switch as an ftp server if an update is needed.
				if len(self.switchSlotsToUpgrade) > 0:
					child.sendline('display ftp-server')
					child.expect(threeComPrompt)
				
					ftpServerInformation = child.before

					if 'FTP server is running' not in ftpServerInformation:
						systemViewPrompt = re.compile('\[[a-zA-Z0-9-]+\]')
						
						child.sendline('system-view')
						child.expect(systemViewPrompt)
						
						child.sendline('ftp server enable')
						child.expect(systemViewPrompt)

						child.sendline('display ftp-server')
						child.expect(systemViewPrompt)
					
						ftpServerInformation = child.before
						
						#Exit system-view mode.
						child.sendline('quit')

						if 'FTP server is running' not in ftpServerInformation:
							resultDict['errorMessages'].append("The switch's ftp server could not be enabled.")
					
				child.sendline('quit')
			except (pexpect.TIMEOUT, pexpect.EOF, pexpect.ExceptionPexpect) as e:
				resultDict['errorMessages'].append('The session with the switch was aborted.')
				logger.error("Problems were encountered while checking the switch; session aborted: " + str(e))
			except InvalidPasswordError as e:
				logger.error(e.message)

		logger.info("Done checking the switch's connnectivity, model, software version, and setting up its ftp server if necessary.")

		return resultDict

        def __getSwitchResources(self, switchModel, networkSwitchResources):
		errorsEncountered = False
                started = False
		switchResourceDict = {}

                logger = logging.getLogger(self.loggerName)

                logger.info("Getting the resources for switch model '" + switchModel + "'.")

                for data in networkSwitchResources:
                        data = data.strip()

                        if not re.match(switchModel, data) and not started:
                                continue
                        elif re.match(switchModel, data):
                                started = True
                                continue
                        elif re.match(r'\s*$', data):
                                break
                        else:
                                resourceList = [x.strip() for x in data.split('=')]

				try:
                                	switchResourceDict[resourceList[0]] = resourceList[1]
				except IndexError as err:
					errorsEncountered = True
					logger.error("An index out of range error occured for switch resource list: " + resourceList)
		
		#If this is true, then the switch's model was missing or incorrectly entered into the network switch resource file.
		if not started:
			errorsEncountered = True
			logger.error("The switch's model (" + switchModel + ") was not found in the network switch resource file.")

                logger.info("Done getting the resources for switch model '" + switchModel + "'.")

		return [errorsEncountered, switchResourceDict]

        #End __getSwitchResources(self, switchModel, networkSwitchResources):


#This section is for running the module standalone for debugging purposes.
if __name__ == '__main__':
        ip = '10.41.0.9'
        username = 'admin'      #manager for ProCurve or Admin/admin for 3Com.
        password = 'HP1nv3nt'
        switchType = '3Com'
	switchSoftwareVersion = '2422P01'
	model = 'FF 5930-4Slot Switch'

	#***This will become a resource.***
	imageSize = 100000

	networkSwitch = NetworkSwitch(ip, username, password)

	resultDict = networkSwitch.checkSwitch(switchType, model, switchSoftwareVersion, imageSize)
	print resultDict
