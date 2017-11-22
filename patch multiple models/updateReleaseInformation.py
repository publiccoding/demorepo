#!/usr/bin/python

from spUtils import (RED, RESETCOLORS)
import logging
import re
import datetime


'''
This function updates the patch bundle version information file.  If the file
is not present it will be created.
Valid input for updateType is: 'all', 'kernel', 'os'.
The function returns either 'Failure' or 'Success'.
'''
def updateVersionInformationFile(patchResourceDict, updateType, loggerName):
		
	logger = logging.getLogger(loggerName)

	logger.info("Updating the patch bundle version information file.")

	try:
		releaseNotes = patchResourceDict['releaseNotes']
		versionInformationFile = re.sub('\s+', '', patchResourceDict['versionInformationFile'])
        except KeyError as err:
                logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
                return 'Failure'

	releaseNotes = re.sub('Install Date:', 'Install Date: ' + str(datetime.datetime.now()), releaseNotes)

	try:
		f = open(versionInformationFile, 'a')

        	if updateType == 'all':
			releaseNotes = re.sub('Comments', 'Both kernel and os patches.', releaseNotes)
			f.write(releaseNotes + '\n')
		elif updateType == 'kernel':
			releaseNotes = re.sub('Comments', 'Kernel patches only.', releaseNotes)
			f.write(releaseNotes + '\n')
		elif updateType == 'os':
			releaseNotes = re.sub('Comments', 'OS patches only.', releaseNotes)
			f.write(releaseNotes + '\n')
		else:
			logger.error("An invalid update type was used.  Valid types are 'all', 'kernel', or 'os'.")
			return 'Failure'
	except IOError as err:
		logger.error("Unable to update the patch bundle version information file.\n" + str(err))
                return 'Failure'
	
	f.close()

	logger.info("Done updating the patch bundle version information file.")

	return 'Success'

#End updateVersionInformationFile(patchResourceDict, updateType, loggerName):


'''
#This section is for running the module standalone for debugging purposes. Uncomment to use.
if __name__ == '__main__':

	patchResourceFile = '/hp/support/patches/resourceFiles/patchResourceFile'

	#Setup logging.
	loggerName = 'testLogger'
	logger = logging.getLogger(loggerName)
	logFile = 'updateVersionInformationFile.log'

        try:
                open(logFile, 'w').close()
        except IOError:
                print RED + "Unable to access " + logFile + " for writing." + RESETCOLORS
                exit(1)

        handler = logging.FileHandler(logFile)

	logger.setLevel(logging.DEBUG)
	handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

	#Save the options for later use.
        patchResourceDict['options'] = options

        #Get patch resource file data and save it to a dictionary (hash).
        try:
                with open(applicationResourceFile) as f:
                        for line in f:
                                line = line.strip()
                                #Remove quotes from resources.
                                line = re.sub('[\'"]', '', line)

                                #Ignore commented and blank lines.
                                if len(line) == 0 or re.match("^#", line):
                                        continue
                                else:
                                        (key, val) = line.split('=')
                                        key = re.sub('\s+', '', key)
                                        patchResourceDict[key] = val.lstrip()
        except IOError as err:
                print RED + "Unable to access the application's resource file " + applicationResourceFile + ".\n" + str(err) + "\n" + RESETCOLORS
                exit(1)

	#updateType is: 'os', 'kernel' or 'all'
	updateType = 'all'

	if updateVersionInformationFile(patchResourceDict, updateType, loggerName) == 'Success':
                print GREEN + "Successfully updated the patch bundle version information file." + RESETCOLORS
        else:
                print RED + "Failed to update the patch bundle version information file; check the log file for errors." + RESETCOLORS
'''
