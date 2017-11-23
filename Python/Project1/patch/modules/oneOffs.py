# Embedded file name: ./oneOffs.py
import subprocess
import logging
import re

class OneOffs:

    def __init__(self, loggerName):
        self.logger = logging.getLogger(loggerName)

    def removeRPMs(self, patchResourceDict):
        rpmsForRemoval = ''
        count = 1
        self.logger.info('Removing the RPMs, which were identified by the patch resource file for removal.')
        try:
            rpmsToRemove = patchResourceDict['rpmsToRemove']
        except KeyError as err:
            self.logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
            return False

        rpmsToRemoveList = re.sub(',\\s*', ' ', rpmsToRemove).split()
        rpmList, result = self.__checkRPMsForRemoval(rpmsToRemoveList)
        if not result:
            self.logger.error('Problems were encountered while getting the updated list of RPMs to remove.')
            return False
        rpmsToRemove = ' '.join(rpmList)
        if len(rpmList) != 0:
            command = 'rpm -e ' + rpmsToRemove
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            self.logger.info('The output of the command (' + command + ') used to remove the pre-identified RPMs for removal was: ' + out.strip())
            if result.returncode == 0:
                self.logger.info('Successfully removed the following RPMs: ' + rpmsToRemove)
            else:
                self.logger.error('Problems were encountered while removing the RPMs which were identified by the patch resource file for removal.\n' + err)
                return False
        else:
            self.logger.info('There were no RPMs that needed to be removed.')
        self.logger.info('Done removing the RPMs, which were identified by the patch resource file for removal.')
        return True

    def addRPMs(self, patchResourceDict):
        self.logger.info('Adding the RPMs, which were identified by the patch resource file for addition.')
        try:
            additionalRPMSRepository = patchResourceDict['additionalSubDir']
            osPatchRepository = patchResourceDict['osSubDir']
            rpmsToAddList = re.sub('\\s+', '', patchResourceDict['rpmsToAdd']).split(',')
            self.logger.info('The list of RPMs to add was determined to be: ' + str(rpmsToAddList))
        except KeyError as err:
            self.logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
            return False

        updatedRPMSToAddList, result = self.__checkRPMsForAddition(rpmsToAddList)
        if not result:
            self.logger.error('Problems were encountered while getting the updated list of RPMs to add.')
            return False
        if len(updatedRPMSToAddList) != 0:
            rpmsToAdd = ' '.join(updatedRPMSToAddList)
            command = 'zypper -n --non-interactive-include-reboot-patches --no-refresh in -r ' + additionalRPMSRepository + ' -r ' + osPatchRepository + ' ' + rpmsToAdd
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            self.logger.info('The output of the command (' + command + ') used to add the pre-identified RPMs for addition was: ' + out.strip())
            if result.returncode == 0:
                self.logger.info('Successfully added the following RPMs: ' + rpmsToAdd)
            else:
                self.logger.error('Problems were encountered while adding the RPMs which were identified by the patch resource file for addition.\n' + err)
                return False
        else:
            self.logger.info('There were no RPMs that needed to be added.')
        self.logger.info('Done adding the RPMs, which were identified by the patch resource file for addition.')
        return True

    def __checkRPMsForAddition(self, rpmList):
        updatedRPMList = []
        result = True
        self.logger.info('Checking the installed RPMs for addition.')
        for rpm in rpmList:
            command = 'rpm -q ' + rpm
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            self.logger.info('The output of the command (' + command + ') used to check if an RPM was installed was: ' + out.strip())
            if result.returncode == 0:
                continue
            elif 'is not installed' in out:
                updatedRPMList.append(rpm)
            else:
                self.logger.error('Problems were encountered while checking if RPM ' + rpm + ' was installed.\n' + err)
                result = False
                break

        self.logger.info('The updated RPM list for addition was determined to be: ' + str(updatedRPMList))
        self.logger.info('Done checking the installed RPMs for addition.')
        return (updatedRPMList, result)

    def __checkRPMsForRemoval(self, rpmsToRemoveList):
        updatedRPMList = []
        result = True
        self.logger.info('Checking the installed RPMs for removal.')
        command = 'rpm -qa'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to get a list of the installed RPMs was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Problems were encountered while getting a list of the installed RPMs.\n' + err)
            result = False
        else:
            rpmList = out.split()
            for rpm in rpmsToRemoveList:
                for installedRPM in rpmList:
                    if re.match(rpm, installedRPM) != None:
                        updatedRPMList.append(installedRPM)

        self.logger.info('The updated RPM list for removal was determined to be: ' + str(updatedRPMList))
        self.logger.info('Done checking the installed RPMs for removal.')
        return (updatedRPMList, result)