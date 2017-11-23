# Embedded file name: ./updateReleaseInformation.py
from spUtils import RED, RESETCOLORS
import logging
import re
import datetime

def updateVersionInformationFile(patchResourceDict, updateType, loggerName):
    logger = logging.getLogger(loggerName)
    logger.info('Updating the patch bundle version information file.')
    try:
        releaseNotes = patchResourceDict['releaseNotes']
        versionInformationFile = re.sub('\\s+', '', patchResourceDict['versionInformationFile'])
    except KeyError as err:
        logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
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
        logger.error('Unable to update the patch bundle version information file.\n' + str(err))
        return 'Failure'

    f.close()
    logger.info('Done updating the patch bundle version information file.')
    return 'Success'