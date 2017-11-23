# Embedded file name: ./collectComponentInformation.py
import re
import logging
import time
import os
from computeNode import ComputeNode
from csurUpdateUtils import RED, RESETCOLORS, TimerThread

class GetComponentInformation:

    def __init__(self, csurResourceDict, cursesThread):
        self.csurResourceDict = csurResourceDict
        self.cursesThread = cursesThread

    def getComponentInformation(self, versionInformationLogOnly, updateOSHarddrives):
        logBaseDir = self.csurResourceDict['logBaseDir']
        csurBasePath = self.csurResourceDict['csurBasePath']
        self.csurResourceDict['multipleUpgradesRequiredDict'] = {'SAN Switches': [],
         '3PAR': []}
        timerThreadLocationDict = {}
        componentListDict = {'computeNodeList': [],
         'networkSwitchList': [],
         'sanSwitchList': [],
         'storeServList': []}
        logger = logging.getLogger('mainApplicationLogger')
        componentResourceList = self.__getComponentResources(['Compute Node'], csurBasePath)
        if componentResourceList[0]:
            self.__exitOnError("An error occurred while collecting component resources; check the application's log file for errors; exiting program execution.")
        try:
            computeNode = ComputeNode(self.csurResourceDict.copy(), '127.0.0.1')
            computeNodeDict = computeNode.getComputeNodeDict()
            hostname = computeNodeDict['hostname']
            self.csurResourceDict['hostname'] = hostname
        except KeyError as err:
            logger.error('The resource key (' + str(err) + ") was not present in the application's resource file.")
            self.__exitOnError("A resource key was not present in the application's resource file; check the application's log file for errors; exiting program execution.")

        if versionInformationLogOnly:
            timerThread = TimerThread('Getting compute node ' + hostname + "'s version report ... ")
        elif updateOSHarddrives:
            timerThread = TimerThread('Initializing compute node ' + hostname + ' for an OS hard drive update ... ')
        else:
            timerThread = TimerThread('Initializing compute node ' + hostname + ' ... ')
        timerThread.daemon = True
        timerThread.start()
        if '127.0.0.1' not in timerThreadLocationDict:
            self.cursesThread.insertTimerThread(['', timerThread])
            timerThreadLocationDict['127.0.0.1'] = self.cursesThread.getTimerThreadLocation()
        else:
            self.cursesThread.insertTimerThread(['', timerThread], timerThreadLocationDict['127.0.0.1'])
        resultDict = computeNode.computeNodeInitialize(componentResourceList[1]['ComputeNodeResources'][:], versionInformationLogOnly, updateOSHarddrives)
        timerThread.stopTimer()
        timerThread.join()
        if len(resultDict['errorMessages']) != 0:
            if versionInformationLogOnly:
                self.__exitOnError('Error(s) were encountered while generating compute node ' + hostname + "'s version report; check the compute node's log file for additional information; exiting program execution.")
            elif updateOSHarddrives:
                if 'There are no local hard drives to update' not in resultDict['errorMessages'][-1]:
                    self.__exitOnError('Error(s) were encountered while initializing compute node ' + hostname + " for an OS hard drive update; check the compute node's log file for additional information; exiting program execution.")
                else:
                    self.cursesThread.updateTimerThread('Compute node ' + hostname + ' does not have any local hard drives to update.', timerThreadLocationDict['127.0.0.1'])
                    self.__exitOnError('Compute node ' + hostname + ' does not have any local hard drives to update; exiting program execution.')
            else:
                self.__exitOnError('Error(s) were encountered while initializing compute node ' + hostname + "; check the compute node's log file for additional information; exiting program execution.")
        if versionInformationLogOnly:
            self.cursesThread.updateTimerThread('Done generating compute node ' + hostname + "'s version report.", timerThreadLocationDict['127.0.0.1'])
            logger.info('Done generating compute node ' + hostname + "'s version report.")
        elif resultDict['updateNeeded']:
            if updateOSHarddrives:
                self.cursesThread.updateTimerThread('Done initializing compute node ' + hostname + ' for an OS hard drive update.', timerThreadLocationDict['127.0.0.1'])
                logger.info('Done initializing compute node ' + hostname + ' for an OS hard drive update.')
            else:
                self.cursesThread.updateTimerThread('Done initializing compute node ' + hostname + '.', timerThreadLocationDict['127.0.0.1'])
                logger.info('Done initializing compute node ' + hostname + '.')
            componentListDict['computeNodeList'].append(computeNode)
        elif len(resultDict['hardDrivesMissingFirmware']) != 0:
            self.cursesThread.updateTimerThread('Compute node ' + hostname + "'s local OS hard drives are not being updated, since firmware for the hard drives was missing.", timerThreadLocationDict['127.0.0.1'])
            logger.info('Compute node ' + hostname + "'s local OS hard drives are not being updated, since firmware for the hard drives was missing.")
        else:
            self.cursesThread.updateTimerThread('Compute node ' + hostname + ' was skipped, since it was already up to date.', timerThreadLocationDict['127.0.0.1'])
            logger.info('Compute node ' + hostname + ' was skipped, since it was already up to date.')
        self.csurResourceDict['hardDrivesMissingFirmware'] = resultDict['hardDrivesMissingFirmware']
        self.csurResourceDict['timerThreadLocationDict'] = timerThreadLocationDict
        return componentListDict

    def __getComponentResources(self, componentList, csurBasePath):
        componentResourceDict = {}
        errors = False
        logger = logging.getLogger('mainApplicationLogger')
        logger.info('Getting component resource data for ' + ', '.join(componentList) + '.')
        for component in componentList:
            try:
                if component == 'Compute Node':
                    resourceFile = csurBasePath + '/resourceFiles/' + self.csurResourceDict['computeNodeResourceFile']
                elif component == 'Network Switch':
                    resourceFile = csurBasePath + '/resourceFiles/' + self.csurResourceDict['networkSwitchResourceFile']
                elif component == 'SAN Switch':
                    resourceFile = csurBasePath + '/resourceFiles/' + self.csurResourceDict['sanSwitchResourceFile']
                elif component == '3PAR StoreServ':
                    resourceFile = csurBasePath + '/resourceFiles/' + self.csurResourceDict['threePARResourceFile']
            except KeyError as err:
                errors = True
                logger.error('The resource key (' + str(err) + ") was not present in the application's resource file.")
                break

            try:
                with open(resourceFile) as f:
                    resources = f.read().splitlines()
            except IOError as err:
                errors = True
                logger.error('Unable to open the ' + component + "'s resource file (" + resourceFile + ') for reading.\n' + str(err))
                break

            if not errors:
                componentResourceKey = re.sub('\\s+', '', component) + 'Resources'
                componentResourceDict[componentResourceKey] = resources

        logger.info('Done getting component resource data for ' + ', '.join(componentList) + '.')
        return [errors, componentResourceDict]

    def __exitOnError(self, message):
        self.cursesThread.insertMessage(['error', message])
        time.sleep(10.0)
        self.cursesThread.join()
        exit(1)