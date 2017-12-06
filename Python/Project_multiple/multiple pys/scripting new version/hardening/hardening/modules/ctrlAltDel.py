import subprocess
import logging
import datetime
import shutil
import re


'''
This class is used to comment out the ctrl+alt+del trap in inittab so 
users can no longer use this key sequence to reboot a system.
'''
class ConfigureCtrlAltDel:
	'''
	This method will disable the key sequence ctrl+alt+del, which is used to reboot a system.
	'''
	def disableCtrlAltDel(self, loggerName, osDistLevel):
		logger = logging.getLogger(loggerName)

		logger.info("Updating the system so that the key sequence ctrl+alt+del no longer causes a system reboot.")

		'''
		SLES4SAP 11.4 uses inittab while SLES4SAP 12.x uses systemd.
		'''
		if osDistLevel == 'SLES4SAP_11.4':
			inittabFile = '/etc/inittab'
			ctrlaltdelSet = False

			#Use date to create a time specific backup of the inittab file.
			dateTimestamp = (datetime.datetime.now()).strftime('%Y%m%d%H%M%S')

			#Make a backup of the current inittab file.
			try:
				shutil.copy2(inittabFile, inittabFile + '.' + dateTimestamp)
			except IOError as err:
				logger.error("Unable to make a backup of the system's inittab file.\n" + str(err))
				return False

			#Read inittab into an array, so it can be parsed for ctrlaltdel.
			try:
				f = open(inittabFile, 'r')
				inittabConfigurationData = f.readlines()
				f.close()
			except IOError as err:
				logger.error("Unable to access the system's inittab file.\n" + str(err))
				return False

			logger.debug("The inittab file data was determined to be: " + str(inittabConfigurationData))
			
			for line in inittabConfigurationData:
				line = line.strip()

				if re.match('\s*ca::ctrlaltdel', line):
					ctrlaltdelSet = True
					break

			#If ctraltdel was set then comment it out and check to confirm that it was successfully commented out.
			if ctrlaltdelSet:
				command = "sed -i '0,/^\s*ca::ctrlaltdel.*$/s//#&/' " + inittabFile

				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				logger.debug("The output of the command (" + command + ") used to update the inittab file was: " + out.strip())

				if result.returncode != 0:
					logger.error("Problems were encountered while updating the system's inittab file " + inittabFile + ".\n" + err)
					return False
				else: #Confirm update.
					command = 'egrep "^\s*ca::ctrlaltdel.*$ ' + inittabFile

					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
					out, err = result.communicate()

					logger.debug("The output of the command (" + command + ") used to check that the inittab file was updated successfully was: " + out.strip())

					if result.returncode == 0:
						logger.error("Problems were encountered while updating the system's inittab file " + inittabFile + ".\n" + err)
						return False
			else:
				logger.info("The system's inittab file was already configured to prevent a system reboot via the ctrl+alt+del key sequence.")

		else:
			command = "systemctl status ctrl-alt-del.target"

			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			logger.debug("The output of the command (" + command + ") used to check if the key sequence ctrl+alt+del is enabled was: " + out.strip())

			if err != '': #Can't rely on the return code, since a number other then '0' does not mean the command failed.
				logger.error("Problems were encountered while checking if the key sequence ctrl+alt+del was enabled.\n" + err)
				return False
			else:
				if re.search('masked\s+\(/dev/null\)', out, re.IGNORECASE|re.DOTALL|re.MULTILINE) != None:
					logger.info("The system was already configured to prevent a system reboot via the ctrl+alt+del key sequence.")
				else:
					command = "systemctl mask ctrl-alt-del.target"

					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
					out, err = result.communicate()

					logger.debug("The output of the command (" + command + ") used to disable the ctrl+alt+del key sequence was: " + out.strip())

					if err != '':
						logger.error("Problems were encountered while disabling the ctrl+alt+del key sequence.\n" + err)
						return False
					else: # Confirm update.
						command = "systemctl status ctrl-alt-del.target"

						result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
						out, err = result.communicate()

						logger.debug("The output of the command (" + command + ") used to check if the key sequence ctrl+alt+del was disabled was: " + out.strip())

						if err != '':
							logger.error("Problems were encountered while checking if the key sequence ctrl+alt+del was disabled.\n" + err)
							return False
						else:
							if re.search('masked\s+\(/dev/null\)', out, re.IGNORECASE|re.DOTALL|re.MULTILINE) == None:
								logger.error("Problems were encountered while disabling the ctrl+alt+del key sequence.\n" + err)
								return False

		logger.info("Done updating the system so that the key sequence ctrl+alt+del no longer causes a system reboot.")

		return True

	#End disableCtrlAltDel(self, loggerName, osDistLevel):

#End ConfigureCtrlAltDel:
