#!/usr/bin/python

import logging
import os
import optparse
import subprocess
import time
import socket
import re
import signal
import computeNode
import csurUtils
import csurUpdate


def init():

	currentTime = 1444615201
	now = int(round(time.time()))

	try:
		if (now - currentTime) > 604800:
			raise NotImplementedError()
	except NotImplementedError:
		print csurUtils.RED + "NotImplementedError Bye" + csurUtils.RESETCOLORS
		exit(1)

	if os.geteuid() != 0:
		print csurUtils.RED + "You must be root to run this program." + csurUtils.RESETCOLORS
		exit(1)

	usage = 'usage: %prog [-g -f CSUR_FILENAME [-d]] or [-u -f CSUR_FILENAME [-d]]'

	parser = optparse.OptionParser(usage=usage)

	parser.add_option('-d', action='store_true', default=False, help='This option is used to collect debug information.', metavar=' ')
	parser.add_option('-f', action='store', help='This option is mandatory and requires its argument to be the data file containing CSUR reference information.', metavar='FILENAME')
	parser.add_option('-g', action='store_true', default=False, help='This option is used to collect system Gap Analysis data.', metavar=' ')
	parser.add_option('-u', action='store_true', default=False, help='This option is used when a system update is to be performed.', metavar=' ')

	(options, args) = parser.parse_args()

	if not options.f:
		parser.print_help()
		exit(1)
	else:
		csurDataFile = options.f

	if options.g == False and options.u == False:
		parser.print_help()
		exit(1)

	if options.g and options.u:
		parser.print_help()
		exit(1)

	if options.g:
		action = 'gapAnalysis'
	else:
		action = 'csurUpdate'

	try:
		fh = open(csurDataFile)
		csurData = fh.readlines()
	except IOError:
		print csurUtils.RED + "Unable to open " + csurDataFile + " for reading.\n" + csurUtils.RESETCOLORS
		exit(1)

	fh.close()

	#Always start with a new log file.
	try:
		if os.path.isfile(logFile):
			os.remove(logFile)
		else:
			open(logFile, 'w').close()
	except IOError:
		print csurUtils.RED + "Unable to access " + logFile + " for writing.\n" + csurUtils.RESETCOLORS
		exit(1)

	handler = logging.FileHandler(logFile)

	if options.d:
		csurUtils.setLogLevel('DEBUG')
		logger.setLevel(logging.DEBUG)
		handler.setLevel(logging.DEBUG)
	else:
		csurUtils.setLogLevel('INFO')
		logger.setLevel(logging.INFO)
		handler.setLevel(logging.INFO)

	formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	#Need OS distribution level which is needed to determine driver information.
	command = "cat /proc/version|grep -i suse"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if err != '':
		print csurUtils.RED + "Unable to get system OS type.\n" + err + csurUtils.RESETCOLORS
		exit(1)
		
	if result.returncode == 0:
		OSDist = 'SLES'
		command = "cat /etc/SuSE-release | grep PATCHLEVEL|awk '{print $3}'"
	else:
		OSDist = 'RHEL'
		command = "cat /etc/redhat-release | egrep -o \"[1-9]{1}\.[0-9]{1}\""

	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if err != '':
		print csurUtils.RED + "Unable to get OS distribution level.\n" + err + csurUtils.RESETCOLORS
		exit(1)
	else:
		if OSDist == 'SLES':
			OSDistLevel = OSDist + 'SP' + out.strip()
		else:
			OSDistLevel = OSDist +  out.strip()

	#Get system model.
	command = "dmidecode -s system-product-name|awk '{print $2$3}'"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if err != '':
		print csurUtils.RED + "Unable to get system model.\n" + err + csurUtils.RESETCOLORS
		exit(1)
		
	systemModel = out.strip()	

	#Need to make sure the correct CSUR file was provided.
	command = "egrep \"^" + OSDistLevel + "-.*" + systemModel + "\" "  + csurDataFile
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		print csurUtils.RED + "The wrong CSUR file was provided for this system (" + systemModel + ")" + csurUtils.RESETCOLORS
		exit(1)

	return  csurDataFile, csurData, action, OSDistLevel, systemModel
#End init()


'''
Once the update begins we do not want it interrupted as this could result in a system
being in an unknown state.
'''
def signal_handler(signum, frame):
	regex = r"^(y|n)$"

	print csurUtils.RED + "\nThe update should not be interrupted once started, since it could put the system in an unknown state.\n" + csurUtils.RESETCOLORS

	while True:
		response = raw_input("Do you really want to interrupt the update [y|n]: ")
		
		if not re.match(regex, response):
			print "A valid response is y|n.  Please try again."
			continue
		elif(response == 'y'):
			exit(1)
		else:
			return
#End signal_handler(signum, frame):


def firmware_signal_handler(signum, frame):
	print csurUtils.RED + "\nThe firmware update should not be interrupted once started, since it could put the system in an unknown state.\nIf you really want to interrupt the firmware update process then you will have to kill it.\n" + csurUtils.RESETCOLORS
#End firmware_signal_handler(signum, frame):
		
		
	
#####################################################################################################
# Main program starts here.
#####################################################################################################
logger = logging.getLogger()
logFile = "/hp/support/data/csur/csur.log"
hostname = socket.gethostname()
dateTimeStamp = time.strftime("%d-%b-%Y_%H:%M")
gapAnalysisFile = "/hp/support/data/csur/" + hostname + "_" + dateTimeStamp + "_gapAnalysis.dat"
firmwareToUpdate = []

csurDataFile, csurData, action, OSDistLevel, systemModel = init()

if (systemModel == 'DL580G7') or (systemModel == 'DL980G7'):
	computeNode = computeNode.Gen1ScaleUpComputeNode(systemModel, OSDistLevel, gapAnalysisFile)
elif systemModel == 'BL680cG7':
	computeNode = computeNode.ComputeNode(systemModel, OSDistLevel, gapAnalysisFile)
elif systemModel == 'DL580Gen8':
	computeNode = computeNode.DL580Gen8ComputeNode(systemModel, OSDistLevel, gapAnalysisFile)
else:
	print "Model " + systemModel + " is not a supported system type."
	exit(1)

firmwareDict = computeNode.getFirmwareDict(csurData[:])

if action == 'gapAnalysis':
	print "Phase 1: Getting system firmware Gap Analysis data."
else:
	print "Phase 1: Initializing system update."

#---------------------------------------------------------------------------------------
#Write log header and section header to gap analysis data file.
csurUtils.logGAHeader(hostname, systemModel, gapAnalysisFile)
csurUtils.logSectionHeader("Firmware", gapAnalysisFile)

#Get firmware inventory. We always get storage firmware first for data file formatting purposes.
computeNode.getStorageFirmwareInventory(firmwareDict.copy(), firmwareToUpdate)
computeNode.getNICFirmwareInventory(firmwareDict.copy(), firmwareToUpdate)
computeNode.getCommonFirmwareInventory(firmwareDict.copy(), firmwareToUpdate)
computeNode.getComputeNodeSpecificFirmwareInventory(firmwareDict.copy(), firmwareToUpdate)

#Close out section.
csurUtils.logSectionTail(gapAnalysisFile)

if computeNode.getFirmwareStatus():
	print "\n" + csurUtils.RED + "There were problems getting firmware information.\nCheck log file for addtional information.\n" + csurUtils.RESETCOLORS

if action == 'gapAnalysis':
	print "Phase 2: Getting system driver Gap Analysis data."

#---------------------------------------------------------------------------------------
csurUtils.logSectionHeader("Drivers", gapAnalysisFile)

#Get driver inventory.
driversToUpdate = computeNode.getDriverInventory(csurData[:])

if (systemModel == 'DL580G7') or (systemModel == 'DL980G7'):
	computeNode.getFusionIODriverInventory(csurData[:])

csurUtils.logSectionTail(gapAnalysisFile)

if computeNode.getDriverStatus():
	print "\n" + csurUtils.RED + "There were problems getting driver information.\nCheck log file for addtional information.\n" + csurUtils.RESETCOLORS

if action == 'gapAnalysis':
	print "Phase 3: Getting system software Gap Analysis data."

#---------------------------------------------------------------------------------------
csurUtils.logSectionHeader("Software", gapAnalysisFile)

#Get software inventory from CSUR file.
softwareToUpdate = computeNode.getSoftwareInventory(csurData[:])

csurUtils.logSectionTail(gapAnalysisFile)

if computeNode.getSoftwareStatus():
	print "\n" + csurUtils.RED + "There were problems getting software information.\nCheck log file for addtional information.\n" + csurUtils.RESETCOLORS

if action != 'csurUpdate':
	if computeNode.getFirmwareStatus() or computeNode.getDriverStatus() or computeNode.getDriverStatus():
		print csurUtils.RED + "\nGap Analysis data collection completed with errors.\nCheck log file for addtional information.\nAlso, collect data file " + gapAnalysisFile + " to create Gap Analysis report." + csurUtils.RESETCOLORS
		exit(1)
	else:
		print csurUtils.GREEN + "\nGap Analysis data collection completed successfully.  Collect data file\n" + gapAnalysisFile + " to create Gap Analysis report." + csurUtils.RESETCOLORS
		exit(0)

#---------------------------------------------------------------------------------------
#Beginning of update section.

#Set traps so that the software and driver update is not interrupted by the user without first giving them a chance to continue.
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGQUIT, signal_handler)

if computeNode.getFirmwareStatus() or computeNode.getDriverStatus() or computeNode.getDriverStatus():
	regex = r"^(y|n)$"
	print csurUtils.RED + "\nThere were errors while performing the system inventory." +  csurUtils.RESETCOLORS
	while True:
		response = raw_input("Do you want to continue at this time [y|n]: ")
		
		if not re.match(regex, response):
			print "A valid response is y|n.  Please try again."
			continue
		elif(response == 'n'):
			exit(1)
		else:
			break
	
#Instantiate the computeNode update class.
computeNodeUpdate = csurUpdate.ComputeNodeUpdate()

#Update software.
if len(softwareToUpdate) != 0:
	print "Phase 2: Updating software."
	updateDict = csurUtils.getPackageDict(softwareToUpdate[:], csurData[:], 'Software', OSDistLevel, systemModel)
	
	computeNodeUpdate.updateSoftware(softwareToUpdate[:], updateDict.copy(), OSDistLevel)
else:
	print "Phase 2: There was no software that needed to be updated."

#A 5 second delay between phases to give one a chance to read the screen in case it scrolls off.
time.sleep(5)
#Update drivers.
if len(driversToUpdate) != 0:
	print "Phase 3: Updating drivers."
	updateDict = csurUtils.getPackageDict(driversToUpdate[:], csurData[:], 'Drivers', OSDistLevel, systemModel)	
	computeNodeUpdate.updateDrivers(updateDict.copy(), OSDistLevel, systemModel)
else:
	print "Phase 3: There were no drivers that needed to be updated."

time.sleep(5)

#Set traps so that the firmware update is not interrupted by the user.
signal.signal(signal.SIGINT, firmware_signal_handler)
signal.signal(signal.SIGQUIT, firmware_signal_handler)

#Update firmware.
if len(firmwareToUpdate) != 0:
	print "Phase 4: Updating firmware."
	updateDict = csurUtils.getPackageDict(firmwareToUpdate[:], csurData[:], 'Firmware')	
	computeNodeUpdate.updateFirmware(updateDict.copy(), OSDistLevel)
else:
	print "Phase 4: There was no firmware that needed to be updated."

if len(softwareToUpdate) != 0 or len(driversToUpdate) != 0 or len(firmwareToUpdate) != 0:
	computeNodeUpdate.finalizeUpdate(hostname, systemModel)
else:
	print "There were no updates needed."
	exit(0)
