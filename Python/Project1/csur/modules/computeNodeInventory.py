# Embedded file name: ./computeNodeInventory.py
import re
import os
import subprocess
import logging

class ComputeNodeInventory():

    def __init__(self, computeNodeDict, noPMCFirmwareUpdateModels, computeNodeResources, **kwargs):
        self.systemModel = computeNodeDict['systemModel']
        self.osDistLevel = computeNodeDict['osDistLevel']
        self.noPMCFirmwareUpdateModels = noPMCFirmwareUpdateModels
        self.computeNodeResources = computeNodeResources
        if 'systemGeneration' in kwargs and self.systemModel == 'DL380pGen8' and kwargs['systemGeneration'] == 'Gen1.x':
            self.iLOFirmwareType = 'iLODL380pGen8'
        else:
            self.iLOFirmwareType = 'iLO'
        self.externalStoragePresent = False
        loggerName = computeNodeDict['loggerName']
        hostname = computeNodeDict['hostname']
        self.logger = logging.getLogger(loggerName)
        self.versionInformationLogger = logging.getLogger('versionInformationLog')
        self.versionInformationLogger.info('{0:40}'.format('Version information for Compute Node ' + hostname + ':') + '\n')
        self.inventoryError = False
        self.hardDriveFirmwareMissing = False
        self.hardDrivesMissingFirmware = []
        self.hbaPresent = False
        self.localStoragePresent = False
        self.firmwareDict = {}
        self.componentUpdateDict = {'Firmware': {},
         'Drivers': {},
         'Software': [],
         'sgSoftware': [],
         'sgNFSSoftware': []}
        self.mellanoxBusList = []
        self.notVersionMatchMessage = 'FAIL'
        self.versionMatchMessage = 'PASS'
        self.versionMatchWarningMessage = 'WARNING'

    def __getFirmwareDict(self):
        started = False
        self.logger.info('Getting the firmware dictionary.')
        for data in self.computeNodeResources:
            data = data.replace(' ', '')
            if not re.match('Firmware.*', data) and not started:
                continue
            elif re.match('Firmware.*', data):
                started = True
                continue
            elif re.match('\\s*$', data):
                break
            else:
                firmwareList = data.split('|')
                self.firmwareDict[firmwareList[0]] = [firmwareList[1], firmwareList[2]]

        self.logger.info('The firmware dictionary contents was determined to be: ' + str(self.firmwareDict) + '.')
        self.logger.info('Done getting the firmware dictionary.')

    def getComponentUpdateInventory(self, csurResourceDict):
        try:
            pciIdsFile = csurResourceDict['csurBasePath'] + '/resourceFiles/' + csurResourceDict['pciIdsFile']
            nicList = csurResourceDict['nicList']
            sgSoftwareList = csurResourceDict['sgSoftwareList']
            sgNFSSoftwareList = csurResourceDict['sgNFSSoftwareList']
            hbaDrivers = csurResourceDict['hbaDrivers']
            hbaSoftware = csurResourceDict['hbaSoftware']
            localStorageDrivers = csurResourceDict['localStorageDrivers']
            localStorageSoftware = csurResourceDict['localStorageSoftware']
        except KeyError as err:
            logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
            self.inventoryError = True
            return

        componentHeader = 'Component'
        componentUnderLine = '---------'
        csurVersionHeader = 'CSUR Version'
        csurVersionUnderLine = '------------'
        currentVersionHeader = 'Current Version'
        currentVersionUnderLine = '---------------'
        statusHeader = 'Status'
        statusUnderLine = '------'
        self.__getFirmwareDict()
        self.versionInformationLogger.info('{0:40}'.format('Firmware Versions:') + '\n')
        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentHeader, csurVersionHeader, currentVersionHeader, statusHeader))
        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentUnderLine, csurVersionUnderLine, currentVersionUnderLine, statusUnderLine))
        if self.systemModel != '16sx86':
            if self.__getLocalStorage() == 'Present':
                self.__getStorageFirmwareInventory()
        self.__getNICFirmwareInventory(pciIdsFile, nicList)
        self.__getCommonFirmwareInventory()
        self._getComputeNodeSpecificFirmwareInventory()
        if self.systemModel != '16sx86':
            self.versionInformationLogger.info('\n' + '{0:40}'.format('Driver Versions:') + '\n')
            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentHeader, csurVersionHeader, currentVersionHeader, statusHeader))
            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentUnderLine, csurVersionUnderLine, currentVersionUnderLine, statusUnderLine))
            self.__getDriverInventory(hbaDrivers, localStorageDrivers)
            self._getComputeNodeSpecificDriverInventory()
        self.versionInformationLogger.info('\n' + '{0:40}'.format('Software Versions:') + '\n')
        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentHeader, csurVersionHeader, currentVersionHeader, statusHeader))
        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentUnderLine, csurVersionUnderLine, currentVersionUnderLine, statusUnderLine))
        self.__getSoftwareInventory(sgSoftwareList, sgNFSSoftwareList, hbaSoftware, localStorageSoftware)
        self._getComputeNodeSpecificSoftwareInventory()

    def getLocalHardDriveFirmwareInventory(self):
        hardDrivesLocal = None
        if self.__getLocalStorage() == 'Present':
            self.__getFirmwareDict()
            hardDrivesLocal = True
            self.__getLocalOSHardDriveFirmwareInventory()
        elif self.__getLocalStorage() == 'Absent':
            hardDrivesLocal = False
        return hardDrivesLocal

    def __getStorageFirmwareInventory(self):
        self.logger.info('Getting the storage firmware inventory.')
        if os.path.isfile('/usr/sbin/ssacli'):
            arrayCfgUtilFile = '/usr/sbin/ssacli'
        elif os.path.isfile('/usr/sbin/hpssacli'):
            arrayCfgUtilFile = '/usr/sbin/hpssacli'
        elif os.path.isfile('/usr/sbin/hpacucli'):
            arrayCfgUtilFile = '/usr/sbin/hpacucli'
        else:
            self.logger.error('There is no Smart Storage Administration software installed.\n')
            self.inventoryError = True
            return
        command = arrayCfgUtilFile + ' ctrl all show'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to get the list of storage controllers was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Failed to get the list of storage controllers.\n' + err)
            self.inventoryError = True
            return
        controllerList = re.findall('P\\d{3}i*\\s+in\\s+Slot\\s+\\d{1}', out, re.MULTILINE | re.DOTALL)
        self.logger.info('The controller list was determined to be: ' + str(controllerList) + '.')
        hardDriveList = []
        for controller in controllerList:
            controllerModel = controller.split()[0]
            controllerSlot = controller.split()[-1]
            csurControllerFirmwareVersion = self.firmwareDict[controllerModel][0]
            command = arrayCfgUtilFile + ' ctrl slot=' + controllerSlot + ' show'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            self.logger.info('The output of the command (' + command + ') used to get the storage controllers firmware version was: ' + out.strip())
            if result.returncode != 0:
                self.logger.error('Failed to get the list of storage controllers.\n' + err)
                self.inventoryError = True
                return
            installedControllerFirmwareVersion = re.match('.*Firmware Version:\\s+(\\d+\\.\\d+).*', out, re.MULTILINE | re.DOTALL).group(1)
            self.logger.info("The controller's firmware version was determined to be: " + installedControllerFirmwareVersion + '.')
            if installedControllerFirmwareVersion != csurControllerFirmwareVersion and self.firmwareDict[controllerModel][1] != 'None':
                self.componentUpdateDict['Firmware'][controllerModel] = self.firmwareDict[controllerModel][1]
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(controllerModel, csurControllerFirmwareVersion, installedControllerFirmwareVersion, self.notVersionMatchMessage))
            else:
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(controllerModel, csurControllerFirmwareVersion, installedControllerFirmwareVersion, self.versionMatchMessage))
            if controllerModel == 'P812' or controllerModel == 'P431':
                if self.systemModel != 'DL580Gen9':
                    csurEnclosureFirmwareVersion = self.firmwareDict['D2700'][0]
                    enclosure = 'D2700'
                else:
                    csurEnclosureFirmwareVersion = self.firmwareDict['D3700'][0]
                    enclosure = 'D3700'
                self.externalStoragePresent = True
                command = arrayCfgUtilFile + ' ctrl slot=' + controllerSlot + ' enclosure all show detail'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to get the storage controllers enclosure firmware version was: ' + out.strip())
                if result.returncode != 0:
                    self.logger.error("Failed to get the storage contoller's details.\n" + err)
                    self.inventoryError = True
                    return
                installedEnclosureFirmwareVersion = re.match('.*Firmware Version:\\s+(\\d+\\.\\d+|\\d+).*', out, re.MULTILINE | re.DOTALL).group(1)
                self.logger.info("The controller's enclosure firmware version was determined to be: " + installedEnclosureFirmwareVersion + '.')
                if installedEnclosureFirmwareVersion != csurEnclosureFirmwareVersion and self.firmwareDict[enclosure][1] != 'None':
                    self.componentUpdateDict['Firmware'][enclosure] = self.firmwareDict[enclosure][1]
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(enclosure, csurEnclosureFirmwareVersion, installedEnclosureFirmwareVersion, self.notVersionMatchMessage))
                else:
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(enclosure, csurEnclosureFirmwareVersion, installedEnclosureFirmwareVersion, self.versionMatchMessage))
            command = arrayCfgUtilFile + ' ctrl slot=' + controllerSlot + ' pd all show detail'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            self.logger.info('The output of the command (' + command + ') used to get the hard drive list and their firmware version was: ' + out.strip())
            if result.returncode != 0:
                self.logger.error('Failed to get hard drive versions.\n' + err)
                self.inventoryError = True
                return
            hardDriveDataList = re.findall('Firmware\\s+Revision:\\s+[0-9A-Z]{4}\\s+Serial\\s+Number:\\s+[0-9A-Z]+\\s+WWID:\\s+[0-9A-F]+\\s+Model:\\s+HP\\s+[0-9A-Z]+|Firmware\\s+Revision:\\s+[0-9A-Z]{4}\\s+Serial\\s+Number:\\s+[0-9A-Z]+\\s+Model:\\s+HP\\s+[0-9A-Z]+', out, re.MULTILINE | re.DOTALL)
            self.logger.info('The hard drive data list was determined to be: ' + str(hardDriveDataList) + '.')
            for hardDrive in hardDriveDataList:
                hardDriveData = hardDrive.split()
                hardDriveVersion = hardDriveData[-1] + ' ' + hardDriveData[2]
                hardDriveList.append(hardDriveVersion)

        hardDriveList.sort()
        self.logger.info('The hard drive list was determined to be: ' + str(hardDriveList) + '.')
        hardDriveModels = []
        count = 0
        for hd in hardDriveList:
            hardDriveData = hd.split()
            if count == 0:
                hardDriveModels.append(hardDriveData[0])
                tmpHardDriveModel = hardDriveData[0]
                count += 1
            elif hardDriveData[0] != tmpHardDriveModel:
                hardDriveModels.append(hardDriveData[0])
                tmpHardDriveModel = hardDriveData[0]

        self.logger.info('The hard drive models were determined to be: ' + str(hardDriveModels))
        for hardDriveModel in hardDriveModels:
            hardDriveVersionMismatch = False
            try:
                csurHardDriveFirmwareVersion = self.firmwareDict[hardDriveModel][0]
            except KeyError:
                self.logger.error('Firmware for the hard drive model ' + hardDriveModel + ' is missing from the csur bundle.')
                self.hardDriveFirmwareMissing = True
                self.hardDrivesMissingFirmware.append(hardDriveModel)
                continue

            for hd in hardDriveList:
                hardDriveData = hd.split()
                if hardDriveData[0] == hardDriveModel:
                    installedHardDriveFirmwareVersion = hardDriveData[1]
                    self.logger.info("The hard drive's firmware version was determined to be: " + installedHardDriveFirmwareVersion + '.')
                    if installedHardDriveFirmwareVersion != csurHardDriveFirmwareVersion and self.firmwareDict[hardDriveModel][1] != 'None':
                        self.componentUpdateDict['Firmware'][hardDriveModel] = self.firmwareDict[hardDriveModel][1]
                        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(hardDriveModel, csurHardDriveFirmwareVersion, installedHardDriveFirmwareVersion, self.notVersionMatchMessage))
                        hardDriveVersionMismatch = True
                        break

            if not hardDriveVersionMismatch:
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(hardDriveModel, csurHardDriveFirmwareVersion, installedHardDriveFirmwareVersion, self.versionMatchMessage))

        self.logger.info('Done getting the storage firmware inventory.')

    def __getLocalOSHardDriveFirmwareInventory(self):
        self.logger.info('Getting the local OS hard drive firmware inventory.')
        if os.path.isfile('/usr/sbin/ssacli'):
            arrayCfgUtilFile = '/usr/sbin/ssacli'
        elif os.path.isfile('/usr/sbin/hpssacli'):
            arrayCfgUtilFile = '/usr/sbin/hpssacli'
        elif os.path.isfile('/usr/sbin/hpacucli'):
            arrayCfgUtilFile = '/usr/sbin/hpacucli'
        else:
            self.logger.error('There is no Smart Storage Administration software installed.\n' + err)
            self.inventoryError = True
            return
        command = arrayCfgUtilFile + ' ctrl all show'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to get the list of attached storage controllers was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Failed to get the list of attached storage controllers.\n' + err)
            self.inventoryError = True
            return
        if re.match('\\s*Smart\\s+Array\\s+P\\d{3}i\\s+in\\s+Slot\\s+\\d{1}', out, re.MULTILINE | re.DOTALL):
            controllerModel = re.match('\\s*Smart\\s+Array\\s+(P\\d{3}i)\\s+in\\s+Slot\\s+\\d{1}', out, re.MULTILINE | re.DOTALL).group(1)
            controllerSlot = re.match('\\s*Smart\\s+Array\\s+P\\d{3}i\\s+in\\s+Slot\\s+(\\d{1})', out, re.MULTILINE | re.DOTALL).group(1)
        else:
            self.logger.error("Failed to get the internal storage controller's information.")
            self.inventoryError = True
            return
        self.logger.info('The controller was determined to be: ' + controllerModel + ' in slot ' + controllerSlot + '.')
        hardDriveList = []
        command = arrayCfgUtilFile + ' ctrl slot=' + controllerSlot + ' pd all show detail'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to get the hard drive list and their firmware version was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Failed to get hard drive versions.\n' + err)
            self.inventoryError = True
            return
        hardDriveDataList = re.findall('Firmware\\s+Revision:\\s+[0-9A-Z]{4}\\s+Serial\\s+Number:\\s+[0-9A-Z]+\\s+WWID:\\s+[0-9A-F]+\\s+Model:\\s+HP\\s+[0-9A-Z]+|Firmware\\s+Revision:\\s+[0-9A-Z]{4}\\s+Serial\\s+Number:\\s+[0-9A-Z]+\\s+Model:\\s+HP\\s+[0-9A-Z]+', out, re.MULTILINE | re.DOTALL)
        self.logger.info('The hard drive data list was determined to be: ' + str(hardDriveDataList) + '.')
        for hardDrive in hardDriveDataList:
            hardDriveData = hardDrive.split()
            hardDriveVersion = hardDriveData[-1] + ' ' + hardDriveData[2]
            hardDriveList.append(hardDriveVersion)

        hardDriveList.sort()
        self.logger.info('The hard drive list was determined to be: ' + str(hardDriveList) + '.')
        hardDriveModels = []
        count = 0
        for hd in hardDriveList:
            hardDriveData = hd.split()
            if count == 0:
                hardDriveModels.append(hardDriveData[0])
                tmpHardDriveModel = hardDriveData[0]
                count += 1
            elif hardDriveData[0] != tmpHardDriveModel:
                hardDriveModels.append(hardDriveData[0])
                tmpHardDriveModel = hardDriveData[0]

        self.logger.info('The hard drive models were determined to be: ' + str(hardDriveModels))
        for hardDriveModel in hardDriveModels:
            hardDriveVersionMismatch = False
            try:
                csurHardDriveFirmwareVersion = self.firmwareDict[hardDriveModel][0]
            except KeyError:
                self.logger.error('Firmware for the hard drive model ' + hardDriveModel + ' is missing from the csur bundle.')
                self.hardDriveFirmwareMissing = True
                self.hardDrivesMissingFirmware.append(hardDriveModel)
                break

            for hd in hardDriveList:
                hardDriveData = hd.split()
                if hardDriveData[0] == hardDriveModel:
                    installedHardDriveFirmwareVersion = hardDriveData[1]
                    self.logger.info("The hard drive's firmware version was determined to be: " + installedHardDriveFirmwareVersion + '.')
                    if installedHardDriveFirmwareVersion != csurHardDriveFirmwareVersion and self.firmwareDict[hardDriveModel][1] != 'None':
                        self.componentUpdateDict['Firmware'][hardDriveModel] = self.firmwareDict[hardDriveModel][1]
                        hardDriveVersionMismatch = True
                        break

        self.logger.info('Done getting the local OS hard drive firmware inventory.')

    def __getNICFirmwareInventory(self, pciIdsFile, nicList):
        nicCardModels = []
        count = 0
        self.logger.info('Getting the NIC card firmware inventory.')
        nicBusList = self.__getNicBusList(pciIdsFile, nicList)
        if nicBusList == 'NICBusFailure':
            return
        for nd in nicBusList:
            nicCardData = nd.split()
            if count == 0:
                nicCardModels.append(nicCardData[1])
                tmpNicCardModel = nicCardData[1]
                count += 1
            elif nicCardData[1] != tmpNicCardModel:
                nicCardModels.append(nicCardData[1])
                tmpNicCardModel = nicCardData[1]

        self.logger.info('The NIC card models were determined to be: ' + str(nicCardModels) + '.')
        command = 'ifconfig -a'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to get the NIC card list was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error("Failed to get the Compute Node's NIC card list.\n" + err)
            self.inventoryError = True
            return
        nicCardList = re.findall('^[empth0-9]{3,}', out, re.MULTILINE | re.DOTALL)
        self.logger.info('The NIC card list was determined to be: ' + str(nicCardList) + '.')
        for nicCardModel in nicCardModels:
            nicCardVersionMismatch = False
            nicCardFoundError = False
            count = 0
            try:
                csurNicCardFirmwareVersion = self.firmwareDict[nicCardModel][0]
            except KeyError:
                self.logger.error('Firmware for the NIC card model ' + nicCardModel + ' is missing from the csur bundle.')
                self.inventoryError = True
                continue

            for data in nicBusList:
                found = False
                nicCardData = data.split()
                nicBus = nicCardData[0]
                installedNicCardModel = nicCardData[1]
                if installedNicCardModel == nicCardModel:
                    for nic in nicCardList:
                        command = 'ethtool -i ' + nic
                        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        out, err = result.communicate()
                        self.logger.info('The output of the command (' + command + ') used to check the NIC card firmware was: ' + out.strip())
                        if result.returncode != 0:
                            self.logger.error('Failed to get the NIC card information for (' + nic + ').\n' + err)
                            self.inventoryError = True
                            continue
                        if nicBus in out:
                            nicDevice = nic
                            found = True
                        else:
                            continue
                        versionList = out.splitlines()
                        for line in versionList:
                            if 'firmware-version' in line:
                                firmwareList = line.split()
                                if '5719-v' in line or '5720-v' in line:
                                    installedNicCardFirmwareVersion = re.match('\\d{4}-(.*)', firmwareList[1]).group(1)
                                else:
                                    installedNicCardFirmwareVersion = firmwareList[-1]

                        self.logger.info('The NIC card firmware version was determined to be: ' + str(installedNicCardFirmwareVersion) + '.')
                        if installedNicCardFirmwareVersion != csurNicCardFirmwareVersion and count == 0:
                            if self.firmwareDict[nicCardModel][1] != 'None':
                                self.componentUpdateDict['Firmware'][nicCardModel] = self.firmwareDict[nicCardModel][1]
                                nicCardVersionMismatch = True
                                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(nicCardModel, csurNicCardFirmwareVersion, installedNicCardFirmwareVersion, self.notVersionMatchMessage))
                            count += 1
                        break

                    if not found:
                        self.logger.error('The NIC card (' + data + ') was not found (ifconfig -a), thus there is some sort of NIC card issue that needs to be resolved.')
                        self.inventoryError = True
                        nicCardFoundError = True
                else:
                    continue
                if count == 1:
                    break

            if not nicCardVersionMismatch and not nicCardFoundError:
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(nicCardModel, csurNicCardFirmwareVersion, installedNicCardFirmwareVersion, self.versionMatchMessage))

        self.logger.info('Done getting the NIC card firmware inventory.')

    def __getNicBusList(self, pciIdsFile, nicList):
        nicBusList = []
        busDict = {}
        self.logger.info('Getting the NIC bus list.')
        command = 'lspci -i ' + pciIdsFile + ' -mvv'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            self.logger.error("Failed to get the Compute Node's NIC bus list.\n" + err)
            self.inventoryError = True
            return 'NICBusFailure'
        self.logger.info('The output of the command (' + command + ') used to get the NIC card bus information was: ' + out.strip())
        out = re.sub('\n{2,}', '####', out)
        deviceList = out.split('####')
        for device in deviceList:
            if 'Ethernet controller' in device or 'Network controller' in device:
                bus = re.match('\\s*[a-zA-Z]+:\\s+([0-9a-f]{2}:[0-9a-f]{2}\\.[0-9]).*(' + nicList + ')\\s+Adapter.*', device, re.MULTILINE | re.DOTALL)
                try:
                    if not bus:
                        self.logger.error('A match error was encountered while getting nic bus information for device: ' + device[0:200])
                        self.inventoryError = True
                        continue
                    self.logger.info('The bus information for device:\n' + device[0:100] + '\nwas determined to be: ' + bus.group(1) + '.\n')
                    busPrefix = bus.group(1)[:-2]
                    if busPrefix not in busDict:
                        busDict[busPrefix] = ''
                        nicBusList.append(bus.group(1) + ' ' + bus.group(2))
                        if 'Mellanox' in device:
                            self.mellanoxBusList.append(bus.group(1))
                except AttributeError as err:
                    self.logger.error('An AttributeError was encountered while getting nic bus information: ' + str(err) + '\n' + device[0:200])
                    self.inventoryError = True
                    continue

        nicBusList.sort(key=lambda n: n.split()[1])
        self.logger.info('The NIC card bus list was determined to be: ' + str(nicBusList) + '.')
        self.logger.info('Done getting the NIC bus list.')
        return nicBusList

    def __getCommonFirmwareInventory(self):
        biosFirmwareType = 'BIOS' + self.systemModel
        self.logger.info('Getting the compute node common firmware inventory.')
        if self.systemModel != '16sx86':
            command = 'dmidecode -s bios-release-date'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            self.logger.info('The output of the command (' + command + ") used to get the compute node's BIOS information was: " + out.strip())
            if result.returncode != 0:
                self.logger.error("Failed to get the compute node's BIOS firmware version.\n" + err)
                self.inventoryError = True
            else:
                biosFirmwareDate = out.strip()
                biosFirmwareDateList = biosFirmwareDate.split('/')
                installedBiosFirmwareVersion = biosFirmwareDateList[2] + '.' + biosFirmwareDateList[0] + '.' + biosFirmwareDateList[1]
                self.logger.info("The compute node's bios version was determined to be: " + installedBiosFirmwareVersion + '.')
                csurBiosFirmwareVersion = self.firmwareDict[biosFirmwareType][0]
                if installedBiosFirmwareVersion != csurBiosFirmwareVersion and self.firmwareDict[biosFirmwareType][1] != 'None':
                    self.componentUpdateDict['Firmware'][biosFirmwareType] = self.firmwareDict[biosFirmwareType][1]
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('BIOS', csurBiosFirmwareVersion, installedBiosFirmwareVersion, self.notVersionMatchMessage))
                else:
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('BIOS', csurBiosFirmwareVersion, installedBiosFirmwareVersion, self.versionMatchMessage))
            command = 'hponcfg -g'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            self.logger.info('The output of the command (' + command + ") used to get the compute node's iLO information was: " + out.strip())
            if result.returncode != 0:
                self.logger.error("Failed to get the Compute Node's iLO firmware version.\n" + err)
                self.inventoryError = True
            else:
                installedILOFirmwareVersion = re.match('.*Firmware Revision\\s+=\\s+(\\d+\\.\\d+).*', out, re.MULTILINE | re.DOTALL).group(1)
                self.logger.info("The compute node's iLO version was determined to be: " + installedILOFirmwareVersion + '.')
                csurILOFirmwareVersion = self.firmwareDict[self.iLOFirmwareType][0]
                if installedILOFirmwareVersion != csurILOFirmwareVersion and self.firmwareDict[self.iLOFirmwareType][1] != 'None':
                    self.componentUpdateDict['Firmware']['iLO'] = self.firmwareDict[self.iLOFirmwareType][1]
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('iLO', csurILOFirmwareVersion, installedILOFirmwareVersion, self.notVersionMatchMessage))
                else:
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('iLO', csurILOFirmwareVersion, installedILOFirmwareVersion, self.versionMatchMessage))
        command = 'systool -c scsi_host -v'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ") used to get the compute node's HBA information was: " + out.strip())
        if result.returncode != 0:
            self.logger.error("Failed to get compute node's HBA information.\n" + err)
            self.inventoryError = True
        elif re.search('HBA', out, re.MULTILINE | re.DOTALL) != None:
            hostList = out.split('Device = "')
            if not self.hbaPresent:
                self.hbaPresent = True
            previousSerialNumber = ''
            hbaResultDict = {}
            for host in hostList:
                if re.search('HBA', host, re.MULTILINE | re.DOTALL) != None:
                    currentSerialNumber = ''
                    installedHBAFirmwareVersion = ''
                    hbaModel = ''
                    hostDataList = host.splitlines()
                    for data in hostDataList:
                        if re.match('\\s*optrom_fw_version', data) != None:
                            installedHBAFirmwareVersion = re.match('\\s*optrom_fw_version\\s+=\\s+"([0-9.]+)\\s+', data).group(1)
                            self.logger.info("The HBA's firmware version was determined to be: " + installedHBAFirmwareVersion + '.')
                        if re.match('\\s*model_name', data) != None:
                            hbaModel = re.match('\\s*model_name\\s+=\\s+"(.*)"', data).group(1)
                            self.logger.info("The HBA's model was determined to be: " + hbaModel + '.')
                        if re.match('\\s*serial_num', data) != None:
                            currentSerialNumber = re.match('\\s*serial_num\\s+=\\s+"(.*)"', data).group(1)
                            self.logger.info("The HBA's serial number was determined to be: " + currentSerialNumber + '.')
                            if currentSerialNumber != previousSerialNumber:
                                previousSerialNumber = currentSerialNumber
                            else:
                                break
                        if installedHBAFirmwareVersion != '' and hbaModel != '' and currentSerialNumber != '':
                            try:
                                csurHBAFirmwareVersion = self.firmwareDict[hbaModel][0]
                            except KeyError:
                                self.logger.error('Firmware for the HBA model ' + hbaModel + ' is missing from the csur bundle.')
                                self.inventoryError = True
                                break

                            if installedHBAFirmwareVersion != csurHBAFirmwareVersion and self.firmwareDict[hbaModel][1] != 'None':
                                if hbaModel not in self.componentUpdateDict['Firmware']:
                                    self.componentUpdateDict['Firmware'][hbaModel] = self.firmwareDict[hbaModel][1]
                                if hbaModel not in hbaResultDict or hbaResultDict[hbaModel][2]:
                                    hbaResultDict[hbaModel] = [csurHBAFirmwareVersion, installedHBAFirmwareVersion, False]
                            elif hbaModel not in hbaResultDict:
                                hbaResultDict[hbaModel] = [csurHBAFirmwareVersion, installedHBAFirmwareVersion, True]
                            break

            for hbaModel in hbaResultDict:
                if not hbaResultDict[hbaModel][2]:
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(hbaModel, hbaResultDict[hbaModel][0], hbaResultDict[hbaModel][1], self.notVersionMatchMessage))
                else:
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(hbaModel, hbaResultDict[hbaModel][0], hbaResultDict[hbaModel][1], self.versionMatchMessage))

        if self.systemModel not in self.noPMCFirmwareUpdateModels:
            installedPMCFirmwareVersion = ''
            command = 'dmidecode'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            self.logger.info('The output of the command (' + command + ") used to get the compute node's dmidecode information was: " + out.strip())
            if result.returncode != 0:
                self.logger.error("Failed to get compute node's dmidecode information needed to determine the Power Management Contoller's firmware version.\n" + err)
                self.inventoryError = True
            else:
                dmidecodeList = out.splitlines()
                found = False
                for data in dmidecodeList:
                    if not found and re.match('^\\s*Power Management Controller Firmware\\s*$', data) != None:
                        found = True
                        continue
                    elif found:
                        installedPMCFirmwareVersion = data.strip()
                        self.logger.info("The Power Management Controller's firmware version was determined to be: " + installedPMCFirmwareVersion + '.')
                        break
                    else:
                        continue

                if installedPMCFirmwareVersion != '':
                    pmcCSURReference = 'PMC' + self.systemModel
                    try:
                        csurPMCFirmwareVersion = self.firmwareDict[pmcCSURReference][0]
                    except KeyError:
                        self.logger.error('Firmware for the Power Management Controller is missing from the csur bundle.')
                        self.inventoryError = True
                    else:
                        if installedPMCFirmwareVersion != csurPMCFirmwareVersion and self.firmwareDict[pmcCSURReference][1] != 'None':
                            self.componentUpdateDict['Firmware'][pmcCSURReference] = self.firmwareDict[pmcCSURReference][1]
                            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('PMC', csurPMCFirmwareVersion, installedPMCFirmwareVersion, self.notVersionMatchMessage))
                        else:
                            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('PMC', csurPMCFirmwareVersion, installedPMCFirmwareVersion, self.versionMatchMessage))
                else:
                    self.logger.error("The Power Management Controller's firmware version was not found in the output of dmidecode.")
                    self.inventoryError = True
        self.logger.info('Done getting the compute node common firmware inventory.')
        return

    def __getDriverInventory(self, hbaDrivers, localStorageDrivers):
        started = False
        driversFound = False
        updateDriverList = []
        hbaDriverDict = dict.fromkeys([ x.strip() for x in hbaDrivers.split(',') ])
        localStorageDriverDict = dict.fromkeys([ x.strip() for x in localStorageDrivers.split(',') ])
        mlnxCount = 0
        self.logger.info('Getting the driver inventory.')
        for data in self.computeNodeResources:
            data = data.replace(' ', '')
            if 'Drivers' not in data and not driversFound:
                continue
            elif 'Drivers' in data:
                driversFound = True
                continue
            elif self.osDistLevel in data and not self.systemModel in data and not started:
                continue
            elif self.osDistLevel in data and self.systemModel in data:
                started = True
                continue
            elif re.match('\\s*$', data):
                break
            else:
                csurDriverList = data.split('|')
                csurDriver = csurDriverList[0]
                csurDriverVersion = csurDriverList[1]
                if not self.hbaPresent and csurDriver in hbaDriverDict:
                    continue
                if not self.localStoragePresent and csurDriver in localStorageDriverDict:
                    continue
                command = 'modinfo ' + csurDriver
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to get the driver information was: ' + out.strip())
                if result.returncode != 0:
                    if (csurDriver == 'mlx4_en' or csurDriver == 'mlnx') and mlnxCount == 0:
                        self.logger.warn('The first Mellanox driver checked (' + csurDriver + ') appears not to be the driver being used.\n' + err)
                        mlnxCount += 1
                        continue
                    else:
                        self.logger.error("Failed to get the Compute Node's driver version for driver " + csurDriver + '.\n' + err)
                        self.inventoryError = True
                driverDataList = out.splitlines()
                for data in driverDataList:
                    if re.match('version:\\s+.*', data) != None:
                        versionList = data.split()
                        installedDriverVersion = versionList[1]
                        break

                self.logger.info('The driver version was determined to be: ' + installedDriverVersion + '.')
                if installedDriverVersion != csurDriverVersion and csurDriverList[2] != 'None':
                    self.componentUpdateDict['Drivers'][csurDriver] = csurDriverList[2]
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurDriver, csurDriverVersion, installedDriverVersion, self.notVersionMatchMessage))
                else:
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurDriver, csurDriverVersion, installedDriverVersion, self.versionMatchMessage))

        self.logger.info('Done getting the driver inventory.')
        return

    def __getSoftwareInventory(self, sgSoftwareList, sgNFSSoftwareList, hbaSoftware, localStorageSoftware):
        started = False
        softwareFound = False
        updateSoftwareList = []
        sgSoftwareDict = dict.fromkeys([ x.strip() for x in sgSoftwareList.split(',') ])
        sgNFSSoftwareDict = dict.fromkeys([ x.strip() for x in sgNFSSoftwareList.split(',') ])
        hbaSoftwareDict = dict.fromkeys([ x.strip() for x in hbaSoftware.split(',') ])
        localStorageSoftwareDict = dict.fromkeys([ x.strip() for x in localStorageSoftware.split(',') ])
        self.logger.info('Getting the software inventory.')
        for data in self.computeNodeResources:
            data = data.replace(' ', '')
            if 'Software' not in data and not softwareFound:
                continue
            elif 'Software' in data:
                softwareFound = True
                continue
            elif self.osDistLevel in data and not self.systemModel in data and not started:
                continue
            elif self.osDistLevel in data and self.systemModel in data:
                started = True
                continue
            elif re.match('\\s*$', data):
                break
            else:
                csurSoftwareList = data.split('|')
                csurSoftware = csurSoftwareList[0]
                csurSoftwareEpoch = csurSoftwareList[1]
                csurSoftwareVersion = csurSoftwareList[2]
                if not self.hbaPresent and csurSoftware in hbaSoftwareDict:
                    continue
                if not self.localStoragePresent and csurSoftware in localStorageSoftwareDict:
                    continue
                if self.systemModel != 'DL380pGen8':
                    if self.systemModel != 'DL360pGen8' and 'serviceguard' in csurSoftware:
                        continue
                    command = "rpm -q --queryformat=%{buildtime}':'%{version}'-'%{release} " + csurSoftware
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    self.logger.info('The output of the command (' + command + ') used to get the software epoch and version information was: ' + out.strip())
                    if result.returncode != 0:
                        if 'is not installed' in out:
                            if csurSoftware in sgNFSSoftwareDict:
                                self.componentUpdateDict['sgNFSSoftware'].append(csurSoftwareList[3])
                            elif csurSoftware in sgSoftwareDict:
                                self.componentUpdateDict['sgSoftware'].append(csurSoftwareList[3])
                            else:
                                self.componentUpdateDict['Software'].append(csurSoftwareList[3])
                            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurSoftware, csurSoftwareVersion, 'Not Installed', self.versionMatchWarningMessage))
                            continue
                        else:
                            self.logger.error("Failed to get the Compute Node's software version for software " + csurSoftware + '.\n' + err)
                            self.inventoryError = True
                            continue
                    rpmInformationList = out.strip().split(':')
                    installedSoftwareEpoch = rpmInformationList[0]
                    installedSoftwareVersion = rpmInformationList[1]
                    self.logger.info('The software epoch date was determined to be: ' + installedSoftwareEpoch + '.')
                    if installedSoftwareEpoch != csurSoftwareEpoch and csurSoftwareList[3] != 'None':
                        csurSoftware in sgNFSSoftwareDict and self.componentUpdateDict['sgNFSSoftware'].append(csurSoftwareList[3])
                    elif csurSoftware in sgSoftwareDict:
                        self.componentUpdateDict['sgSoftware'].append(csurSoftwareList[3])
                    else:
                        self.componentUpdateDict['Software'].append(csurSoftwareList[3])
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurSoftware, csurSoftwareVersion, installedSoftwareVersion, self.notVersionMatchMessage))
                else:
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurSoftware, csurSoftwareVersion, installedSoftwareVersion, self.versionMatchMessage))

        self.logger.info('Done getting the software inventory.')

    def __getLocalStorage(self):
        self.logger.info('Checking to see if there is any local storage.')
        command = 'lsscsi -H'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to get a list of SCSI devices was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Failed to get the list of SCSI devices.\n' + err)
            self.inventoryError = True
            return 'Error'
        scsiDict = dict.fromkeys([ col.split()[1] for col in out.splitlines() ])
        self.logger.info('The SCSI devices were determined to be: ' + str(scsiDict))
        if 'hpsa' in scsiDict or 'cciss' in scsiDict:
            self.localStoragePresent = True
            return 'Present'
        else:
            return 'Absent'
        self.logger.info('Done checking to see if there is any local storage.')

    def getComponentUpdateDict(self):
        return self.componentUpdateDict

    def getMellanoxBusList(self):
        return self.mellanoxBusList

    def getInventoryStatus(self):
        return self.inventoryError

    def getHardDriveFirmwareStatus(self):
        return self.hardDriveFirmwareMissing

    def getHardDrivesMissingFirmware(self):
        return ', '.join(self.hardDrivesMissingFirmware)

    def _getComputeNodeSpecificFirmwareInventory(self):
        pass

    def _getComputeNodeSpecificDriverInventory(self):
        pass

    def _getComputeNodeSpecificSoftwareInventory(self):
        pass

    def isExternalStoragePresent(self):
        return self.externalStoragePresent


