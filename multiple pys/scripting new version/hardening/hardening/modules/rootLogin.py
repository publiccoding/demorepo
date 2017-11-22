import subprocess
import logging
import datetime
import shutil
import re
import os


'''
This class is used to configure root logins.
'''
class ConfigureRootLogin:

        def __init__(self, loggerName):
		self.logger = logging.getLogger(loggerName)
        #End __init__(self):


	'''
	This method will configure sshd so that root can no longer login
	via ssh.
	'''
	def configureSSHLogin(self):
		sshdConfigurationFile = '/etc/ssh/sshd_config'
		permitRootLogin = None
		commentedPermitRootLogin = False
		unCommentedPermitRootLogin = False
		updateRequired = True

		self.logger.info("Updating the system's sshd configuration file to disable root logins via ssh.")

		#Use date to create a time specific backup of the sshd configuration file.
		dateTimestamp = (datetime.datetime.now()).strftime('%Y%m%d%H%M%S')

		#Make a backup of the current sshd configuration.
		try:
			shutil.copy2(sshdConfigurationFile, sshdConfigurationFile + '.' + dateTimestamp)
		except IOError as err:
			self.logger.error("Unable to make a backup of the system's sshd configuration file.\n" + str(err))
			return False

		#Read sshd_config into an array, so we can parse it for the PermitRootLogin resource.
		try:
			f = open(sshdConfigurationFile, 'r')
			sshdConfigurationData = f.readlines()
			f.close()
		except IOError as err:
			self.logger.error("Unable to access the system's sshd configuration file.\n" + str(err))
			return False

		self.logger.debug("The sshd configuration file data was determined to be: " + str(sshdConfigurationData))
		
		for line in sshdConfigurationData:
			line = line.strip()

			if re.match('\s*PermitRootLogin\s+', line):
				unCommentedPermitRootLogin = True

				try:
					permitRootLogin = re.match('\s*PermitRootLogin\s+(.*)', line).group(1) 
				except AttributeError as err:
					self.logger.error("An AttributeError was encountered while getting the PermitRootLogin resource setting: " + str(err))
					return False

				if permitRootLogin.lower() == 'no':
					updateRequired = False
	
				break
			elif re.match('\s*#\s*PermitRootLogin\s+', line):
				commentedPermitRootLogin = True

		if updateRequired:
			if unCommentedPermitRootLogin:
				command = "sed -i '0,/^\s*PermitRootLogin.*$/s//PermitRootLogin no/' " + sshdConfigurationFile
			elif commentedPermitRootLogin:
				command = "sed -i '0,/^\s*#\s*PermitRootLogin.*$/s//PermitRootLogin no/' " + sshdConfigurationFile
			else:
				command = 'echo "PermitRootLogin no" >> ' + sshdConfigurationFile 

			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			self.logger.debug("The output of the command (" + command + ") used to update the sshd PermitRootLogin resource was: " + out.strip())

			if result.returncode != 0:
				self.logger.error("Problems were encountered while updating the system's sshd configuration file " + sshdConfigurationFile + ".\n" + err)
				return False
			else: #Confirm update.
				command = 'egrep "^\s*PermitRootLogin\s+no\s*" ' + sshdConfigurationFile

				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				self.logger.debug("The output of the command (" + command + ") used to check that the sshd PermitRootLogin resource was updated successfully was: " + out.strip())

				if result.returncode != 0:
					self.logger.error("Problems were encountered while updating the system's sshd configuration file " + sshdConfigurationFile + ".\n" + err)
					return False
		else:
			self.logger.info("The system's sshd configuration file was already configured to prevent root logins via ssh.")

		self.logger.info("Done updating the system's sshd configuration file to disable root logins via ssh.")

		return True

	#End configureSSHLogin(self):


	'''
	This method will configure the system so that root can only login on tty1 (console).
	Instead of first checking /etc/securetty, we just make a backup and create a new updated securetty file.
	'''
	def configureTTYLogin(self):
		secureTTYFile = '/etc/securetty'

		self.logger.info("Updating the system so that root can only login on tty1 (console).")

		#Use date to create a time specific backup of .
		dateTimestamp = (datetime.datetime.now()).strftime('%Y%m%d%H%M%S')

		#Make a backup of the current securetty file if it exists.
		if os.path.isfile('/etc/securetty'):
			try:
				shutil.copy2(secureTTYFile, secureTTYFile + '.' + dateTimestamp)
			except IOError as err:
				self.logger.error("Unable to make a backup of the system's securetty file.\n" + str(err))
				return False

		command = 'echo tty1 > ' + secureTTYFile 

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to update " + secureTTYFile + " was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Problems were encountered while updating " + secureTTYFile + ".\n" + err)
			return False
		else: #Confirm update.
			command = 'egrep tty1 ' + secureTTYFile

			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			self.logger.debug("The output of the command (" + command + ") used to check that " + secureTTYFile + " was updated successfully was: " + out.strip())

			if result.returncode != 0:
				self.logger.error("Problems were encountered while updating " + secureTTYFile + ".\n" + err)
				return False

		self.logger.info("Done updating the system so that root can only login on tty1 (console).")

		return True

	#End configureTTYLogin(self):

#End ConfigureRootLogin:
