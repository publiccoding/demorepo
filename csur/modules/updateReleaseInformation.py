# Embedded file name: ./updateReleaseInformation.py
import logging
import re
import datetime

def updateVersionInformationFile(csurResourceDict):
    result = True
    computeNodeDict = csurResourceDict['componentListDict']['computeNodeList'][0].getComputeNodeDict()
    logger = logging.getLogger(computeNodeDict['loggerName'])
    logger.info('Updating the csur bundle version information file.')
    try:
        releaseNotes = csurResourceDict['releaseNotes']
        versionInformationFile = re.sub('\\s+', '', csurResourceDict['versionInformationFile'])
    except KeyError as err:
        logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
        result = False

    if result:
        releaseNotes = re.sub('Install Date:', 'Install Date: ' + str(datetime.datetime.now()), releaseNotes)
        try:
            f = open(versionInformationFile, 'a')
            f.write(releaseNotes + '\n')
        except IOError as err:
            logger.error('Unable to update the csur bundle version information file.\n' + str(err))
            result = False
        finally:
            f.close()

    logger.info('Done updating the csur bundle version information file.')
    return result