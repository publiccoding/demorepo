# Embedded file name: ./configureRepository.py
from spUtils import RED, RESETCOLORS
import subprocess
import logging
import os

def configureRepositories(patchDirList, loggerName):
    logger = logging.getLogger(loggerName)
    logger.info('Configuring patch repositories.')
    logger.info('The patch directory list is: ' + str(patchDirList))
    for dir in patchDirList:
        repositoryName = dir.split('/').pop()
        command = 'zypper lr ' + repositoryName
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ") used to list repository '" + repositoryName + "' was: " + out.strip())
        if result.returncode == 0:
            logger.info('Removing repository ' + repositoryName + ', since it was present.')
            command = 'zypper rr ' + repositoryName
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            logger.info('The output of the command (' + command + ") used to remove repository '" + repositoryName + "' was: " + out.strip())
            if result.returncode != 0:
                logger.error('The repository ' + repositoryName + ', could not be removed.\n' + err)
                print RED + 'Unable to remove existing repositories; check the log file for errors; exiting program execution.' + RESETCOLORS
                exit(1)
            else:
                logger.info('The repository ' + repositoryName + ', was successfully removed.')
        elif "Repository '" + repositoryName + "' not found by its alias" in err:
            logger.info('The repository ' + repositoryName + ', was not found to be present.')
        else:
            logger.error('Unable to get repository information using command ' + command + '\n' + err)
            print RED + 'Unable to get repository information; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)
        logger.info('Adding repository ' + repositoryName + '.')
        command = 'zypper ar -t plaindir ' + dir + ' ' + repositoryName
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ") used to add repository '" + repositoryName + "' was: " + out.strip())
        if result.returncode != 0:
            logger.error('The repository ' + repositoryName + ', was unsuccessfully added.\n' + err)
            print RED + 'Unable to to add repositories; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)
        else:
            logger.info('The repository ' + repositoryName + ', was successfully added.')

    logger.info('Done configuring patch repositories.')