class Gen1ScaleUpComputeNodeInventory(ComputeNodeInventory):

    def __init__(self, computeNodeDict, noPMCFirmwareUpdateModels, computeNodeResources):
        ComputeNodeInventory.__init__(self, computeNodeDict, noPMCFirmwareUpdateModels, computeNodeResources)
        self.busList = []

    def _getComputeNodeSpecificFirmwareInventory(self):
        self.logger.info("Getting the compute node's FusionIO firmware inventory.")
        command = 'fio-status'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to get the FusionIO firmware information was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Failed to get the FusionIO status information needed to determine the FusionIO firmware version information.\n' + err)
            self.inventoryError = True
            return
        fioStatusList = out.splitlines()
        count = 0
        ioDIMMStatusDict = {}
        firmwareUpdateRequired = 'no'
        csurFusionIOFirmwareVersion = self.firmwareDict['FusionIO'][0]
        for line in fioStatusList:
            line = line.strip()
            if 'Firmware' in line or re.search('PCI:[0-9a-f]{2}:[0-9]{2}\\.[0-9]{1}', line):
                if 'Firmware' in line:
                    ioDIMMStatusDict['Firmware'] = re.match('Firmware\\s+(v([0-9]\\.){2}[0-9]{1,2})', line).group(1)
                    self.logger.info('The ioDIMM firmware version was determined to be: ' + ioDIMMStatusDict['Firmware'] + '.')
                else:
                    ioDIMMStatusDict['bus'] = re.match('.*([0-9a-f]{2}:[0-9]{2}\\.[0-9]{1})', line).group(1)
                    self.logger.info('The ioDIMM bus was determined to be: ' + ioDIMMStatusDict['bus'] + '.')
                count += 1
            if count == 2:
                if ioDIMMStatusDict['Firmware'] != csurFusionIOFirmwareVersion:
                    self.busList.append(ioDIMMStatusDict['bus'])
                    if firmwareUpdateRequired == 'no':
                        self.componentUpdateDict['Firmware']['FusionIO'] = self.firmwareDict['FusionIO'][1]
                        firmwareUpdateRequired = 'yes'
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('FusionIOBus: ' + ioDIMMStatusDict['bus'], csurFusionIOFirmwareVersion, ioDIMMStatusDict['Firmware'], self.notVersionMatchMessage))
                else:
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('FusionIOBus: ' + ioDIMMStatusDict['bus'], csurFusionIOFirmwareVersion, ioDIMMStatusDict['Firmware'], self.versionMatchMessage))
                ioDIMMStatusDict.clear()
                count = 0

        self.logger.info("Done getting the compute node's FusionIO firmware inventory.")

    def _getComputeNodeSpecificDriverInventory(self):
        started = False
        updateDriverList = []
        self.logger.info("Getting the compute node's FusionIO driver inventory.")
        for data in self.computeNodeResources:
            data = data.replace(' ', '')
            if not re.match('FusionIODriver', data) and not started:
                continue
            elif re.match('FusionIODriver', data):
                started = True
                continue
            else:
                csurDriverList = data.split('|')
                csurDriverVersion = csurDriverList[1]
                command = 'modinfo iomemory_vsl'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to get the FusionIO driver information was: ' + out.strip())
                if result.returncode != 0:
                    self.logger.error('Failed to get the FusionIO driver information.\n' + err)
                    self.inventoryError = True
                else:
                    installedDriverVersion = re.match('.*srcversion:\\s+([1-3][^\\s]+)', out, re.MULTILINE | re.DOTALL).group(1)
                    self.logger.info('The FusionIO driver version was determined to be: ' + installedDriverVersion + '.')
                    if installedDriverVersion != csurDriverVersion:
                        self.componentUpdateDict['Drivers']['iomemory_vsl'] = csurDriverList[2]
                        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('iomemory_vsl', csurDriverVersion, installedDriverVersion, self.notVersionMatchMessage))
                    else:
                        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('iomemory_vsl', csurDriverVersion, installedDriverVersion, self.versionMatchMessage))
                break

        self.logger.info("Done getting the compute node's FusionIO driver inventory.")

    def _getComputeNodeSpecificSoftwareInventory(self):
        softwareFound = False
        updateRequired = False
        self.logger.info("Getting the compute node's FusionIO software inventory.")
        for data in self.computeNodeResources:
            data = data.replace(' ', '')
            if not re.match('FusionIOSoftware', data) and not softwareFound:
                continue
            elif re.match('FusionIOSoftware', data):
                softwareFound = True
                continue
            elif re.match('\\s*$', data):
                break
            else:
                csurSoftwareList = data.split('|')
                csurSoftware = csurSoftwareList[0]
                csurSoftwareEpoch = csurSoftwareList[1]
                csurSoftwareVersion = csurSoftwareList[2]
                command = "rpm -q --queryformat=%{buildtime}':'%{version}'-'%{release} " + csurSoftware
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.info('The output of the command (' + command + ') used to get the software epoch information was: ' + out.strip())
                if result.returncode != 0:
                    if 'is not installed' in err or 'is not installed' in out:
                        if not updateRequired:
                            updateRequired = True
                        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurSoftware, csurSoftwareVersion, 'Not Installed', self.versionMatchWarningMessage))
                        continue
                    else:
                        self.logger.error("Failed to get the Compute Node's software version for software " + csurSoftware + '.\n' + err)
                        self.inventoryError = True
                        continue
                rpmInformationList = out.strip().split(':')
                installedSoftwareEpoch = rpmInformationList[0]
                installedSoftwareVersion = rpmInformationList[1]
                self.logger.info('The software epoch date was determined to be: ' + installedSoftwareEpoch + '.')
                if installedSoftwareEpoch != csurSoftwareEpoch:
                    if not updateRequired:
                        updateRequired = True
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurSoftware, csurSoftwareVersion, installedSoftwareVersion, self.notVersionMatchMessage))
                else:
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(csurSoftware, csurSoftwareVersion, installedSoftwareVersion, self.versionMatchMessage))

        if updateRequired:
            self.componentUpdateDict['Software'].append('FusionIO')
        self.logger.info("Done getting the compute node's FusionIO software inventory.")

    def getFusionIOBusList(self):
        return self.busList