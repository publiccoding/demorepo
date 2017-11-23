import subprocess
import logging
import datetime
import shutil
import re



'''
This class is used to modify permissions on certain system files.
Permissions will be set using /etc/permissions.secure and
/etc/permissions.local.
'''
class ConfigureSystemFiles:
        def __init__(self, loggerName):
                self.logger = logging.getLogger(loggerName)
        #End __init__(self):


	'''
	This method will update system files using /etc/permissions.secure and /etc/permissions.local
	as the input source.
	'''
	def updatePermissions(self, permissionsResourceFile, logBaseDir):
		permissionsLocalFile = '/etc/permissions.local'
		permissionsSecureFile = '/etc/permissions.secure'
		permissionsResourceDict = {}

		self.logger.info("Updating permissions on system files identified by /etc/permissions.secure and /etc/permissions.local.")

		#Get the contents of the permissions resource file.
		try:
			f = open(permissionsResourceFile, 'r')
			permissionsResourceData = f.readlines()
			f.close()
		except IOError as err:
			self.logger.error("Unable to access the permissions resource file (" + permissionsResourceFile + ").\n" + str(err))
			return False

		#Save the permissions resource file data to a dictionary for future reference.
		for line in permissionsResourceData:
			#Skip commented and blank lines.
			if re.match('#', line) or re.match('\s*$', line):
				continue

			line = line.strip()
			key, value = line.split('|')

			permissionsResourceDict[key] = value

                #Use date to create a time specific backup of the permissions.local file.
                dateTimestamp = (datetime.datetime.now()).strftime('%Y%m%d%H%M%S')

		#Check current settings of permissions.secure and permissions.local and adjust as necessary.
		if not self.__adjustDuplicatePermissions(permissionsLocalFile, permissionsResourceDict, dateTimestamp):
			return False

		if not self.__adjustDuplicatePermissions(permissionsSecureFile, permissionsResourceDict, dateTimestamp):
			return False

		#Update permissions.local with the settings in the permissions resource dictionary.
		try:
			f = open(permissionsLocalFile, 'a')

			for file in permissionsResourceDict:
				f.write(file + '\t' + permissionsResourceDict[file] + '\n')

			f.close()
		except IOError as err:
			self.logger.error("Unable to open the permissions file (" + permissionsLocalFile + ") to append additional settings.\n" + str(err))
			return False

		#Before updating permissions save out what the system currently sees as being out of compliance.
		secureWarningsResult, permissionsSecureFileWarnings = self.__getPermissionsWarnings(permissionsSecureFile)
		localWarningsResult, permissionsLocalFileWarnings = self.__getPermissionsWarnings(permissionsLocalFile)

		if not secureWarningsResult or not localWarningsResult:
			return False

		try:
			with open(logBaseDir + 'permissionsWarningLog.log', 'w') as f:
				permissionsSecureWarnings = '*********************** Warnings from ' + permissionsSecureFile + ' are shown below. ***********************\n'
				permissionsLocalWarnings = '*********************** Warnings from ' + permissionsLocalFile + ' are shown below. ***********************\n'
				f.write(permissionsSecureWarnings + permissionsSecureFileWarnings + '\n\n' + permissionsLocalWarnings + permissionsLocalFileWarnings)
		except IOError as err:
			self.logger.error("Unable to write the permissions warning log file (" + logBaseDir + "permissionsWarningLog.log).\n" + str(err))
			return False

		#Set the system file permissions using permissions.secure and the updated permissions.local.
		if not self.__setPermissions(permissionsSecureFile):
			return False

		if not self.__setPermissions(permissionsLocalFile):
			return False

		#Check to make sure the files were updated as expected.
		if not self.__checkPermissions(permissionsSecureFile):
			return False

		if not self.__checkPermissions(permissionsLocalFile):
			return False

		self.logger.info("Done updating permissions on system files identified by /etc/permissions.secure and /etc/permissions.local.")

		return True	

	#End updatePermissions(self, permissionsResourceFile, logBaseDir):


	'''
	This function is used to check for duplicate entries in the permissions files before the update takes place.
	'''
	def __adjustDuplicatePermissions(self, permissionsFile, permissionsResourceDict, dateTimestamp):
                #Make a backup of the current permissions file.
                try:
                        shutil.copy2(permissionsFile, permissionsFile + '.' + dateTimestamp)
                except IOError as err:
                        self.logger.error("Unable to make a backup of the system's " + permissionsFile + " file.\n" + str(err))
                        return False

                #Get a list of the uncommented settings in permissions file.
                command = 'egrep -v "\s*#" ' + permissionsFile

                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()

                self.logger.debug("The output of the command (" + command + ") used to get the uncommented settings in " + permissionsFile + " was: " + out.strip())

                if err != '': #egrep will not have a return code of 0 if there are no uncommented lines.
                        self.logger.error("Problems were encountered while getting the uncommented settings in " + permissionsFile + " .\n" + err)
                        return False

                out = out.strip()

                '''
                If a file permissions setting is already in permissions.local then we will not add that
                file from the permissions resource file, since this could potentially override a customer's configuration.
		Additionally, if a file permissions setting is already in permissions.secure then we will comment out the entry
		in permissions.secure.
                '''
                if len(out) != 0:
                        fileList = out.split('\n')

                        for file in fileList:
                                if len(file) == 0:
                                        continue

                                fileDataList = file.split()

                                currentFile = fileDataList[0].strip()

                                if currentFile in permissionsResourceDict:
					if 'local' in permissionsFile:
                                        	del permissionsResourceDict[currentFile]
					else:
						file = re.sub('/', '\\/', file)
                                		command = "sed -i '0,/" + file + "/s//#" + file + "/' " + permissionsFile

						result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
						out, err = result.communicate()

						self.logger.debug("The output of the command (" + command + ") used to update the permissions file (" + permissionsFile + ") was: " + out.strip())

						if result.returncode != 0:
							self.logger.error("Problems were encountered while updating the permissions file (" + permissionsFile + ").\n" + err)
							return False

		return True

	#End __adjustDuplicatePermissions(self, permissionsFile, permissionsResourceDict, dateTimestamp):


	'''
	This method is used to get the current warnings before an update.
	'''
	def __getPermissionsWarnings(self, permissionsFile):
		command = 'chkstat --warn ' + permissionsFile

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to check the system's current compliance with " + permissionsFile + " was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Problems were encountered while checking the system's current compliance with " + permissionsFile + " .\n" + err)
			return False, ''

		return True, out

	#End __getPermissionsWarnings(self, permissionsFile):


	'''
	This method is used to set the permissions of the designated system files.
	'''
	def __setPermissions(self, permissionsFile):
		command = 'chkstat --set ' + permissionsFile

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to set system file permissions using " + permissionsFile + " was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Problems were encountered while setting system file permissions using " + permissionsFile + ".\n" + err)
			return False

		return True

	#End __setPermissions(self, permissionsFile):


	'''
	This method is used to check if permissions were successfully set.
	'''
	def __checkPermissions(self, permissionsFile):
		command = 'chkstat --warn ' + permissionsFile

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to check the system's post update compliance with " + permissionsFile + " was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Problems were encountered while checking the system's post update compliance with " + permissionsFile + ".\n" + err)
			return False

		if re.search('wrong', out, re.MULTILINE|re.DOTALL|re.IGNORECASE) != None:
			self.logger.error("The system's post update compliance appears to have failed in reference to the " + permissionsFile + " file.")
			return False
				
		return True

	#End __checkPermissions(self, permissionsFile):

#End ConfigureSystemFiles:
