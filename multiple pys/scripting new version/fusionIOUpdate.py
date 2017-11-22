import subprocess
import logging
import re
import time


'''
This class is used for updating the FusionIO driver and firmware subsystem 
on Gen1.0 Scale-up compute nodes.
'''
class FusionIOUpdate():
	def __init__(self, loggerName):
		self.loggerName = loggerName
		self.logger = logging.getLogger(loggerName)

		self.pid = 0
	#End __init__(loggerName):


	'''
	This function is used to update the firmware of the FusionIO DIMMs.
	'''
	def updateFusionIOFirmware(self, busList, firmwareDir):
		#Ensure self.pid is set to 0 before any work begins.
		self.pid = 0

		self.logger.info("Updating the FusionIO firmware.")

		for bus in busList:
			time.sleep(2)
			
			command = "fio-update-iodrive -y -f -s " + bus + ' ' + firmwareDir + '/' + "*.fff"
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=self.preexec, shell=True)

			#We get the processes PID in case the process is cancelled and we need to kill the process.
			self.pid = result.pid

			out, err = result.communicate()

			self.logger.debug("The output of the command (" + command + ") used to update the FusionIO firmware was: " + out.strip())

			if result.returncode != 0:
				self.logger.error("Failed to upgrade the FusionIO firmware:\n" + err)
				return False

		return True

		self.logger.info("Done updating the FusionIO firmware.")

	#End updateFusionIOFirmware(self, csurResourceDict, firmwareDir):


	'''
	This function is used to build and install the FusionIO driver.
	It also will install libvsl as well, since it had a dependency on the driver.
	'''
	def buildInstallFusionIODriver(self, csurResourceDict, driverDir):
		#Ensure self.pid is set to 0 before any work begins.
		self.pid = 0

		self.logger.info("Building and installing the FusionIO driver.")

		fusionSourceDir = driverDir + '/src/'

		try:
			fusionIODriverSrcRPM = re.sub('\s+', '', patchResourceDict['fusionIODriverSrcRPM'])
		except KeyError as err:
			self.logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
			return False

		#Build the driver for the new kernel.
		command = "rpmbuild --rebuild " + fusionSourceDir + fusionIODriverSrcRPM
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=self.preexec, shell=True)

		#We get the processes PID in case the process is cancelled and we need to kill the process.
		self.pid = result.pid

		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to build the FusionIO driver was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Failed to build the FusionIO driver:\n" + err)
			return False

		out = out.strip()

		kernel = csurResourceDict['kernel']
		processorType = csurResourceDict['processorType']

		'''
		This strips off iomemory from RPM name, since it will not be needed in the regex match.
		Additionally, the source RPM is renamed to the driver RPM's name, which includes the current 
		kernel and processor type in its name.
		'''
		fusionIODriverRPM = (fusionIODriverSrcRPM.replace('iomemory-vsl', '-vsl-' + kernel)).replace('src', processorType)

		#Compile the regex that will be used to get the driver RPM location.
		fusionIODriverPattern = re.compile('.*Wrote:\s+((/[0-9,a-z,A-Z,_]+)+' + fusionIODriverRPM +')', re.DOTALL)

		self.logger.debug("The regex used to get the FusionIO driver RPM location was: " + fusionIODriverPattern.pattern)

		driverRPM = re.match(fusionIODriverPattern, out).group(1)

		self.logger.debug("The FuionIO driver was determined to be: " + driverRPM)

		#Install the FusionIO software and driver.
		command = "rpm -ivh " + driverDir + '/' + "libvsl-*.rpm " + driverRPM 
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=self.preexec, shell=True)

		#We get the processes PID in case the process is cancelled and we need to kill the process.
		self.pid = result.pid

		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to install the FusionIO driver was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Failed to install the FusionIO driver:\n" + err)
			return False

		self.logger.info("Done building and installing the FusionIO driver.")

		return True

	#End buildInstallFusionIODriver(self, csurResourceDict, driverDir):


	'''
	This function is used to retrieve the PID of the currently running update.
	'''
	def getUpdatePID(self):
		return self.pid
	#End getUpdatePID(self):
