import subprocess
import logging
import datetime
import shutil
import re
import os
import stat


'''
This class is used to set the system default umask to 077 and 
to update the /home directory permissions to 755 and user 
directories in /home to 700.
'''
class ConfigureUmaskHomeDir:
	def __init__(self, loggerName):
		self.logger = logging.getLogger(loggerName)
	#End __init__(self, loggerName):
	
	'''
	This method will disable the key sequence ctrl+alt+del, which is used to reboot a system.
	'''
	def updateUmask(self):
		self.logger.info("Updating the system's umask so that files and directories created by a user are only accessible to themself.")

		loginDefsFile = '/etc/login.defs'
		updateRequired = True
		commentedUmask = False
		unCommentedUmask = False

		#Use date to create a time specific backup of the login.defs file.
		dateTimestamp = (datetime.datetime.now()).strftime('%Y%m%d%H%M%S')

		#Make a backup of the current login.defs file.
		try:
			shutil.copy2(loginDefsFile, loginDefsFile + '.' + dateTimestamp)
		except IOError as err:
			self.logger.error("Unable to make a backup of the system's login.defs file.\n" + str(err))
			return False

		#Read login.defs into an array, so it can be parsed for UMASK.
		try:
			f = open(loginDefsFile, 'r')
			loginDefsConfigurationData = f.readlines()
			f.close()
		except IOError as err:
			self.logger.error("Unable to access the system's login.defs file.\n" + str(err))
			return False

		self.logger.debug("The login.defs file data was determined to be: " + str(loginDefsConfigurationData))
		
		for line in loginDefsConfigurationData:
			line = line.strip()

			if re.match('\s*UMASK\s+(\d{3})', line):
				unCommentedUmask = True
				
				try:
					umask = re.match('\s*UMASK\s+(\d{3})', line).group(1)
                                except AttributeError as err:
                                        self.logger.error("An AttributeError was encountered while getting the umask resource setting: " + str(err))
                                        return False

				if umask == '077':
					updateRequired = False
				break

			if re.match('\s*#\s*UMASK\s+(\d{3})', line):
				commentedUmask = True

		if updateRequired:
			if unCommentedUmask:
                                command = "sed -i '0,/^\s*UMASK.*$/s//UMASK 077/' " + loginDefsFile
			elif commentedUmask:
                                command = "sed -i '0,/^\s*#\s*UMASK.*$/s//UMASK 077/' " + loginDefsFile
                        else:
                                command = 'echo "UMASK 077" >> ' + loginDefsFile

                        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        out, err = result.communicate()

                        self.logger.debug("The output of the command (" + command + ") used to update the login.defs UMASK resource was: " + out.strip())

                        if result.returncode != 0:
                                self.logger.error("Problems were encountered while updating the system's UMASK resource in the " + loginDefsFile + " file.\n" + err)
                                return False
                        else: #Confirm update.
                                command = 'egrep "^\s*UMASK\s+077\s*" ' + loginDefsFile

                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()

                                self.logger.debug("The output of the command (" + command + ") used to check that the login.defs UMASK resource was updated successfully was: " + out.strip())

                                if result.returncode != 0:
                                        self.logger.error("Problems were encountered while updating the system's UMASK resource in the " + loginDefsFile + " file.\n" + err)
                                        return False
                else:
                        self.logger.info("The UMASK resource in the " + loginDefsFile + " file was already set to 077.")

		self.logger.info("Done updating the system's umask so that files and directories created by a user are only accessible to themself.")

		return True

	#End updateUmask(self):


	'''
	This function updates the /home directory to 0755 and user's home to 0700.
	Instead of checking permissions first it is just a quick to set them even
	if not necessary.
	'''
	def updateHomeDir(self):
		homeDir = '/home'

		self.logger.info("Updating the system's /home directory permissions to 0755 and each user's home directory in /home to 0700.")

		os.chmod(homeDir, stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)

		if not oct(os.stat(homeDir).st_mode & 0777) == '0755':
			self.logger.error("Problems were encountered while setting the permissions of " + homeDir + " to 0755.")
			return False

		#Get the list of user directories in /home.
		userDirList = os.walk(homeDir).next()[1]

		for dir in userDirList:
			userDir = homeDir + '/' + dir
			os.chmod(userDir, stat.S_IRWXU)

			if not oct(os.stat(userDir).st_mode & 0777) == '0700':
				self.logger.error("Problems were encountered while setting the permissions of " + userDir + " to 0700.")
				return False

		self.logger.info("Done updating the system's /home directory permissions to 0755 and each user's home directory in /home to 0700.")

		return True
			
	#End updateHomeDir(self):

#End ConfigureUmaskHomeDir:
