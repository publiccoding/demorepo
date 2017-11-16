# Embedded file name: ./oneOffs.py
import subprocess
import logging
import re

class OneOffs:
    """
    This function is used to remove RPMs.
    """

    def removeRPMs(self, rpmsToRemove, loggerName):
        logger = logging.getLogger(loggerName)
        logger.info('Removing the RPMs, which were identified by the csur resource file for removal.')
        rpmsToRemoveList = re.sub(',\\s*', ' ', rpmsToRemove).split()
        rpmList, result = self.__checkRPMsForRemoval(rpmsToRemoveList, loggerName)
        if not result:
            logger.error('Problems were encountered while getting the updated list of RPMs to remove.')
            return (False, rpmsToRemove)
        rpmsToRemove = ' '.join(rpmList)
        if len(rpmsToRemove) != 0:
            command = 'rpm -e ' + rpmsToRemove
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            logger.info('The output of the command (' + command + ') used to remove the pre-identified RPMs for removal was: ' + out.strip())
            if result.returncode == 0:
                logger.info('Successfully removed the following RPMs: ' + rpmsToRemove)
            else:
                logger.error('Problems were encountered while removing the RPMs which were identified by the patch resource file for removal.\n' + err)
                return (False, re.sub('\\s+', ', ', rpmsToRemove))
        else:
            logger.info('There were no RPMs that needed to be removed.')
        logger.info('Done removing the RPMs, which were identified by the csur resource file for removal.')
        return (True, '')

    def __checkRPMsForRemoval(self, rpmsToRemoveList, loggerName):
        updatedRPMList = []
        result = True
        logger = logging.getLogger(loggerName)
        logger.info('Checking the installed RPMs for removal.')
        command = 'rpm -qa'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ') used to get a list of the installed RPMs was: ' + out.strip())
        if result.returncode != 0:
            logger.error('Problems were encountered while getting a list of the installed RPMs.\n' + err)
            result = False
        else:
            rpmList = out.split()
            for rpm in rpmsToRemoveList:
                for installedRPM in rpmList:
                    if re.match(rpm, installedRPM) != None:
                        updatedRPMList.append(installedRPM)

        logger.info('Done checking the installed RPMs for removal.')
        return (updatedRPMList, result)