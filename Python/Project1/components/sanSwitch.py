import pexpect
import re
import os
import shutil
import time
import pwd
import logging
import subprocess
from csurUpdateUtils import (CouldNotDetermineError, InvalidPasswordError, FileUploadError)


'''
This class is used for updating SAN switches.  
'''
class SANSwitch:
        '''
        The constructor sets up instance variables and initiates logging.
        '''
	def __init__(self, ip, sanSwitchLogDir, logLevel, **kwargs):
                #Instance variables.
                self.ip = ip
                self.password = None
	
		if 'localhostMgmtIP' in kwargs:
			self.localhostMgmtIP = kwargs['localhostMgmtIP']

		if 'scpUsername' in kwargs:
			self.scpUsername = kwargs['scpUsername']

		if 'scpPassword' in kwargs:
			self.scpPassword = kwargs['scpPassword']

		self.sanSwitchLogDir = sanSwitchLogDir
                self.loggerName = ip + 'Logger'
                self.upgradeStatus = None
                self.child = None

		#This holds the directory list of images used to upgrade a switch.
		self.imageDirList = []
		
                #Configure logging
                switchLog = self.sanSwitchLogDir + 'sanSwitch_' + ip + '.log'
                handler = logging.FileHandler(switchLog)

                self.logger = logging.getLogger(self.loggerName)

                if logLevel == 'debug':
                        self.logger.setLevel(logging.DEBUG)
                else:
                        self.logger.setLevel(logging.INFO)

                formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)

                #This gets the version information log file logger.
                self.versionInformationLogger = logging.getLogger('versionInformationLog')

	#End __init__(self, ip, localhostMgmtIP, scpUsername, scpPassword, sanSwitchLogDir, logLevel):


	'''
	This function is used to check connectivity to the switch as well as checking 
	to see if the switch needs to be upgraded.
	Also, SAN switches cannot go through a direct upgrade in some cases.  Thus, multiple upgrades
	may be required.
	Finally, the kwargs are expected to be password only.
	'''
	def initializeSwitch(self, sanSwitchResources, versionInformationLogOnly, csurBasePath, **kwargs):
                if versionInformationLogOnly:
                        self.logger.info("Getting the switch's version report.")
                else:
                        self.logger.info("Initializing the switch for an upgrade.")

		resultDict = {'upgradeNeeded' : False, 'errorMessages' : [], 'imageDirList' : []}
		prompt = re.compile('.*:admin>\s*')

		#This is the expected header from the firmwareshow command.
		firmwareHeaderRegex = 'Appl\s+Primary/Secondary\s+Versions'

		if len(kwargs) != 0:
                        self.password = kwargs['password']
                else:
			self.password = 'HP1nv3nt'

		#SAN switch models need to be dereferenced to their name for readability purposes.
		for line in sanSwitchResources:
			if 'sanSwitchCrossReference' in line:
				sanSwitchCrossReferenceList = line.split('=')
				sanSwitchCrossReference = sanSwitchCrossReferenceList[1]
				sanSwitchCrossReference = re.sub('[\'"]', '', sanSwitchCrossReference).strip()

		sanSwitchCrossReferenceDict = dict(x.split(':') for x in re.sub('\s+:\s+', ':', re.sub(',\s*', ',', sanSwitchCrossReference)).split(','))

		self.logger.debug("The SAN switch cross reference dictionary was determined to be: " + str(sanSwitchCrossReferenceDict))

		#Password authentication is forced.
		cmd = 'ssh -o PasswordAuthentication=yes -o PubkeyAuthentication=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + 'admin@' + self.ip

		try:
			#We give 60 seconds to establish the connection.
			child = pexpect.spawn(cmd, timeout=60)

			child.expect('(?i)password:\s*')

			child.sendline(self.password)

			i = child.expect(['(?i)password:\s*', 'Please change passwords', prompt])
			
			if i == 0:
				raise InvalidPasswordError("An invalid password was provided for admin.") 
			elif i == 1:
				#We are not going to set passwords on the switch if it has not already been done.
				child.sendcontrol('c')
				child.expect(prompt)

			#Get the switch's name.
			child.sendline('switchname')
			child.expect(prompt)
			switchName = child.before
			
			self.logger.debug("The output of the command (switchname) used to get the switch's name was: " + switchName)

			try:
                        	switchName =  re.match('.*switchname\s*([0-9a-zA-Z-]*)', switchName, re.DOTALL|re.MULTILINE|re.IGNORECASE).group(1)
			except AttributeError as err:
				resultDict['errorMessages'].append("Could not determine the switch's name.")
				self.logger.error("Could not determine the switch's name: " + str(err))
				child.terminate(force=True)
				return resultDict

                        self.logger.debug("The switch's name was determined to be: " + switchName)

			#Get firmware information.
			child.sendline('firmwareshow')
			child.expect(prompt)
			firmwareInformation = child.before

			self.logger.debug("The output of the command (firmwareshow) used to check the switch's firmware version was: " + firmwareInformation)

			#Get switch type.
			child.sendline('switchshow')
			child.expect(prompt)
			switchInformation = child.before

			self.logger.debug("The output of the command (switchshow) used to check the switch's type was: " + switchInformation)

			'''
			Checking the switch's firmware version.
			'''
			try:
				installedFirmwareVersion = re.search('(v(\d\.){2}\d[a-z]{1})', firmwareInformation).group(1)
				self.logger.debug("The switch's current firmware version was determined to be: " + installedFirmwareVersion + ".")
			except AttributeError:
				resultDict['errorMessages'].append("Could not determine the switch's firmware version.")
				self.logger.error("Could not determine the switch's firmware version: " + firmwareInformation)
				child.sendline('exit')
				return resultDict

			try:
				switchType = re.search('switchType:\s+(\d+)\.\d+', switchInformation).group(1)

				try:
					switchModel = sanSwitchCrossReferenceDict[switchType]
					self.logger.debug("The switch's model was determined to be: " + switchModel + ".")
				except KeyError as err:
					resultDict['errorMessages'].append("A resource key error was encountered.")
					self.logger.error("The resource key (" + str(err) + ") was not present in the application's resource file.")
					return resultDict
			except AttributeError as err:
				resultDict['errorMessages'].append("Could not determine the switch's type.")
				self.logger.error("Could not determine the switch's type: " + str(err))
				child.sendline('exit')
				return resultDict

			switchResourceList = self.__getSwitchResources(switchModel, sanSwitchResources[:])

			if switchResourceList[0]:
				resultDict['errorMessages'].append("An error occurred while getting the switch's resources.")
				child.sendline('exit')
				return resultDict

			switchResourceDict = switchResourceList[1]

			try:
				csurFirmwareVersion = switchResourceDict['currentFirmwareVersion']

				if not versionInformationLogOnly:
					if installedFirmwareVersion != csurFirmwareVersion:
						#Change the installed firmware version name to a generic name, e.g. v.7.2.1d would become v.7.2.x.
						installedFirmwareVersion = re.sub('\d[a-z]$', 'x', installedFirmwareVersion)

						firstSupportedDirectMigrationVersions = switchResourceDict['firstSupportedDirectMigrationVersions']
						secondSupportedDirectMigrationVersions = switchResourceDict['secondSupportedDirectMigrationVersions']

						#If the switch's current firmware version is not at a supported version for upgrading then return an error.  Otherwise, proceeed.
						if not installedFirmwareVersion in firstSupportedDirectMigrationVersions and not installedFirmwareVersion in secondSupportedDirectMigrationVersions:
							resultDict['errorMessages'].append("The SAN switch is not at a supported firmware version for an automated update.")
							self.logger.error("The SAN switch is not at a supported firmware version for an automated update.")
							child.sendline('exit')
							return resultDict
						elif not installedFirmwareVersion in firstSupportedDirectMigrationVersions:
							#This means multiple updates are needed.
							firmwareImageList = [switchResourceDict['firstFirmwareImage'], switchResourceDict['secondFirmwareImage']]
						else:
							firmwareImageList = [switchResourceDict['firstFirmwareImage']]
						
						for image in firmwareImageList:
							firmwareImage = csurBasePath + '/firmware/sanSwitch/' + image
							#Change into /tmp.
							try:
								os.chdir('/tmp')
							except (OSError, IOError), err:
								resultDict['errorMessages'].append("There was a problem copying the SAN switch's firmware file.")
								self.logger.error("There was a problem copying the SAN switch's firmware file to /tmp:" + "\n" + str(err))
								child.sendline('exit')
								return resultDict

							#Get the firmware images top directory, which will be used during the upgrade as well as after the upgrade to cleanup.
							cmd = "tar --exclude=*/* -tf " + firmwareImage
							result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
							out, err = result.communicate()

							firmwareImageTopDir = out.strip()

							self.logger.debug("The output of the command (" + cmd + ") used to get the firmware image's top directory was: " + firmwareImageTopDir)

							if result.returncode != 0:
								resultDict['errorMessages'].append("Failed to get the firmware image's top directory.")
								self.logger.error("Failed to get the firmware image's top directory:\n" + err)
								child.sendline('exit')
								return resultDict
							else:
								self.imageDirList.append('/tmp/' + firmwareImageTopDir)

							'''
							Only add the image directory reference to the resultDict imageDirList if it does not already exist.
							Also, extract the image, since it has yet to be extracted.
							'''
							if not os.path.isdir(self.imageDirList[-1]):
								resultDict['imageDirList'].append('/tmp/' + firmwareImageTopDir)

								cmd = "tar -zxf " + firmwareImage
								result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
								out, err = result.communicate()

								if result.returncode != 0:
									resultDict['errorMessages'].append("Failed to extract the firmware image.")
									self.logger.error("Failed to extract the firmware image:\n" + err)
									child.sendline('exit')
									return resultDict
						
						resultDict['upgradeNeeded'] = True
					else:
						child.sendline('exit')
						self.__logVersionInformation(switchModel, installedFirmwareVersion, csurFirmwareVersion)
						self.logger.info("Done initializing for a SAN switch upgrade; an upgrade was not needed.")
						return resultDict
				else:
					child.sendline('exit')
					self.__logVersionInformation(switchModel, installedFirmwareVersion, csurFirmwareVersion)
                        		self.logger.info("Done getting the switch's version report.")
					return resultDict
			except KeyError as err:
				resultDict['errorMessages'].append("A resource key error was encountered.")
				self.logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
				child.sendline('exit')
				return resultDict
	                except CouldNotDetermineError as err:
				self.logger.error(err.message)
				resultDict['errorMessages'].append(err.message)
				child.sendline('exit')
				return resultDict

			#Set keys, since an upgrade is required.  First delete any private keys so we start fresh.
			child.sendline('sshutil delprivkey')
			child.expect(prompt)
			child.sendline('sshutil genkey')
			child.expect('Enter passphrase.*:\s*')
			child.sendline('')
			child.expect('Enter same passphrase again:\s*')
			child.sendline('')
			child.expect(prompt)
			
			#Check for successfull build of new key.
			keyGenerationResult = child.before

			if 'generated successfully' not in keyGenerationResult:
				resultDict['errorMessages'].append('Problems were encountered while generating a new key pair.')
				self.logger.error("Problems were encountered while generating a new key pair: " + keyGenerationResult)
				child.sendline('exit')
				return resultDict

			child.sendline('sshutil exportpubkey')
			child.expect('Enter IP address:\s*')
			child.sendline(self.localhostMgmtIP)
			child.expect('Enter remote directory:\s*')
			child.sendline('/tmp')
			child.expect('Enter login name:\s*')
			child.sendline(self.scpUsername)
			child.expect('(?i)password:\s*')
			child.sendline(self.scpPassword)
			child.expect(prompt)
			
			#Check for successfull export of public key.
			keyExportResult = child.before

			if 'is exported successfully' not in keyExportResult:
				resultDict['errorMessages'].append("There was a problem exporting the SAN switch's public key.")
				self.logger.error("There was a problem exporting the SAN switch's public key to this system (" + self.localhostMgmtIP + ").")
				child.sendline('exit')
				return resultDict
			else:
				try:
					switchPublicKey = re.match('.*Exported public key\s*(.*\.pub)', keyExportResult).group(1) 
					self.logger.debug("The switch's public key was determined to be: " + switchPublicKey + ".")

					scpUserHomeDir = pwd.getpwnam(self.scpUsername).pw_dir
				except AttributeError as err:
					resultDict['errorMessages'].append("Could not determine the switch's public key.")
					self.logger.error("Could not determine the switch's public key: " + keyExportResult + '\n' + str(err))
					return resultDict

			if not self.__updateAuthorizedKeys(switchName, scpUserHomeDir, switchPublicKey):
				resultDict['errorMessages'].append("An error occurred while updating" + self.scpUserame + "'s authorized_keys file.")
				child.sendline('exit')
				return resultDict

			#Save a backup of the switches configuration.
			configurationFileName = 'sanSwitch_' + self.ip + '_ConfigurationFile.txt'
			configurationFile = '/tmp/' + configurationFileName

			child.sendline('configupload')
			child.expect('Protocol.*:\s*')
			child.sendline('scp')
			child.expect('Server Name or IP Address.*:\s*')
			child.sendline(self.localhostMgmtIP)
			child.expect('User Name.*:\s*')
			child.sendline(self.scpUsername)
			child.expect('Path/Filename.*:\s*')
			child.sendline(configurationFile)
			child.expect('Section.*:\s*')
			child.sendline(' ')
			child.expect(prompt)

			configurationFileUploadResult = child.before

			if not 'All selected config parameters are uploaded' in configurationFileUploadResult:
				child.sendline('exit')
				raise FileUploadError("The SAN switch's configuration file failed to successfully upload to the local server.") 

			child.sendline('exit')

			#Move the SAN switch's configuration file to the log directory.
			try:
				destination = self.sanSwitchLogDir + configurationFileName
				shutil.move(configurationFile, destination)
			except (OSError, IOError, Error), err:
				resultDict['errorMessages'].append("There was a problem moving the SAN switch's configuration file.")
				self.logger.error("There was a problem moving the SAN switch's configuration file to " + destination + ":\n" + str(err))

		except (pexpect.TIMEOUT, pexpect.EOF, pexpect.ExceptionPexpect) as err:
			resultDict['errorMessages'].append('The session with the switch was aborted.')
			self.logger.error("Problems were encountered while checking the switch; session aborted: " + str(err))
			return resultDict
		except InvalidPasswordError as err:
			resultDict['errorMessages'].append(err.message)
			self.logger.error(err.message)
			child.terminate(force=True)
			return resultDict
		except FileUploadError as err:
			resultDict['errorMessages'].append(err.message)
			self.logger.error(err.message)
			return resultDict

        	self.__logVersionInformation(switchModel, installedFirmwareVersion, csurFirmwareVersion)

                if versionInformationLogOnly:
                        self.logger.info("Done getting the switch's version report.")
                else:
                        self.logger.info("Done initializing the switch for an upgrade.")

		return resultDict

	#End initializeSwitch(self, sanSwitchResources, versionInformationLogOnly, **kwargs):


        '''
        This function does the actual upgrade of the switch.
        '''
        def upgradeSwitch(self):
		prompt = re.compile('.*:admin>\s*')

                self.logger.info("Upgrading the switch.")

		cmd = 'ssh -o PasswordAuthentication=yes -o PubkeyAuthentication=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + 'admin@' + self.ip

		for firmwareDir in self.imageDirList:
			try:
				#We give 60 seconds to establish the connection.
				self.child = pexpect.spawn(cmd, timeout=60)

				self.child.expect('(?i)password:\s*')

				self.child.sendline(self.password)

				i = self.child.expect(['Please change passwords', prompt])

				if i == 0:
					self.child.sendcontrol('c')
					self.child.expect(prompt)

				self.child.sendline('firmwaredownload')
				self.child.expect('IP Address:\s*')
				self.child.sendline(self.localhostMgmtIP)
				self.child.expect('User Name:\s*')
				self.child.sendline(self.scpUsername)
				self.child.expect('File Name:\s*')
				self.child.sendline(firmwareDir)
				self.child.expect('Network Protocol.*:\s*')
				self.child.sendline('3')
				i = self.child.expect(['Do you want to continue.*:\s*','(?i)failed'], timeout=240)

				if i == 0:
					self.child.sendline('y')
					'''
					Documentation says it can take up to 30 minutes to download the software, so we give 45 minutes.
					Thus, building in a 15 minute buffer.
					'''
					self.logger.info("Waiting for the upgrade to terminate the original session with the switch, which can take up to 45 minutes.")
					self.child.expect(pexpect.EOF, timeout=2700)
					self.logger.degug("The output of the switch before the session was terminated was:" + self.child.before())
					self.child.close()
					self.logger.info("The upgrade terminated the original session with the switch.")

					if not self.__monitorUpgradeStatus():
						self.upgradeStatus = 'Failed'
						break
				else:
					self.upgradeStatus = 'Failed'
					self.logger.error("Problems were encountered while updating the switch: " + self.child.before)
					break
			except (pexpect.TIMEOUT, pexpect.EOF, pexpect.ExceptionPexpect) as err:
				self.upgradeStatus = 'Failed'
				self.logger.error("Problems were encountered while updating the switch; session aborted: " + str(err))

                if self.upgradeStatus == None:
                        self.upgradeStatus = 'Succeeded'

                self.logger.info("Done upgrading the switch.")

        #End upgradeSwitch(self):


        '''
        This function is used to get the switches CSUR resources from
        the SAN switch resource file.
        '''
        def __getSwitchResources(self, switchModel, sanSwitchResources):
                errorsEncountered = False
                started = False
                switchResourceDict = {}


                self.logger.info("Getting the resources for switch model '" + switchModel + "'.")

                for data in sanSwitchResources:
                        data = data.strip()

                        if not re.match(switchModel, data) and not started:
                                continue
                        elif re.match(switchModel, data):
                                started = True
                                continue
                        elif re.match('\s*$', data):
                                break
			elif re.match('#', data):
				continue
                        else:
                                resourceList = [x.strip(" '\"") for x in data.split('=')]

                                try:
                                        switchResourceDict[resourceList[0]] = resourceList[1]
                                except IndexError as err:
                                        errorsEncountered = True
                                        self.logger.error("An index out of range error occured for switch resource list: " + str(resourceList) + '\n' + str(err))

                #If this is true, then the switch's model was missing or incorrectly entered into the SAN switch resource file.
                if not started:
                        errorsEncountered = True
                        self.logger.error("The switch's model (" + switchModel + ") was not found in the SAN switch resource file.")

                self.logger.info("Done getting the resources for switch model '" + switchModel + "'.")

                return [errorsEncountered, switchResourceDict]

        #End __getSwitchResources(self, switchModel, sanSwitchResources):


        '''
        This function logs the switch's version information.
        '''
        def __logVersionInformation(self, switchModel, installedFirmwareVersion, csurFirmwareVersion):
                self.versionInformationLogger.info('\n')
                self.versionInformationLogger.info('Firmware information for SAN switch at ' + self.ip + ':')
		componentHeader = 'Switch Model'
		componentUnderLine = '------------'

		csurVersionHeader = 'CSUR Version'
		csurVersionUnderLine = '------------'

		currentVersionHeader = 'Current Version'
		currentVersionUnderLine = '---------------'

		statusHeader = 'Status'
		statusUnderLine = '------'

		self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentHeader, csurVersionHeader, currentVersionHeader, statusHeader))
		self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentUnderLine, csurVersionUnderLine, currentVersionUnderLine, statusUnderLine))

                if installedFirmwareVersion != csurFirmwareVersion:
                	self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(switchModel, csurFirmwareVersion, installedFirmwareVersion, 'FAIL'))
                else:
                	self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(switchModel, csurFirmwareVersion, installedFirmwareVersion, 'PASS'))

        #End __logVersionInformation(self, switchModel, installedFirmwareVersion, csurFirmwareVersion):


	'''
	This function does two things.  First it confirms that the scp user that was provided is able to log into the server and
	secondly it ensures their .ssh directory is present and cleans up and updates their authorized_keys as necessary.
	'''
	def __updateAuthorizedKeys(self, switchName, scpUserHomeDir, switchPublicKey):
		scpUserAuthorizedKeysDir = scpUserHomeDir + '/.ssh'
		scpUserAuthorizedKeysFile = scpUserSSHDir + '/authorized_keys'

		cmd = 'ssh -o PasswordAuthentication=yes -o PubkeyAuthentication=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + self.scpUsername + '@' + self.localhostMgmtIP + " ls " +  scpUserAuthorizedKeysDir

		try:
			#We give 60 seconds to establish the connection.
			child = pexpect.spawn(cmd, timeout=60)

			child.expect('(?i)password:\s*')

			child.sendline(self.scpPassword)

			i = child.expect(['(?i)password:\s*', pexpect.EOF])

			if i == 0:
				raise InvalidPasswordError("An invalid password was provided for " + self.scpUsername + ".")
			elif i == 1:
				result = child.before

			child.close()
		except (pexpect.TIMEOUT, pexpect.EOF, pexpect.ExceptionPexpect) as err:
			self.logger.error("Problems were encountered while checking " + self.scpUsername + "'s .ssh directory; session aborted: " + str(err))
			return False
		except InvalidPasswordError as err:
			self.logger.error("Problems were encountered while checking " + self.scpUsername + "'s .ssh directory: " + err.message)
			return False

		if child.exitstatus != 0:
			if 'No such file or directory' in result:
				#Create the user's .ssh directory, since it appears to have not been present.
				cmd = 'ssh -o PasswordAuthentication=yes -o PubkeyAuthentication=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + self.scpUsername + '@' + self.localhostMgmtIP + " mkdir " +  scpUserAuthorizedKeysDir

				self.logger.debug("The command used to create " + self.scpUsername + "'s .ssh directory was: " + cmd)

				try:
					#We give 60 seconds to establish the connection.
					child = pexpect.spawn(cmd, timeout=60)

					child.expect('(?i)password:\s*')

					child.sendline(self.scpPassword)

					child.expect(pexpect.EOF)

					result = child.before

					child.close()
				except (pexpect.TIMEOUT, pexpect.EOF, pexpect.ExceptionPexpect) as err:
					self.logger.error("Problems were encountered while creating " + self.scpUsername + "'s .ssh directory; session aborted: " + str(err))
					return False

				if child.exitstatus != 0:
					self.logger.error("Problems were encountered while creating " +  self.scpUsername + "'s .ssh directory: " + result)
					return False
			else:
				self.logger.error("Problems were encountered while checking " + self.scpUsername + "'s .ssh directory: " + err.message)
				return False
		elif 'authorized_keys' in result:
			#Remove old switch keys from authorized_keys if they are present.
			cmd = 'ssh -o PasswordAuthentication=yes -o PubkeyAuthentication=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + self.scpUsername + '@' + self.localhostMgmtIP + " sed -ri \"'/^\s*ssh-rsa\s+.*==\s+.*" + switchName + "\s*$/d' " +  scpUserAuthorizedKeysFile + "\""

			self.logger.debug("The command used to cleanup " + self.scpUsername + "'s authorized_keys file was: " + cmd)

			try:
				#We give 60 seconds to establish the connection.
				child = pexpect.spawn(cmd, timeout=60)

				child.expect('(?i)password:\s*')

				child.sendline(self.scpPassword)

				child.expect(pexpect.EOF)

				result = child.before

				child.close()
			except (pexpect.TIMEOUT, pexpect.EOF, pexpect.ExceptionPexpect) as err:
				self.logger.error("Problems were encountered while cleaning up " + self.scpUsername + "'s authorized_keys file; session aborted: " + str(err))
				return False

			if child.exitstatus != 0:
				self.logger.error("Problems were encountered while cleaning up " + self.scpUsername + "'s authorized_keys file: " + result)
				return False

		cmd = 'ssh -o PasswordAuthentication=yes -o PubkeyAuthentication=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + self.scpUsername + '@' + self.localhostMgmtIP + ' cat /tmp/' + switchPublicKey + ' >> ' + scpUserAuthorizedKeysFile

		self.logger.debug("The command used to update " + self.scpUsername + "'s authorized_keys file with the switch's key was: " + cmd)

		try:
			#We give 60 seconds to establish the connection.
			child = pexpect.spawn(cmd, timeout=60)

			child.expect('(?i)password:\s*')

			child.sendline(self.scpPassword)

			child.expect(pexpect.EOF)

			result = child.before

			child.close()
		except (pexpect.TIMEOUT, pexpect.EOF, pexpect.ExceptionPexpect) as err:
			self.logger.error("Problems were encountered while updating " + self.scpUsername + "'s authorized_keys file with the switch's key; session aborted: " + str(err))
			return False

		if child.exitstatus != 0:
			self.logger.error("Problems were encountered while updating " +  self.scpUsername + "'s authorized_keys file with the switch's key: " + result)
			return False
		else:
			return True

	#End __updateAuthorizedKeys(self, switchName, scpUserHomeDir, switchPublicKey):


        '''
        This function is used to get the switch's IP address.
        '''
        def getIP(self):
                return self.ip
        #End getIP(self):


        '''
        This function is used to get the status of the switch upgrade,
        whether it failed or succedded.
        '''
        def getSwitchUpgradeStatus(self):
                return self.upgradeStatus
        #End getSwitchUpgradeStatus(self):


        '''
        This function is used to close/terminate the connection to the
        switch which in essence cancels the upgrade.
        It is only called if a user has requested so by Ctrl-C.
        '''
        def cancelUpgrade(self):
                self.logger.info("The switch's upgrade was cancelled.")
                self.child.terminate(force=True)
        #End cancelUpgrade(self):


	'''
	This function is used to monitor the switch's upgrade as the original 
	connection will be lost.
	'''
	def __monitorUpgradeStatus(self):
		upgradeStatus = False
		prompt = re.compile('.*:admin>\s*')

                self.logger.info("Monitoring the switch's upgrade status.")

		cmd = 'ssh -o PasswordAuthentication=yes -o PubkeyAuthentication=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + 'admin@' + self.ip

		#Wait for approximately 20 minutes for the upgrade to finish, which should be more than sufficient.
		count = 0

		while count < 5:
			try:
				#We give 60 seconds to establish the connection.
				self.child = pexpect.spawn(cmd, timeout=60)

				i = self.child.expect(['(?i)password:\s*', pexpect.TIMEOUT, pexpect.EOF])

				if i == 1:
                			self.logger.info("Switch connection attempt number " + count + " timed out. " + 5 - count + " more attempts will be made.")
					self.child.close()
					time.sleep(240)
					count += 1
					continue
				elif i == 2:
                			self.logger.info("Switch connection attempt number " + count + " failed. " + 5 - count + " more attempts will be made.")
					time.sleep(300)
					count += 1
					continue
				else:
					self.child.sendline(self.password)

				i = self.child.expect(['Please change passwords', prompt])
				
				if i == 0:
					self.child.sendcontrol('c')
					self.child.expect(prompt)

				self.child.sendline('firmwaredownstatus')
				self.child.expect(prompt)
				currentStatus = self.child.before()
				self.logger.debug("The output of firmwaredownstatus was determinted to be: " + currentStatus)
			
				if 'failed' in currentStatus.lower():
					self.logger.error("Problems were encountered while updating the switch; upgrade failed: " + currentStatus)
					self.child.sendline('exit')
					break
				elif 'firmwaredownload command has completed successfully' in currrentStatus.lower():
					self.child.sendline('exit')
					upgradeStatus = True
					break
				else:
                			self.logger.info("Switch connection attempt number " + count + " shows that the upgrade is still taking place. " + 5 - count + " more attempts will be made.")
					time.sleep(300)
					count += 1
					continue
			except (pexpect.TIMEOUT, pexpect.EOF, pexpect.ExceptionPexpect) as err:
				self.logger.error("Problems were encountered while updating the switch; session aborted: " + str(err))
				break

		self.logger.info("Done monitoring the switch's upgrade status.")

		return upgradeStatus

	#End __monitorUpgradeStatus(self):

#End class SANSwitch:
