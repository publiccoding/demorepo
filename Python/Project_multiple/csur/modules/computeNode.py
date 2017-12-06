# Embedded file name: ./computeNode.py
import logging
import os
import subprocess
import re
from fusionIOUtils import checkFusionIOFirmwareUpgradeSupport
from computeNodeInventory import ComputeNodeInventory, Gen1ScaleUpComputeNodeInventory

class ComputeNode:

    def __init__(self, csurResourceDict, ip):
        self.csurResourceDict = csurResourceDict
        self.computeNodeDict = {}
        try:
            logBaseDir = self.csurResourceDict['logBaseDir']
        except KeyError as err:
            raise KeyError(str(err))

        self.computeNodeDict['ip'] = ip
        hostname = os.uname()[1]
        self.computeNodeDict['hostname'] = hostname
        computeNodeLog = logBaseDir + 'computeNode_' + hostname + '.log'
        handler = logging.FileHandler(computeNodeLog)
        self.loggerName = ip + 'Logger'
        self.computeNodeDict['loggerName'] = self.loggerName
        logger = logging.getLogger(self.loggerName)
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def computeNodeInitialize(self, computeNodeResources, versionInformationLogOnly, updateOSHarddrives):
        logger = logging.getLogger(self.loggerName)
        resultDict = {'updateNeeded': False,
         'errorMessages': [],
         'hardDrivesMissingFirmware': ''}
        command = 'dmidecode -s system-product-name'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        out = out.strip()
        logger.info('The output of the command (' + command + ") used to get the system's model was: " + out)
        if result.returncode != 0:
            logger.error("Unable to get the system's model information.\n" + err)
            resultDict['errorMessages'].append("Unable to get the system's model information.")
            return resultDict
        else:
            try:
                systemModel = re.match('[a-z,0-9]+\\s+(.*)', out, re.IGNORECASE).group(1).replace(' ', '')
            except AttributeError as err:
                logger.error("There was a system model match error when trying to match against '" + out + "':\n" + str(err) + '.')
                resultDict['errorMessages'].append('There was a system model match error.')
                return resultDict

            try:
                if systemModel not in self.csurResourceDict['supportedComputeNodeModels']:
                    logger.error("The system's model (" + systemModel + ') is not supported by this CSUR bundle.')
                    resultDict['errorMessages'].append("The system's model is not supported by this CSUR bundle.")
                    return resultDict
            except KeyError as err:
                logger.error('The resource key (' + str(err) + ") was not present in the application's resource file.")
                resultDict['errorMessages'].append('A resource key error was encountered.')
                return resultDict

            logger.info("The system's model was determined to be: " + systemModel + '.')
            self.computeNodeDict['systemModel'] = systemModel
            command = 'cat /proc/version'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            logger.info('The output of the command (' + command + ') used to get the OS distribution information was: ' + out.strip())
            if result.returncode != 0:
                logger.error("Unable to get the system's OS distribution version information.\n" + err)
                resultDict['errorMessages'].append("Unable to get the system's OS distribution version information.")
                return resultDict
            versionInfo = out.lower()
            if 'suse' in versionInfo:
                OSDist = 'SLES'
                command = 'cat /etc/SuSE-release'
            else:
                OSDist = 'RHEL'
                command = 'cat /etc/redhat-release'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                logger.error("Unable to get the system's OS distribution level.\n" + err)
                resultDict['errorMessages'].append("Unable to get the system's OS distribution level.")
                return resultDict
            releaseInfo = out.replace('\n', ' ')
            if OSDist == 'SLES':
                try:
                    slesVersion = re.match('.*version\\s*=\\s*([1-4]{2})', releaseInfo, re.IGNORECASE).group(1)
                except AttributeError as err:
                    logger.error("There was SLES OS version match error when trying to match against '" + releaseInfo + "':\n" + str(err) + '.')
                    resultDict['errorMessages'].append('There was a SLES OS version match error.')
                    return resultDict

                try:
                    slesPatchLevel = re.match('.*patchlevel\\s*=\\s*([1-4]{1})', releaseInfo, re.IGNORECASE).group(1)
                except AttributeError as err:
                    logger.error("There was SLES patch level match error when trying to match against '" + releaseInfo + "':\n" + str(err) + '.')
                    resultDict['errorMessages'].append('There was a SLES patch level match error.')
                    return resultDict

                osDistLevel = OSDist + slesVersion + '.' + slesPatchLevel
            else:
                try:
                    rhelVersion = re.match('.*release\\s+([6-7]{1}.[0-9]{1}).*', releaseInfo, re.IGNORECASE).group(1)
                except AttributeError as err:
                    logger.error("There was RHEL OS version match error when trying to match against '" + releaseInfo + "':\n" + str(err) + '.')
                    resultDict['errorMessages'].append('There was a RHEL OS version match error.')
                    return resultDict

                osDistLevel = OSDist + rhelVersion
            try:
                if osDistLevel not in self.csurResourceDict['supportedDistributionLevels']:
                    logger.error("The system's OS distribution level (" + osDistLevel + ') is not supported by this CSUR bundle.')
                    resultDict['errorMessages'].append("The system's OS distribution level is not supported by this CSUR bundle.")
                    return resultDict
            except KeyError as err:
                logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
                resultDict['errorMessages'].append('A resource key error was encountered.')
                return resultDict

            logger.info("The system's OS distribution level was determined to be: " + osDistLevel + '.')
            self.computeNodeDict['osDistLevel'] = osDistLevel
            if not versionInformationLogOnly:
                if 'DL380' in systemModel or 'DL360' in systemModel:
                    if 'SLES' in osDistLevel:
                        sgBinPath = '/opt/cmcluster/bin'
                    else:
                        sgBinPath = '/usr/local/cmcluster/bin'
                    command = sgBinPath + '/cmviewcl -f line -l cluster'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    logger.info('The output of the command (' + command + ') used to check if the cluster is running was: ' + out.strip())
                    if result.returncode != 0:
                        logger.error('Unable to check if the cluster is running.\n' + err)
                        resultDict['errorMessages'].append('Unable to check if the cluster is running.')
                        return resultDict
                    clusterView = out.splitlines()
                    for line in clusterView:
                        if re.search('^status=', line):
                            if re.match('status=up', line):
                                logger.error('It appears that the cluster is still running.\n' + out.strip())
                                resultDict['errorMessages'].append('It appears that the cluster is still running.')
                                return resultDict

                    command = sgBinPath + '/cmversion'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    out = out.strip()
                    logger.info('The output of the command (' + command + ") used to get Serviceguard's version was: " + out)
                    if result.returncode != 0:
                        logger.error("Unable to get Serviceguard's version.\n" + err)
                        resultDict['errorMessages'].append("Unable to get Serviceguard's version.")
                        return resultDict
                    sgVersion = out[0:7]
                    try:
                        if sgVersion not in self.csurResourceDict['supportedServiceguardLevels']:
                            logger.error('The current version of Serviceguard ' + out + ' is not supported for an upgrade.')
                            resultDict['errorMessages'].append('The current version of Serviceguard is not supported.')
                            return resultDict
                    except KeyError as err:
                        logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
                        resultDict['errorMessages'].append('A resource key error was encountered.')
                        return resultDict

                if not 'DL380' in systemModel:
                    if not 'DL320' in systemModel:
                        if not 'DL360' in systemModel:
                            command = 'ps -C hdbnameserver,hdbcompileserver,hdbindexserver,hdbpreprocessor,hdbxsengine,hdbwebdispatcher'
                            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                            out, err = result.communicate()
                            logger.info('The output of the command (' + command + ') used to check if SAP is running was: ' + out.strip())
                            if result.returncode == 0:
                                logger.warn('It appears that SAP HANA is still running.\n' + out)
                                resultDict['errorMessages'].append('It appears that SAP HANA is still running.')
                                return resultDict
                        if systemModel == 'DL580G7' or systemModel == 'DL980G7':
                            command = 'mount'
                            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                            out, err = result.communicate()
                            logger.info('The output of the command (' + command + ') used to check if the log partition is mounted was: ' + out.strip())
                            if result.returncode != 0:
                                logger.error('Unable to check if the log partition is mounted.\n' + err)
                                resultDict['errorMessages'].append('Unable to check if the log partition is mounted.')
                                return resultDict
                            if re.search('/hana/log|/HANA/IMDB-log', out, re.MULTILINE | re.DOTALL) != None:
                                logger.error('The log partition is still mounted.')
                                resultDict['errorMessages'].append('The log partition needs to be unmounted before the system is updated.')
                                return resultDict
                            command = 'uname -r'
                            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                            out, err = result.communicate()
                            kernel = out.strip()
                            logger.info('The output of the command (' + command + ') used to get the currently used kernel was: ' + kernel)
                            if result.returncode != 0:
                                logger.error("Unable to get the system's current kernel information.\n" + err)
                                resultDict['errorMessages'].append("Unable to get the system's current kernel information.")
                                return resultDict
                            logger.info('The currently used kernel was determined to be: ' + kernel + '.')
                            self.computeNodeDict['kernel'] = kernel
                            command = 'uname -p'
                            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                            out, err = result.communicate()
                            processorType = out.strip()
                            logger.info('The output of the command (' + command + ") used to get the compute node's processor type was: " + processorType)
                            if result.returncode != 0:
                                logger.error("Unable to get the system's processor type.\n" + err)
                                resultDict['errorMessages'].append("Unable to get the system's processor type.")
                                return resultDict
                            logger.info("The compute node's processor type was determined to be: " + processorType + '.')
                            self.computeNodeDict['processorType'] = processorType
                            try:
                                if not checkFusionIOFirmwareUpgradeSupport(self.csurResourceDict['fusionIOFirmwareVersionList'], self.loggerName):
                                    resultDict['errorMessages'].append('The fusionIO firmware is not at a supported version for an automatic upgrade.')
                                    return resultDict
                            except KeyError as err:
                                logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
                                resultDict['errorMessages'].append('A resource key error was encountered.')
                                return resultDict

                    if not updateOSHarddrives and not systemModel == '16sx86':
                        result = self.__checkDrivers(computeNodeResources, systemModel, osDistLevel)
                        if result != '':
                            resultDict['errorMessages'].append(result)
                            return resultDict
                    try:
                        if systemModel == 'DL580G7' or systemModel == 'DL980G7':
                            computeNodeInventory = Gen1ScaleUpComputeNodeInventory(self.computeNodeDict.copy(), self.csurResourceDict['noPMCFirmwareUpdateModels'], computeNodeResources)
                        elif systemModel == 'DL380pGen8' and 'systemGeneration' in self.csurResourceDict and self.csurResourceDict['systemGeneration'] == 'Gen1.x':
                            computeNodeInventory = ComputeNodeInventory(self.computeNodeDict.copy(), self.csurResourceDict['noPMCFirmwareUpdateModels'], computeNodeResources, systemGeneration='Gen1.x')
                        else:
                            computeNodeInventory = ComputeNodeInventory(self.computeNodeDict.copy(), self.csurResourceDict['noPMCFirmwareUpdateModels'], computeNodeResources)
                    except KeyError as err:
                        logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
                        resultDict['errorMessages'].append('A resource key error was encountered.')
                        return resultDict

                    if not updateOSHarddrives:
                        computeNodeInventory.getComponentUpdateInventory(self.csurResourceDict.copy())
                    else:
                        hardDrivesLocal = computeNodeInventory.getLocalHardDriveFirmwareInventory()
                        if hardDrivesLocal != None and not hardDrivesLocal:
                            resultDict['errorMessages'].append('There are no local hard drives to update, since there were no controllers detected.')
                            return resultDict
                    if computeNodeInventory.getInventoryStatus():
                        resultDict['errorMessages'].append("Errors were encountered during the compute node's inventory.")
                        return resultDict
                    if computeNodeInventory.getHardDriveFirmwareStatus():
                        resultDict['hardDrivesMissingFirmware'] = computeNodeInventory.getHardDrivesMissingFirmware()
                    if versionInformationLogOnly:
                        return resultDict
                    componentUpdateDict = computeNodeInventory.getComponentUpdateDict()
                    self.computeNodeDict['componentUpdateDict'] = updateOSHarddrives and len(componentUpdateDict['Firmware']) != 0 and len(resultDict['hardDrivesMissingFirmware']) == 0 and componentUpdateDict
                    resultDict['updateNeeded'] = True
                else:
                    logger.error('The local hard drives are not being updated, since firmware was missing for the following hard drives: ' + resultDict['hardDrivesMissingFirmware'] + '.')
            else:
                componentDictSizes = [ len(dict) for dict in componentUpdateDict.values() ]
                if any((x != 0 for x in componentDictSizes)):
                    self.computeNodeDict['componentUpdateDict'] = componentUpdateDict
                    resultDict['updateNeeded'] = True
                    self.computeNodeDict['mellanoxBusList'] = computeNodeInventory.getMellanoxBusList()
                    if 'FusionIO' in componentUpdateDict['Firmware']:
                        self.computeNodeDict['busList'] = computeNodeInventory.getFusionIOBusList()
                    self.computeNodeDict['externalStoragePresent'] = computeNodeInventory.isExternalStoragePresent()
            return resultDict

    def __checkDrivers(self, computeNodeResources, systemModel, osDistLevel):
        errorMessage = ''
        logger = logging.getLogger(self.loggerName)
        hbaPresent, localStoragePresent = self.__checkStorage()
        if hbaPresent == None or localStoragePresent == None:
            errorMessage = 'Problems were encountered while checking local storage components.'
            return errorMessage
        else:
            try:
                hbaDrivers = self.csurResourceDict['hbaDrivers']
                localStorageDrivers = self.csurResourceDict['localStorageDrivers']
                nicDriverDict = dict.fromkeys([ x.strip() for x in self.csurResourceDict['nicDriverList'].split(',') ])
                nicDriverCrossReferenceList = self.csurResourceDict['nicDriverCrossReferenceList'].split(',')
                pciIdsFile = self.csurResourceDict['csurBasePath'] + '/resourceFiles/' + self.csurResourceDict['pciIdsFile']
            except KeyError as err:
                logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
                errorMessage = 'A resource key was not present in the resource file.'
                return errorMessage

            hbaDriverDict = dict.fromkeys([ x.strip() for x in hbaDrivers.split(',') ])
            localStorageDriverDict = dict.fromkeys([ x.strip() for x in localStorageDrivers.split(',') ])
            nicDriverCrossReferenceDict = dict([ x.replace(' ', '').split(':') for x in nicDriverCrossReferenceList ])
            installedNicDriverDict, errorsEncountered = self.__getInstalledNicDriverDict(nicDriverCrossReferenceDict, pciIdsFile)
            if errorsEncountered:
                errorMessage = 'Problems were encountered while getting the list of NIC drivers that should be loaded.'
                return errorMessage
            logger.info('The installed NIC driver dictionary is: ' + str(installedNicDriverDict))
            command = command = 'cat /proc/modules'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            logger.info('The output of the command (' + command + ') used to get the list of loaded drivers was: ' + out.strip())
            if result.returncode != 0:
                logger.error('Could not get the list of loaded drivers.\n' + err)
                errorMessage = 'Could not get the list of loaded drivers.'
                return errorMessage
            driverDict = dict.fromkeys([ col.split()[0] for col in out.splitlines() ])
            logger.info('The driver dictionary (loaded drivers) was determined to be: ' + str(driverDict))
            driversFound = False
            started = False
            mlnxDriverFound = False
            for data in computeNodeResources:
                data = data.replace(' ', '')
                if 'Drivers' not in data and not driversFound:
                    continue
                elif 'Drivers' in data:
                    driversFound = True
                    continue
                elif osDistLevel in data and not systemModel in data and not started:
                    continue
                elif osDistLevel in data and systemModel in data:
                    started = True
                    continue
                elif re.match('\\s*$', data):
                    break
                else:
                    computeNodeDriverList = data.split('|')
                    computeNodeDriver = computeNodeDriverList[0]
                    if not hbaPresent and computeNodeDriver in hbaDriverDict:
                        continue
                    if not localStoragePresent and computeNodeDriver in localStorageDriverDict:
                        continue
                    if computeNodeDriver not in driverDict:
                        if computeNodeDriver in installedNicDriverDict:
                            if (computeNodeDriver == 'mlx4_en' or computeNodeDriver == 'mlnx') and not mlnxDriverFound:
                                mlnxDriverFound = True
                                continue
                            else:
                                logger.error('The ' + computeNodeDriver + ' driver does not appear to be loaded.')
                                errorMessage = 'The ' + computeNodeDriver + ' driver does not appear to be loaded.'
                                return errorMessage
                        elif computeNodeDriver in nicDriverDict:
                            continue
                        else:
                            logger.error('The ' + computeNodeDriver + ' driver does not appear to be loaded.')
                            errorMessage = 'The ' + computeNodeDriver + ' driver does not appear to be loaded.'
                            return errorMessage

            return errorMessage

    def __checkStorage(self):
        hbaPresent = None
        localStoragePresent = None
        logger = logging.getLogger(self.loggerName)
        logger.info('Checking for local storage components.')
        command = 'systool -c scsi_host -v'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ') used to check if HBAs are present was: ' + out.strip())
        if result.returncode != 0:
            logger.error("Failed to get the compute node's HBA information.\n" + err)
        elif re.search('HBA', out, re.MULTILINE | re.DOTALL) != None:
            hbaPresent = True
        else:
            hbaPresent = False
        command = 'lsscsi'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ') used to check if local storage is present was: ' + out.strip())
        if result.returncode != 0:
            logger.error("Failed to get the compute node's SCSI information.\n" + err)
        else:
            scsiDict = dict.fromkeys([ col.split()[1] for col in out.splitlines() ])
            logger.info('The SCSI devices were determined to be: ' + str(scsiDict))
            if 'storage' in scsiDict:
                localStoragePresent = True
            else:
                localStoragePresent = False
        logger.info('Done checking for local storage components.')
        return (hbaPresent, localStoragePresent)

    def __getInstalledNicDriverDict(self, nicDriverCrossReferenceDict, pciIdsFile):
        logger = logging.getLogger(self.loggerName)
        installedNICDriverDict = {}
        command = 'lspci -i ' + pciIdsFile + ' -mvv'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ') used to check what nic drivers should be loaded depending on the installed NIC cards was: ' + out.strip())
        if result.returncode != 0:
            logger.error('Failed to get the list of installed NIC cards.\n' + err)
            return (installedNICDriverDict, True)
        else:
            out = re.sub('\n{2,}', '####', out)
            deviceList = out.split('####')
            for device in deviceList:
                if 'Ethernet controller' in device or 'Network controller' in device:
                    try:
                        nicModel = re.match('.*\\s+([a-z0-9+]+)\\s+Adapter.*', device, re.MULTILINE | re.DOTALL | re.IGNORECASE).group(1)
                    except AttributeError as err:
                        logger.error("There was a match error when trying to get the NIC cards models when matching against '" + device + "':\n" + str(err) + '.')
                        return (installedNICDriverDict, True)

                    nicDriverList = nicDriverCrossReferenceDict[nicModel].replace(' ', '').split('|')
                    for driver in nicDriverList:
                        installedNICDriverDict[driver] = None

            return (installedNICDriverDict, False)

    def getComputeNodeDict(self):
        return self.computeNodeDict