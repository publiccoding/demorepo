# Embedded file name: ./computeNodeUpdate.py
import subprocess
import os
import re
import time
import logging
import threading
import datetime
import shutil
import signal
from csurUpdateUtils import TimedProcessThread, TimerThread
from fusionIOUtils import removeFusionIOPackages
from fusionIOUpdate import FusionIODriverUpdate, FusionIOFirmwareUpdate
from oneOffs import OneOffs
from serviceguard import Serviceguard

class ComputeNodeUpdate:

    def __init__(self, cursesThread, csurResourceDict, timerThreadLocation):
        self.cursesThread = cursesThread
        self.timerThreadLocation = timerThreadLocation
        self.csurResourceDict = csurResourceDict
        self.computeNodeDict = self.csurResourceDict['componentListDict']['computeNodeList'][0].getComputeNodeDict()
        self.componentUpdateDict = self.computeNodeDict['componentUpdateDict']
        self.updateComponentProblemDict = {'Firmware': {},
										   'Drivers': {},
										   'Software': {}}
        self.csurBasePath = self.csurResourceDict['csurBasePath']
        self.logger = logging.getLogger(self.computeNodeDict['loggerName'])
        self.timedProcessThread = ''
        self.pid = 0
        self.wait = False
        self.cancel = False
        self.fusionIODriverUpdateStarted = False
        self.fusionIOFirmwareUpdateStarted = False
        self.fusionIODriverUpdate = ''
        self.fusionIOFirmwareUpdateThreadList = []
        self.connectXCfgFile = '/etc/infiniband/connectx.conf'

    def updateComputeNodeComponents(self):
        timerThread = TimerThread('Updating compute node ' + self.computeNodeDict['hostname'] + ' ... ')
        timerThread.daemon = True
        timerThread.start()
        self.cursesThread.insertTimerThread(['', timerThread])
        if 'iomemory_vsl' in self.componentUpdateDict['Drivers']:
            self.fusionIODriverUpdate = FusionIODriverUpdate()
        if len(self.componentUpdateDict['Drivers']) != 0:
            self.__updateDrivers()
        if len(self.componentUpdateDict['Firmware']) != 0 and not self.cancel:
            self.__updateFirmware()
        if len(self.componentUpdateDict['Software']) != 0 and not self.cancel:
            self.__updateSoftware()
        if (len(self.componentUpdateDict['sgSoftware']) != 0 or len(self.componentUpdateDict['sgNFSSoftware']) != 0) and not self.cancel:
            serviceguard = Serviceguard(self.logger)
            upgradeCompleted = serviceguard.upgradeServiceguard(self.csurResourceDict.copy())
            if not upgradeCompleted:
                self.logger.error('The Serviceguard upgrade completed with errors.')
                self.updateComponentProblemDict['Software']['Serviceguard'] = ''
        timerThread.stopTimer()
        timerThread.join()
        self.cursesThread.updateTimerThread('Done updating compute node ' + self.computeNodeDict['hostname'] + '.', self.timerThreadLocation)

    def __updateSoftware(self):
        softwareDir = self.csurBasePath + '/software/computeNode/'
        softwareList = self.componentUpdateDict['Software']
        osDistLevel = self.computeNodeDict['osDistLevel']
        systemModel = self.computeNodeDict['systemModel']
        self.logger.info('Updating the software that was identified as needing to be updated.')
        if systemModel == '16sx86':
            if not self.__prepareForCS900SoftwareUpdate():
                self.updateComponentProblemDict['Software']['prepareForCS900SoftwareUpdate'] = ''
                return
        for software in softwareList:
            softwareName = re.match('(([a-zA-Z]+-*)+)', software).group(1).strip('-')
            time.sleep(2)
            while self.wait:
                time.sleep(1)

            if self.cancel:
                return
            if softwareName == 'hponcfg' and re.match('RHEL6.*', osDistLevel):
                command = 'rpm -q hponcfg'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to check if hponcfg is installed was: ' + out.strip())
                if result.returncode == 0:
                    out = out.splitlines()
                    command = 'rpm -e ' + ' '.join(out)
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    self.logger.info('The output of the command (' + command + ') used to remove hponcfg was: ' + out.strip())
                    if result.returncode != 0:
                        self.logger.error('Problems were encountered while trying to remove hponcfg; skipping update.\n' + err)
                        self.updateComponentProblemDict['Software'][softwareName] = ''
                        continue
            if softwareName == 'hp-health':
                command = 'rpm -q hp-health'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to check if hp-health is installed was: ' + out.strip())
                if result.returncode == 0:
                    if re.match('SLES12.*', osDistLevel):
                        command = 'systemctl stop hp-health'
                    else:
                        command = '/etc/init.d/hp-health stop'
                    self.timedProcessThread = TimedProcessThread(command, 120, self.computeNodeDict['loggerName'])
                    self.timedProcessThread.start()
                    self.pid = self.timedProcessThread.getProcessPID()
                    statusList = self.timedProcessThread.getCompletionStatus()
                    status = statusList[0]
                    self.pid = 0
                    if status == 'timedOut':
                        self.logger.error('hp-health could not be stopped; will try to kill it now.')
                        command = 'pgrep -x hpasmlited'
                        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        out, err = result.communicate()
                        self.logger.info('The output of the command (' + command + ') used to get the PID of hp-health was: ' + out.strip())
                        if result.returncode == 0:
                            hpHealthPID = out.strip()
                            command = 'kill -9 ' + hpHealthPID
                            self.timedProcessThread = TimedProcessThread(command, 120, self.computeNodeDict['loggerName'])
                            self.timedProcessThread.start()
                            self.pid = self.timedProcessThread.getProcessPID()
                            status = self.timedProcessThread.getCompletionStatus()
                            self.pid = 0
                            if status == 'timedOut':
                                self.logger.error('A second attempt to stop hp-health timed out; skipping update of hp-health.')
                                self.updateComponentProblemDict['Software'][softwareName] = ''
                                continue
                    elif status == 'Failed':
                        self.logger.error('An error was encountered while trying to stop hp-health; skipping update of hp-health.\n' + statusList[1])
                        self.updateComponentProblemDict['Software'][softwareName] = ''
                        continue
            if softwareName == 'FusionIO':
                if not removeFusionIOPackages(self.csurResourceDict['fusionIOSoftwareRemovalPackageList'], 'software', self.computeNodeDict['loggerName']):
                    self.logger.error('The FusionIO software could not be removed before updating/re-installing; skipping update of FusionIO software.')
                    self.updateComponentProblemDict['Software'][softwareName] = ''
                    continue
                updateSoftwareList = re.sub(',\\s*', ' ', self.csurResourceDict['fusionIOSoftwareInstallPackageList'])
                softwarePackage = softwareDir + re.sub(' ', ' ' + softwareDir, updateSoftwareList)
            else:
                softwarePackage = softwareDir + software
            command = 'rpm -U --quiet --oldpackage --replacefiles --replacepkgs --nosignature ' + softwarePackage
            self.timedProcessThread = TimedProcessThread(command, 180, self.computeNodeDict['loggerName'])
            self.timedProcessThread.setDaemon(True)
            self.timedProcessThread.start()
            self.pid = self.timedProcessThread.getProcessPID()
            status = self.timedProcessThread.getCompletionStatus()
            self.pid = 0
            if software == 'FusionIO' and ('iomemory_vsl' in self.updateComponentProblemDict['Drivers'] or 'FusionIO' in self.updateComponentProblemDict['Firmware']):
                self.logger.error('The FusionIO software update was skipped due to errors that were encountered during the FusionIO driver or firmware update.')
                self.updateComponentProblemDict['Software']['FusionIO'] = ''
                continue
            elif software == 'FusionIO':
                fusionIOSoftwarePkgList = updateSoftwareList.split()
                packageNames = ''
                for package in fusionIOSoftwarePkgList:
                    packageNames += re.sub('-[0-9]{1}.*', '', package) + ' '

                packageNames = packageNames.strip()
            if status[0] == 'timedOut':
                if software == 'FusionIO':
                    self.logger.info('Verifying the installation status of ' + packageNames + ', since it appears it may not of installed correctly.')
                    command = 'rpm -V --nomtime --nomode --nouser --nogroup ' + packageNames
                else:
                    self.logger.info('Verifying the installation status of ' + softwareName + ', since it appears it may not of installed correctly.')
                    command = 'rpm -V --nomtime --nomode --nouser --nogroup ' + softwareName
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if software == 'FusionIO':
                    self.logger.info('The output of the command (' + command + ') used to verify the installation status of ' + packageNames + '  was: ' + out.strip())
                else:
                    self.logger.info('The output of the command (' + command + ') used to verify the installation status of ' + softwareName + '  was: ' + out.strip())
                if result.returncode != 0:
                    if software == 'FusionIO':
                        self.logger.error('Problems were encountered while updating ' + packageNames + '.\n' + err)
                    else:
                        self.logger.error('Problems were encountered while updating ' + softwareName + '.\n' + err)
                    self.updateComponentProblemDict['Software'][softwareName] = ''
            elif status[0] != 'Succeeded':
                if software == 'FusionIO':
                    self.logger.error('Problems were encountered while updating ' + packageNames + '.\n' + err)
                else:
                    self.logger.error('Problems were encountered while updating ' + softwareName + '.\n' + status[1])
                self.updateComponentProblemDict['Software'][softwareName] = ''

        self.logger.info('Done updating the software that was identified as needing to be updated.')
        if 'rpmsToRemove' in self.csurResourceDict:
            if len(self.csurResourceDict['rpmsToRemove']) != 0:
                rpmsToRemove = self.csurResourceDict['rpmsToRemove']
                oneOffs = OneOffs()
                result, rpmRemovalList = oneOffs.removeRPMs(rpmsToRemove, self.computeNodeDict['loggerName'])
                if not result:
                    self.updateComponentProblemDict['Software']['rpmRemovalFailure'] = rpmRemovalList

    def __prepareForCS900SoftwareUpdate(self):
        softwareList = self.componentUpdateDict['Software']
        osDistLevel = self.computeNodeDict['osDistLevel']
        successfullyPrepared = True
        wbemSoftware = self.csurResourceDict['wbemSoftware']
        wbemSoftwareDict = dict.fromkeys([ x.strip() for x in wbemSoftware.split(',') ])
        self.logger.info('Preparing for a software update.')
        for software in softwareList:
            softwareName = re.match('(([a-zA-Z]+-*)+)', software).group(1).strip('-')
            if softwareName in wbemSoftwareDict:
                command = 'rpm -q --queryformat=%{release} ' + softwareName
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to check if ' + softwareName + ' was installed was: ' + out.strip())
                if result.returncode == 0:
                    revision, _ = out.strip().split('.')
                    self.logger.info('The revision of ' + softwareName + ' was determined to be: ' + revision)
                    if int(revision) <= 51:
                        if not self.__stopWBEMServices(osDistLevel):
                            successfullyPrepared = False
                            break
                        if not self.__removeWBEMSoftware(wbemSoftwareDict):
                            successfullyPrepared = False
                        break
                    elif 52 <= int(revision) <= 55:
                        if not self.__removeWBEMSoftware(['hpsmx-webapp']):
                            successfullyPrepared = False
                        break

        self.logger.info('Done preparing for a software update.')
        return successfullyPrepared

    def __removeWBEMSoftware(self, wbemSoftware):
        softwareToRemove = []
        softwareRemoved = True
        for software in wbemSoftware:
            command = 'rpm -q ' + software
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            self.logger.info('The output of the command (' + command + ') used to check if ' + software + ' was installed was: ' + out.strip())
            if result.returncode == 0:
                softwareToRemove.append(software)

        if len(softwareToRemove) > 0:
            command = 'rpm -e ' + ' '.join(softwareToRemove)
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            self.logger.info('The output of the command (' + command + ') used to remove ' + ' '.join(softwareToRemove) + ' was: ' + out.strip())
            if result.returncode != 0:
                self.logger.error('Problems were encountered while trying to remove ' + ' '.join(softwareToRemove) + ': ' + err)
                softwareRemoved = False
        return softwareRemoved

    def __stopWBEMServices(self, osDistLevel):
        sles11ServicesList = ['hpshd', 'sfcb', 'hpmgmtbase']
        sles12ServicesList = ['hpshd', 'sblim-sfcb', 'hpmgmtbase']
        rhelServicesList = ['hpshd', 'tog-pegasus', 'hpmgmtbase']
        servicesStopped = True
        if 'RHEL6' in osDistLevel:
            for service in rhelServicesList:
                command = 'service ' + service + ' stop'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to stop ' + service + ' was: ' + out.strip())
                command = 'service ' + service + ' status'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if 'running' in out:
                    self.logger.error('Problems were encountered while trying to stop ' + service + '.\n' + out)
                    servicesStopped = False
                    break

        elif 'RHEL7' in osDistLevel:
            for service in rhelServicesList:
                command = 'systemctl stop ' + service
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to stop ' + service + ' was: ' + out.strip())
                command = 'systemctl --quiet is-active ' + service
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode == 0:
                    self.logger.error('Problems were encountered while trying to stop ' + service + '.\n' + out)
                    servicesStopped = False
                    break

        elif 'SLES11' in osDistLevel:
            for service in sles11ServicesList:
                command = '/etc/init.d/' + service + ' stop'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to stop ' + service + ' was: ' + out.strip())
                command = '/etc/init.d/' + service + ' status'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if 'running' in out:
                    self.logger.error('Problems were encountered while trying to stop ' + service + '.\n' + out)
                    servicesStopped = False
                    break

        else:
            for service in sles12ServicesList:
                command = 'systemctl stop ' + service
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to stop ' + service + ' was: ' + out.strip())
                command = 'systemctl --quiet is-active ' + service
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode == 0:
                    self.logger.error('Problems were encountered while trying to stop ' + service + '.\n' + out)
                    servicesStopped = False
                    break

        return servicesStopped

    def __updateDrivers(self):
        driverDir = self.csurBasePath + '/drivers/computeNode/'
        driverDict = self.componentUpdateDict['Drivers']
        systemModel = self.computeNodeDict['systemModel']
        osDistLevel = self.computeNodeDict['osDistLevel']
        self.logger.info('Updating the drivers that were identified as needing to be updated.')
        for driver in driverDict:
            time.sleep(2)
            while self.wait:
                time.sleep(1)

            if self.cancel:
                return
            self.pid = 0
            if driver == 'nx_nic' and (systemModel == 'DL580G7' or systemModel == 'DL980G7'):
                command = 'rpm -qa|grep ^hpqlgc-nx'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to check if the new nx_nic driver is installed was: ' + out.strip())
                if result.returncode != 0:
                    command = 'rpm -e hp-nx_nic-kmp-default hp-nx_nic-tools'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    self.logger.info('The output of the command (' + command + ') used to remove the nx_nic driver was: ' + out.strip())
                    if result.returncode != 0:
                        self.logger.error('Problems were encountered while trying to remove hp-nx_nic-kmp-default and hp-nx_nic-tools; skipping update.\n' + err)
                        self.updateComponentProblemDict['Drivers'][driver] = ''
                        continue
            if driver == 'be2net':
                command = 'rpm -q hp-be2net-kmp-default'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to check if the old be2net driver is installed was: ' + out.strip())
                if result.returncode == 0:
                    command = 'rpm -e hp-be2net-kmp-default'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    self.logger.info('The output of the command (' + command + ') used to remove the be2net driver was: ' + out.strip())
                    if result.returncode != 0:
                        self.logger.error('Problems were encountered while trying to remove hp-be2net-kmp-default; skipping update.\n' + err)
                        self.updateComponentProblemDict['Drivers'][driver] = ''
                        continue
            if driver == 'mlx4_en':
                try:
                    if 'SLES' in osDistLevel:
                        packages = re.sub('\\s*,\\s*', ' ', self.csurResourceDict['slesMellanoxPackageList'])
                        mellanoxPackageList = packages.split(' ')
                    else:
                        packages = re.sub('\\s*,\\s*', ' ', self.csurResourceDict['rhelMellanoxPackageList'])
                        mellanoxPackageList = packages.split(' ')
                except KeyError as err:
                    self.logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
                    self.updateComponentProblemDict['Drivers'][driver] = ''
                    continue

                mellanoxRemovalList = []
                for package in mellanoxPackageList:
                    command = 'rpm -q ' + package + ' > /dev/null 2>&1'
                    result = subprocess.call(command, shell=True)
                    if result == 0:
                        mellanoxRemovalList.append(package)

                if len(mellanoxRemovalList) > 0:
                    packages = ' '.join(mellanoxRemovalList)
                    command = 'rpm -e ' + packages
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    self.logger.info('The output of the command (' + command + ') used to remove the Mellanox conflicting RPMs was: ' + out.strip())
                    if result.returncode != 0:
                        self.logger.error('Problems were encountered while trying to remove the Mellanox conflicting RPMs; skipping update.\n' + err)
                        self.updateComponentProblemDict['Drivers'][driver] = ''
                        continue
            if driver == 'iomemory_vsl':
                if self.__checkIOMemoryVSL():
                    self.updateComponentProblemDict['Drivers'][driver] = ''
                    continue
                if self.__unloadFusionIODriver():
                    self.updateComponentProblemDict['Drivers'][driver] = ''
                    continue
                dateTimestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                iomemoryCfgBackup = '/etc/sysconfig/iomemory-vsl.' + dateTimestamp
                try:
                    shutil.copy2('/etc/sysconfig/iomemory-vsl', iomemoryCfgBackup)
                except IOError as err:
                    self.logger.error("Unable to make a backup of the system's iomemory-vsl configuration file.\n" + str(err))
                    self.updateComponentProblemDict['Drivers'][driver] = ''

                if not removeFusionIOPackages(self.csurResourceDict['fusionIODriverRemovalPackageList'], 'driver', self.computeNodeDict['loggerName'], kernel=self.computeNodeDict['kernel']):
                    self.logger.error('The FusionIO driver packages could not be removed before building/re-installing the FusionIO driver; skipping update of FusionIO driver.')
                    self.updateComponentProblemDict['Drivers'][driver] = ''
                    continue
            if ':' not in driverDict[driver]:
                driverRPMList = driverDir + driverDict[driver]
            else:
                driverRPMsString = driverDict[driver]
                tmpDriverRPMList = driverRPMsString.replace(':', ' ' + driverDir)
                driverRPMList = driverDir + tmpDriverRPMList
            command = 'rpm -U --quiet --oldpackage --replacefiles --replacepkgs --nosignature ' + driverRPMList
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
            self.pid = result.pid
            out, err = result.communicate()
            self.logger.info('The output of the command (' + command + ") used to update the '" + driver + "' driver was: " + out.strip())
            if result.returncode != 0:
                self.logger.error("Problems were encountered while updating driver '" + driver + "'.\n" + err)
                self.updateComponentProblemDict['Drivers'][driver] = ''
                continue
            elif re.search('warning', out, re.MULTILINE | re.DOTALL | re.IGNORECASE) != None:
                self.logger.warn("Warnings were encountered while updating driver '" + driver + "'.\n" + out)
                self.updateComponentProblemDict['Drivers'][driver] = ''
            if driver == 'iomemory_vsl':
                self.fusionIODriverUpdateStarted = True
                if not self.fusionIODriverUpdate.buildInstallFusionIODriver(self.csurResourceDict.copy(), driverDir, self.computeNodeDict['loggerName']):
                    self.logger.error('Problems were encountered while building and installing the FusionIO driver.')
                    self.updateComponentProblemDict['Drivers'][driver] = ''
                self.fusionIODriverUpdateStarted = False
                try:
                    shutil.copy2(iomemoryCfgBackup, '/etc/sysconfig/iomemory-vsl')
                except IOError as err:
                    self.logger.error("Failed to restore the system's iomemory-vsl configuration file.\n" + str(err))
                    self.updateComponentProblemDict['Drivers'][driver] = ''

            if driver == 'mlx4_en' and ('SLES11.4' in osDistLevel or 'RHEL6.7' in osDistLevel) and len(self.computeNodeDict['mellanoxBusList']) != 0 and os.path.exists(self.connectXCfgFile):
                if not self.__updateConnectX():
                    self.updateComponentProblemDict['Drivers'][driver] = ''

        self.logger.info('Done updating the drivers that were identified as needing to be updated.')
        return

    def __updateFirmware(self):
        firmwareDir = self.csurBasePath + '/firmware/computeNode/'
        firmwareDict = self.componentUpdateDict['Firmware']
        osDistLevel = self.computeNodeDict['osDistLevel']
        biosReference = 'BIOSDL580Gen8'
        regex = '.*\\.scexe'
        nicRegex = 'em49|em50|em51|em52'
        self.logger.info('Updating the firmware that were identified as needing to be updated.')
        self.__bringUpNetworks()
        for firmware in firmwareDict:
            time.sleep(2)
            while self.wait:
                time.sleep(1)

            if self.cancel:
                return
            self.pid = 0
            if firmware == 'FusionIO' and 'iomemory_vsl' in self.updateComponentProblemDict['Drivers']:
                self.logger.error('The FusionIO firmware update was skipped due to errors that were encountered during the FusionIO driver update.')
                self.updateComponentProblemDict['Firmware'][firmware] = ''
                continue
            elif firmware == 'FusionIO':
                if self.__unloadFusionIODriver():
                    self.updateComponentProblemDict['Firmware'][firmware] = ''
                    continue
                firmwareImage = firmwareDir + firmwareDict[firmware]
                busList = self.computeNodeDict['busList']
                fusionIOFirmwareUpdateFailureList = []
                self.fusionIOFirmwareUpdateStarted = True
                for bus in busList:
                    self.fusionIOFirmwareUpdateThreadList.append(FusionIOFirmwareUpdate(bus, firmwareImage, fusionIOFirmwareUpdateFailureList, self.computeNodeDict['loggerName']))
                    self.fusionIOFirmwareUpdateThreadList[-1].start()

                while 1:
                    time.sleep(1.0)
                    for i in range(0, len(self.fusionIOFirmwareUpdateThreadList)):
                        if not self.fusionIOFirmwareUpdateThreadList[i].isAlive():
                            del self.fusionIOFirmwareUpdateThreadList[i]
                            break

                    if len(self.fusionIOFirmwareUpdateThreadList) == 0:
                        break

                if len(fusionIOFirmwareUpdateFailureList) > 0:
                    self.logger.error('Problems were encountered while updating the FusionIO firmware for the IODIMMS: ' + ' '.join(fusionIOFirmwareUpdateFailureList))
                    self.updateComponentProblemDict['Firmware'][firmware] = ''
                self.fusionIOFirmwareUpdateStarted = False
            elif re.match(regex, firmwareDict[firmware]):
                os.chdir(firmwareDir)
                command = './' + firmwareDict[firmware] + ' -f -s'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
                self.pid = result.pid
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to update the firmware ' + firmware + ' was: ' + out.strip())
                self.logger.info('The return code from the smart component update was: ' + str(result.returncode))
                if result.returncode == 3:
                    self.logger.error('Problems were encountered while updating firmware ' + firmware + '.\n' + err)
                    self.updateComponentProblemDict['Firmware'][firmware] = ''
                    continue
            else:
                rpm = firmwareDict[firmware]
                command = 'rpm -U --quiet --oldpackage --replacefiles --replacepkgs --nosignature ' + firmwareDir + rpm
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
                self.pid = result.pid
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to update the firmware ' + firmware + ' was: ' + out.strip())
                if result.returncode != 0:
                    self.logger.error('Problems were encountered while updating firmware ' + firmware + '.\n' + err)
                    self.updateComponentProblemDict['Firmware'][firmware] = ''
                    continue
                if rpm.endswith('x86_64.rpm'):
                    firmwareRPMDir = '/usr/lib/x86_64-linux-gnu/'
                    setupDir = firmwareRPMDir + rpm[0:rpm.index('.x86_64.rpm')]
                else:
                    firmwareRPMDir = '/usr/lib/i386-linux-gnu/'
                    setupDir = firmwareRPMDir + rpm[0:rpm.index('.i386.rpm')]
                os.chdir(setupDir)
                setupFile = setupDir + '/hpsetup'
                if os.path.isfile(setupFile):
                    if 'mellanox' in setupDir:
                        command = './hpsetup -s'
                    else:
                        command = './hpsetup -f -s'
                elif 'mellanox' in setupDir:
                    command = './.hpsetup -s'
                else:
                    command = './.hpsetup -f -s'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
                self.pid = result.pid
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to update the firmware ' + firmware + ' was: ' + out.strip())
                self.logger.info('The return code from the smart component update was: ' + str(result.returncode))
                if result.returncode == 3:
                    if re.search('All selected devices are either up-to-date or have newer versions installed', out, re.MULTILINE | re.DOTALL | re.IGNORECASE) == None:
                        self.logger.error('Problems were encountered while updating firmware ' + firmware + '.\n' + err)
                        self.updateComponentProblemDict['Firmware'][firmware] = ''
                        continue
                    else:
                        self.logger.info('A firmware update of ' + firmware + ' was not done due to the following reason: \n' + out)
            if firmware == biosReference and re.match('SLES.*', osDistLevel):
                command = 'ifconfig -a'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to get the list of NIC interfaces for checking if renaming is needed as a result of a bios update was: ' + out.strip())
                if result.returncode != 0:
                    self.logger.error('Problems were encountered while getting the list of NIC interfaces for checking if renaming is needed as a result of a bios update.\n' + err)
                    self.updateComponentProblemDict['Firmware'][biosReference] = 'Network name update failure.'
                elif re.search(nicRegex, out, re.MULTILINE | re.DOTALL) != None:
                    self.__updateNICConfiguration(biosReference)

        self.logger.info('Done updating the firmware that were identified as needing to be updated.')
        return

    def __bringUpNetworks(self):
        count = 1
        nicDownList = []
        command = 'ip link show'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to get the information for the NIC cards that are down was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Problems were encountered while getting the information for the NIC cards that are down.\n' + err)
            return
        else:
            nicDataList = out.splitlines()
            for data in nicDataList:
                if re.search('DOWN', data):
                    match = re.match('[0-9]{1,2}:\\s+(eth[0-9]{1,}|em[0-9]{1,}|(p[0-9]{1,}){2})', data)
                    if match != None:
                        nicDownList.append(match.group(1))

            for nic in nicDownList:
                command = 'ifconfig ' + nic + ' 10.1.1.' + str(count) + '/32  up'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to bring up NIC card ' + nic + ' was: ' + out.strip())
                if result.returncode != 0:
                    self.logger.error('Problems were encountered while bringing up NIC card ' + nic + '.\n' + err)
                count += 1

            return

    def __updateNICConfiguration(self, biosReference):
        emDict = {'em49': 'em0',
         'em50': 'em1',
         'em51': 'em2',
         'em52': 'em3'}
        regex = 'em49|em50|em51|em52'
        command = 'ls /etc/sysconfig/network/ifcfg-{bond*,em*}'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to get the list of network configuration files to update was: ' + out.strip())
        if result.returncode != 0:
            self.updateComponentProblemDict['Firmware'][biosReference] = 'Network configuration file update failure.'
            return
        else:
            out = out.splitlines()
            for file in out:
                try:
                    with open(file) as f:
                        nicData = f.read()
                except IOError as err:
                    self.logger.error('Problems were encountered while reading network configuration file ' + file + '.\n' + str(err))
                    self.updateComponentProblemDict['Firmware'][biosReference] = 'Network configuration file update failure.'
                    return

                if 'em' in file:
                    tmpList = file.split('-')
                    newFile = tmpList[0] + '-' + emDict[tmpList[1]]
                    command = 'mv ' + file + ' ' + newFile
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    if result.returncode != 0:
                        self.logger.error('Problems were encountered while updating (moving) the network configuration file ' + file + '.\n' + err)
                        self.updateComponentProblemDict['Firmware'][biosReference] = 'Network configuration file update failure.'
                        return
                    continue
                elif re.search(regex, nicData, re.MULTILINE | re.DOTALL) != None:
                    nicDataList = nicData.splitlines()
                    for em in emDict:
                        count = 0
                        for data in nicDataList:
                            if em in data:
                                data = re.sub(em, emDict[em], data)
                                nicDataList[count] = data
                            count += 1

                    try:
                        f = open(file, 'w')
                        f.write('\n'.join(nicDataList))
                    except IOError as err:
                        self.logger.error('Problems were encountered while writing out the updated network configuration file ' + file + '.\n' + str(err))
                        self.updateComponentProblemDict['Firmware'][biosReference] = 'Network configuration file update failure.'
                        return

                    f.close()

            return

    def endTask(self):
        self.logger.info('The CSUR update was cancelled by the user.')
        if self.fusionIODriverUpdateStarted:
            self.pid = self.fusionIODriverUpdate.getUpdatePID()
        if self.fusionIOFirmwareUpdateStarted:
            for i in range(0, len(self.fusionIOFirmwareUpdateThreadList)):
                pid = self.fusionIOFirmwareUpdateThreadList[i].getUpdatePID()
                try:
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, signal.SIGKILL)
                except OSError:
                    pass

        elif self.pid != 0:
            try:
                pgid = os.getpgid(self.pid)
                os.killpg(pgid, signal.SIGKILL)
            except OSError:
                pass

        self.cancel = True
        self.wait = False

    def getUpdateComponentProblemDict(self):
        return self.updateComponentProblemDict

    def __checkIOMemoryVSL(self):
        checkFailure = False
        fusionIOConfigurationFile = '/etc/sysconfig/iomemory-vsl'
        cmd = "egrep '^\\s*ENABLED=1' " + fusionIOConfigurationFile
        result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            if 'No such file' in err:
                self.logger.error('Problems were encountered while trying to update ' + fusionIOConfigurationFile + '.\n' + err)
                checkFailure = True
                return
            self.logger.info('Updating ' + fusionIOConfigurationFile + ', since it is not currently enabled for use by /etc/init.d/iomemory-vsl')
            cmd = "egrep 'ENABLED=' " + fusionIOConfigurationFile
            result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
            out, err = result.communicate()
            enabledCurrent = out.strip()
            self.logger.info('The output of the command ' + cmd + ' used to check ENABLED= in ' + fusionIOConfigurationFile + ' was:\n' + enabledCurrent)
            if len(enabledCurrent) != 0:
                cmd = "sed -i 's/" + enabledCurrent + "/ENABLED=1/' " + fusionIOConfigurationFile
            else:
                cmd = "sed -i '0,/^$/s/^$/ENABLED=1/' " + fusionIOConfigurationFile
            self.logger.info('The command used to update ' + fusionIOConfigurationFile + ' was: ' + cmd + '.')
            result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                self.logger.error('Problems were encountered while trying to update ' + fusionIOConfigurationFile + '.\n' + err)
                checkFailure = True

    def __unloadFusionIODriver(self):
        unloadFailure = False
        command = '/etc/init.d/iomemory-vsl status'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to check if the FusionIO driver is running was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Problems were detected while checking if the FusionIO driver is running:\n' + err)
            unloadFailure = True
        elif 'is running' in out:
            command = '/etc/init.d/iomemory-vsl stop'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
            out, err = result.communicate()
            self.logger.info('The output of the command (' + command + ') used to stop the FusionIO driver from running was: ' + out.strip())
            if result.returncode != 0:
                self.logger.error('Problems were detected while stopping the FusionIO driver:\n' + err)
                unloadFailure = True
        return unloadFailure

    def __updateConnectX(self):
        dateTimestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        connectXCfgBackup = self.connectXCfgFile + '.' + dateTimestamp
        try:
            shutil.move(self.connectXCfgFile, connectXCfgBackup)
        except IOError as err:
            print 'Unable to make a backup of ' + self.connectXCfgFile + '.'
            return False

        try:
            f = open(self.connectXCfgFile, 'w')
            for bus in self.computeNodeDict['mellanoxBusList']:
                f.write('connectx_port_config -d ' + bus + ' -c eth,eth\n')

        except IOError as err:
            print 'Unable to update ' + self.connectXCfgFile + ' with the Mellanox port configuration.'
            return False
        finally:
            f.close()

        return True