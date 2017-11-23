import subprocess
import csurUtils
import os
import re
import datetime
import time


class ComputeNodeUpdate():

	def __init__(self):
		self.installSoftwareProblemDict = {}
		self.installDriverProblemDict = {}
		self.installFirmwareProblemDict = {}

		self.updateSoftwareDict = {}
		self.updateDriverDict = {}
		self.updateFirmwareDict = {}

		self.baseDir = '/hp/support/csur/'

	def updateSoftware(self, softwareToUpdate, softwareDict, OSDistLevel):
		self.updateSoftwareDict = softwareDict
		softwareDir = self.baseDir + 'software/' + OSDistLevel + '/'

		csurUtils.log("Begin Updating software.", "info")
		csurUtils.log("softwareDict = " + str(softwareDict), "debug")

		for software in softwareToUpdate:
			time.sleep(2)			
			print "\tUpdating package " + software

			#Need to removed hponcfg first on RHEL systems due to package version mis-match causing installtion file conflicts.
			if software == "hponcfg" and re.match("RHEL6.*", OSDistLevel):
				#First make sure it is already installed
				command = "rpm -q hponcfg"
                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()
				
                                if result.returncode == 0:
					command = "rpm -e hponcfg"
					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
					out, err = result.communicate()

					if result.returncode != 0:
						csurUtils.log(err, "error")
						csurUtils.log("stdout = " + out, "error")
						self.installSoftwareProblemDict[software] = ''
						continue

			#hp-health needs to be stopped first since it has been known to cause installtion problems.
			if software == "hp-health":
				#First make sure it is already installed
				command = "rpm -q hp-health"
                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()
				
				#This means hp-health is installed.
                                if result.returncode == 0:
					command = "/etc/init.d/hp-health stop"

					#Spend up to two minutes trying to stop hp-health
					timedProcessThread = csurUtils.TimedProcessThread(command, 120)
					timedProcessThread.start()
					returncode = timedProcessThread.join()

					if returncode != 0:
						csurUtils.log("hp-health could not be stopped; will try to kill it now.", "error")

						command = "pgrep -x hpasmlited"
						result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
						out, err = result.communicate()
						
						#The result should be 0 unless it just stopped suddenly.
						if result.returncode == 0:
							hpHealthPID = out.strip()
							command = "kill -9 " + hpHealthPID
							#Spend up to two more minutes trying to stop hp-health
							timedProcessThread = csurUtils.TimedProcessThread(command, 120)
							timedProcessThread.start()
							returncode = timedProcessThread.join()

							if returncode != 0:
								csurUtils.log("hp-health could not be stopped; skipping update of hp-health.", "error")
								self.installSoftwareProblemDict[software] = ''
								continue

			command = "rpm -U --oldpackage --nosignature " + softwareDir + softwareDict[software]
			csurUtils.log("command = " + command, "debug")

			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			csurUtils.log("out = " + out, "debug")

			if result.returncode != 0:
				csurUtils.log(err, "error")
				csurUtils.log("stdout = " + out, "error")
				self.installSoftwareProblemDict[software] = ''

		if len(self.installSoftwareProblemDict) != 0:
			print csurUtils.RED + "\tThere were problems updating the software.\n\tCheck the log file for additional information.\n" + csurUtils.RESETCOLORS
		else:
			print csurUtils.GREEN + "\tSoftware update completed successfully.\n" + csurUtils.RESETCOLORS

		csurUtils.log("End Updating software.", "info")
	#End updateSoftware(softwareList)


	def updateDrivers(self, driverDict, OSDistLevel, systemModel):
		self.updateDriverDict = driverDict
		driverDir = self.baseDir + 'drivers/' + OSDistLevel + '/'

		csurUtils.log("Begin Updating drivers.", "info")
		csurUtils.log("driverDict = " + str(driverDict), "debug")

		for driverKey in driverDict:
			time.sleep(2)			
			print "\tUpdating driver " + driverKey
			'''
			nx_nic driver has to be removed first if it is an old driver, since the packages have been renamed.
			We also save a copy of the original RPMs just in case.
			'''
			if driverKey == "nx_nic" and ((systemModel == 'DL580G7') or (systemModel == 'DL980G7')):
				command = "rpm -qa|grep ^hpqlgc-nx"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if result.returncode != 0:
					command = "rpm -e hp-nx_nic-kmp-default hp-nx_nic-tools"
					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
					out, err = result.communicate()

					if err != '' or result.returncode != 0:
						csurUtils.log(err, "error")
						csurUtils.log("stdout = " + out, "error")
						self.installDriverProblemDict[driverKey] = ''
						continue

			#Need to remove the hp-be2net-kmp-default driver first as it will cause a conflict.
			if driverKey == "be2net":
				command = "rpm -q hp-be2net-kmp-default"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if result.returncode == 0:
					command = "rpm -e hp-be2net-kmp-default"
					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
					out, err = result.communicate()

					if err != '':
						csurUtils.log(err, "error")
						self.installDriverProblemDict[driverKey] = ''
						continue
			
			if ':' not in driverDict[driverKey]:
				driverRPMList = driverDir + driverDict[driverKey]
			else:
				if driverKey != "be2net":
					driverRPMsString = driverDict[driverKey]
					tmpDriverRPMList = driverRPMsString.replace(':', ' ' + driverDir)
					driverRPMList = driverDir + tmpDriverRPMList
				else:
					'''
					We have to install the driver before the Fibre Channel Enablement Kit.  
					Thus we will install the be2net driver and Fibre Channel Enablement Kit
					as a separate step.
					'''
					driverRPMsString = driverDict[driverKey]
					location = driverRPMsString.find(':')
					driver = driverDir + (driverRPMsString[:location])
					newRPMList = (driverRPMsString[(location + 1):])
					tmpNewRPMList = newRPMList.replace(':', ' ' + driverDir)
					cnaRPMList = driverDir + tmpNewRPMList

					#Install the be2net driver.
					command = "rpm -U --oldpackage --nosignature " + driver
					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
					out, err = result.communicate()

					csurUtils.log("out = " + out, "debug")

					if result.returncode != 0:
						csurUtils.log(err, "error")
						csurUtils.log("stdout = " + out, "error")
						self.installDriverProblemDict[driverKey] = ''
						continue
					
					#Install the Fibre Channel Enablement Kit.
					command = "rpm -U --replacepkgs --nosignature " + cnaRPMList
					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
					out, err = result.communicate()

					csurUtils.log("out = " + out, "debug")

					if result.returncode != 0:
						csurUtils.log(err, "error")
						csurUtils.log("stdout = " + out, "error")
		
					continue

			command = "rpm -U --oldpackage --nosignature " + driverRPMList
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			csurUtils.log("out = " + out, "debug")

			if result.returncode != 0:
				csurUtils.log(err, "error")
				csurUtils.log("stdout = " + out, "error")
				self.installDriverProblemDict[driverKey] = ''

		if len(self.installDriverProblemDict) != 0:
			print csurUtils.RED + "\tThere were problems updating the drivers.\n\tCheck the log file for additional information.\n" + csurUtils.RESETCOLORS
		else:
			print csurUtils.GREEN + "\tDriver update completed successfully.\n" + csurUtils.RESETCOLORS

		csurUtils.log("End Updating drivers.", "info")
	#End updateDrivers(driverDict, OSDistLevel, systemModel)


	def updateFirmware(self, firmwareDict, OSDistLevel):
		self.updateFirmwareDict = firmwareDict

		firmwareDir = self.baseDir + 'firmware/'

		#This is for firmware that is installed using a smart component.
		regex = ".*\.scexe"

		#This would be part of the error message if already installed.
		message = "is already installed"

		csurUtils.log("Begin Updating firmware.", "info")
		csurUtils.log("firmwareDict = " + str(firmwareDict), "debug")

		#This may not be necessary if not updating NIC cards, but it won't hurt either.
		self.bringUpNetworks()

		for firmwareKey in firmwareDict:
			time.sleep(2)			
			timeFeedbackThread = csurUtils.TimeFeedbackThread("firmware", firmwareKey)
			timeFeedbackThread.start()

			'''
			If updating DL580Gen8 (CS500)BIOS to 1.6 make required network configuration changes. 
			This applies to CSUR1506.
			'''
			if firmwareKey == "BIOSDL580Gen8" and re.match("SLES.*", OSDistLevel) and re.match(".*p79-1.60", firmwareDict[firmwareKey]):
				command = "updateNetworkCFGFiles.pl"
                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()

                                if err != '':
                                        csurUtils.log(err, "error")

			if re.match(regex, firmwareDict[firmwareKey]):
				os.chdir(firmwareDir)
				command = "./" + firmwareDict[firmwareKey] + " -f -s"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if err != '':
					csurUtils.log(err, "error")
				csurUtils.log("out = " + out, "debug")

				if result.returncode == 3:
					csurUtils.log("stdout = " + out, "error")
					self.installFirmwareProblemDict[firmwareKey] = ''

				timeFeedbackThread.stopTimer()
				timeFeedbackThread.join()
			else:
				rpm = firmwareDict[firmwareKey]
				command = "rpm -U --oldpackage --nosignature " + firmwareDir + rpm
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()
				
				if err != '' or result.returncode == 1:
					if err == '':
						csurUtils.log("stdout = " + out, "error")
						self.installFirmwareProblemDict[firmwareKey] = ''
						timeFeedbackThread.stopTimer()
						timeFeedbackThread.join()
						continue
					else:
						if not err.find(message):
							csurUtils.log(err, "error")
							self.installFirmwareProblemDict[firmwareKey] = ''
							timeFeedbackThread.stopTimer()
							timeFeedbackThread.join()
							continue

				'''
				Currently firmware RPMs end with x86_64.rpm or i386.rpm.
				'''
				if rpm.endswith("x86_64.rpm"):	
					firmwareRPMDir = '/usr/lib/x86_64-linux-gnu/'
					setupDir = firmwareRPMDir + rpm[0:rpm.index('.x86_64.rpm')]
				else:
					firmwareRPMDir = '/usr/lib/i386-linux-gnu/'
					setupDir = firmwareRPMDir + rpm[0:rpm.index('.i386.rpm')]


				os.chdir(setupDir)
				setupFile = setupDir + "/hpsetup"

                                '''
                                Need to check setup file, since there is no consistency between RPM images.
                                '''
                                if os.path.isfile(setupFile):
                                        command = "./hpsetup -f -s"
                                else:
                                        command = "./.hpsetup -f -s"

				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if result.returncode == 3:
					csurUtils.log("stdout = " + out, "error")
					self.installFirmwareProblemDict[firmwareKey] = ''

				timeFeedbackThread.stopTimer()
				timeFeedbackThread.join()

		if len(self.installFirmwareProblemDict) != 0:
			print csurUtils.RED + "\tThere were problems updating the firmware.\n\tCheck the log file for additional information.\n" + csurUtils.RESETCOLORS
		else:
			print csurUtils.GREEN + "\tFirmware update completed successfully.\n" + csurUtils.RESETCOLORS

		csurUtils.log("End Updating firmware.", "info")
	#End updateFirmware(firmwareDict)


	'''
	We need to bring up all the NIC cards, since the firmware will not update them if they are down.
	'''
	def bringUpNetworks(self):
		count = 1

		command = "ip link show|egrep -i \".*<BROADCAST,MULTICAST>.*DOWN.*\"|awk '{sub(/:$/, \"\", $2);print $2}'"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		nicList = out.splitlines()

		for nic in nicList:
			command = "ifconfig " + nic + " 10.1.1." + str(count) + "/32  up"
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if err != '' or result.returncode  != 0:
				csurUtils.log("stdout = " + out, "error")
				csurUtils.log(err, "error")

			count+=1
	#End bringUpNetworks():


	def finalizeUpdate(self, hostname, systemModel):
		date = (datetime.date.today()).strftime('%d, %b %Y')
		dateCaption = "System Update Date: " + date
		title = "System update for " + hostname + " (" + systemModel + ")"

		successfulSoftware = []
		successfulDrivers = []
		successfulFirmware = []

		unSuccessfulSoftware = []
		unSuccessfulDrivers = []
		unSuccessfulFirmware = []

		self.getSuccessfulComponentInstalls(successfulSoftware, successfulDrivers, successfulFirmware)
		self.getUnsuccessfulComponentInstalls(unSuccessfulSoftware, unSuccessfulDrivers, unSuccessfulFirmware)

		csurUtils.log("+" + "-"*78 + "+", "info")
		print csurUtils.YELLOW + "+" + "-"*78 + "+" + csurUtils.RESETCOLORS
		csurUtils.log("| " + dateCaption.ljust(77) + "|", "info")
		print csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS + dateCaption.ljust(77) + csurUtils.YELLOW + "|" + csurUtils.RESETCOLORS
		csurUtils.log("+" + "-"*78 + "+", "info")
		print csurUtils.YELLOW + "+" + "-"*78 + "+" + csurUtils.RESETCOLORS
		csurUtils.log("|" + title.center(78) + "|", "info")
		print csurUtils.YELLOW + "|" + csurUtils.RESETCOLORS + title.center(78) + csurUtils.YELLOW + "|" + csurUtils.RESETCOLORS
		csurUtils.log("+" + "-"*78 + "+", "info")
		print csurUtils.YELLOW + "+" + "-"*78 + "+" + csurUtils.RESETCOLORS

		#Print successful updates.
		count = max(len(successfulSoftware), len(successfulDrivers), len(successfulFirmware))

		if count != 0:
			csurUtils.log("|" + "The following components were successfully updated".center(78) + "|", "info")
			print csurUtils.YELLOW + "|" + csurUtils.RESETCOLORS + csurUtils.GREEN + "The following components were successfully updated".center(78) + csurUtils.RESETCOLORS + csurUtils.YELLOW + "|" + csurUtils.RESETCOLORS
			csurUtils.log("+" + "-"*78 + "+", "info")
			print csurUtils.YELLOW + "+" + "-"*78 + "+" + csurUtils.RESETCOLORS
			csurUtils.log("| Software".ljust(27) + "| Drivers".ljust(27) + "| Firmware".ljust(25) + "|", "info")
			print csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS + csurUtils.BLUE + "Software".ljust(25) + csurUtils.RESETCOLORS + csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS + csurUtils.BLUE + "Drivers".ljust(25) + csurUtils.RESETCOLORS + csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS + csurUtils.BLUE + "Firmware".ljust(23) + csurUtils.RESETCOLORS + csurUtils.YELLOW + "|" + csurUtils.RESETCOLORS
			csurUtils.log("+" + "-"*78 + "+", "info")
			print csurUtils.YELLOW + "+" + "-"*78 + "+" + csurUtils.RESETCOLORS

			for i in range(0, count):
				if len(successfulSoftware) > i:
					row = "| " + successfulSoftware[i].ljust(25) + "| "			
					printRow = csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS + successfulSoftware[i].ljust(25) + csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS
				else:
					row = "| " + ' '.ljust(25) + "| "			
					printRow = csurUtils.YELLOW + "| " + ' '.ljust(25) + "| " + csurUtils.RESETCOLORS			

				if len(successfulDrivers) > i:
					row = row + successfulDrivers[i].ljust(25) + "| "
					printRow = printRow + successfulDrivers[i].ljust(25) + csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS
				else:
					row = row + ' '.ljust(25) + "| "
					printRow = printRow + ' '.ljust(25) + csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS

				if len(successfulFirmware) > i:
					row = row + successfulFirmware[i].ljust(23) + "|"
					printRow = printRow + successfulFirmware[i].ljust(23) + csurUtils.YELLOW + "|" + csurUtils.RESETCOLORS
				else:
					row = row + ' '.ljust(23) + "|"			
					printRow = printRow + ' '.ljust(23) + csurUtils.YELLOW + "|" + csurUtils.RESETCOLORS

				csurUtils.log(row, "info")
				print printRow

			csurUtils.log("+" + "-"*78 + "+", "info")
			print csurUtils.YELLOW + "+" + "-"*78 + "+" + csurUtils.RESETCOLORS

		#Print unsuccessful updates.
		count = max(len(unSuccessfulSoftware), len(unSuccessfulDrivers), len(unSuccessfulFirmware))
		rows = ''

		if count != 0:
			csurUtils.log("|" + "The following components were unsuccessfully updated".center(78) + "|", "info")
			print csurUtils.YELLOW + "|" + csurUtils.RESETCOLORS + csurUtils.RED + "The following components were unsuccessfully updated".center(78) + csurUtils.RESETCOLORS + csurUtils.YELLOW + "|" + csurUtils.RESETCOLORS
			csurUtils.log("+" + "-"*78 + "+", "info")
			print csurUtils.YELLOW + "+" + "-"*78 + "+" + csurUtils.RESETCOLORS
			csurUtils.log("| Software".ljust(27) + "| Drivers".ljust(27) + "| Firmware".ljust(25) + "|", "info")
			print csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS + csurUtils.BLUE + "Software".ljust(25) + csurUtils.RESETCOLORS + csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS + csurUtils.BLUE + "Drivers".ljust(25) + csurUtils.RESETCOLORS + csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS + csurUtils.BLUE + "Firmware".ljust(23) + csurUtils.RESETCOLORS + csurUtils.YELLOW + "|" + csurUtils.RESETCOLORS
			csurUtils.log("+" + "-"*78 + "+", "info")
			print csurUtils.YELLOW + "+" + "-"*78 + "+" + csurUtils.RESETCOLORS

			for i in range(0, count):
				if len(unSuccessfulSoftware) > i:
					row = "| " + unSuccessfulSoftware[i].ljust(25) + "| "			
					printRow = csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS + unSuccessfulSoftware[i].ljust(25) + csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS
				else:
					row = "| " + ' '.ljust(25) + "| "			
					printRow = csurUtils.YELLOW + "| " + ' '.ljust(25) + "| " + csurUtils.RESETCOLORS			

				if len(unSuccessfulDrivers) > i:
					row = row + unSuccessfulDrivers[i].ljust(25) + "| "
					printRow = printRow + unSuccessfulDrivers[i].ljust(25) + csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS
				else:
					row = row + ' '.ljust(25) + "| "
					printRow = printRow + ' '.ljust(25) + csurUtils.YELLOW + "| " + csurUtils.RESETCOLORS

				if len(unSuccessfulFirmware) > i:
					row = row + unSuccessfulFirmware[i].ljust(23) + "|"
					printRow = printRow + unSuccessfulFirmware[i].ljust(23) + csurUtils.YELLOW + "|" + csurUtils.RESETCOLORS
				else:
					row = row + ' '.ljust(23) + "|"			
					printRow = printRow + ' '.ljust(23) + csurUtils.YELLOW + "|" + csurUtils.RESETCOLORS

				csurUtils.log(row, "info")
				print printRow

			csurUtils.log("+" + "-"*78 + "+", "info")
			print csurUtils.YELLOW + "+" + "-"*78 + "+" + csurUtils.RESETCOLORS

		if count != 0:
			print csurUtils.RED + "\nThe update completed with errors.  Check log file for additional information." + csurUtils.RESETCOLORS
                	exit(1)
        	else:
                	print csurUtils.GREEN + "\nThe update completed successfully.  Reboot the system for changes to take affect." + csurUtils.RESETCOLORS
                	exit(0)
	#End finalizeUpdate()


	def getSuccessfulComponentInstalls(self, successfulSoftware, successfulDrivers, successfulFirmware):
		if len(self.updateSoftwareDict) != 0:
			for software in self.updateSoftwareDict:
				if not self.installSoftwareProblemDict.has_key(software):
					successfulSoftware.append(software)
					
		if len(self.updateDriverDict) != 0:
			for driver in self.updateDriverDict:
				if not self.installDriverProblemDict.has_key(driver):
					successfulDrivers.append(driver)
					
		if len(self.updateFirmwareDict) != 0:
			for firmware in self.updateFirmwareDict:
				if not self.installFirmwareProblemDict.has_key(firmware):
					successfulFirmware.append(firmware)
	#End getSuccessfulComponentInstalls(successfulSoftware, successfulDrivers, successfulFirmware)


	def getUnsuccessfulComponentInstalls(self, unSuccessfulSoftware, unSuccessfulDrivers, unSuccessfulFirmware):
		if len(self.installSoftwareProblemDict) != 0:
			for software in self.installSoftwareProblemDict:
				unSuccessfulSoftware.append(software)

		if len(self.installDriverProblemDict) != 0:
			for driver in self.installDriverProblemDict:
				unSuccessfulDrivers.append(driver)
					
		if len(self.installFirmwareProblemDict) != 0:
			for firmware in self.installFirmwareProblemDict:
				unSuccessfulFirmware.append(firmware)
	#End getUnsuccessfulComponentInstalls(unSuccessfulSoftware, UnsuccessfulDrivers, UnsuccessfulFirmware)
#End ComputeNodeUpdate()
