# Embedded file name: ./csurUpdateInitialize.py
import logging
import os
import subprocess
import re
import time
from collectComponentInformation import GetComponentInformation

class Initialize:

    def __init__(self, cursesThread):
        self.csurResourceDict = {}
        self.cursesThread = cursesThread

    def __printHeader(self, programVersion):
        version = 'Version ' + programVersion
        versionLength = len(version)
        title = 'SAP HANA CSUR Update Application'
        titleLength = len(title)
        author = 'Bill Neumann - SAP HANA CoE'
        authorLength = len(author)
        copyright = '(c) Copyright 2016 Hewlett Packard Enterprise Development LP'
        copyrightLength = len(copyright)
        welcomeMessageTop = '+' + '-' * 65 + '+'
        welcomeMessageTitle = '|' + title + ' ' * (65 - titleLength) + '|'
        welcomeMessageVersion = '|' + version + ' ' * (65 - versionLength) + '|'
        welcomeMessageAuthor = '|' + author + ' ' * (65 - authorLength) + '|'
        welcomeMessageCopyright = '|' + copyright + ' ' * (65 - copyrightLength) + '|'
        welcomeMessageBottom = '+' + '-' * 65 + '+'
        welcomMessageContainer = [welcomeMessageTop,
         welcomeMessageTitle,
         welcomeMessageVersion,
         welcomeMessageAuthor,
         welcomeMessageCopyright,
         welcomeMessageBottom]
        for line in welcomMessageContainer:
            self.cursesThread.insertMessage(['info', line])

        self.cursesThread.insertMessage(['info', ''])

    def init(self, csurBasePath, logBaseDir, programVersion, versionInformationLogOnly, updateOSHarddrives):
        self.csurResourceDict['csurBasePath'] = csurBasePath
        self.__printHeader(programVersion)
        if versionInformationLogOnly:
            self.cursesThread.insertMessage(['informative', 'Phase 1: Collecting system version information report.'])
        else:
            self.cursesThread.insertMessage(['informative', 'Phase 1: Initializing for the system update.'])
        csurAppResourceFile = csurBasePath + '/resourceFiles/csurAppResourceFile'
        try:
            with open(csurAppResourceFile) as f:
                for line in f:
                    line = line.strip()
                    line = re.sub('[\'"]', '', line)
                    if len(line) == 0 or re.match('^\\s*#', line) or re.match('^\\s+$', line):
                        continue
                    else:
                        key, val = line.split('=')
                        key = key.strip()
                        self.csurResourceDict[key] = val.strip()

        except IOError as err:
            self.__exitOnError("Unable to open the csur application's resource file (" + csurAppResourceFile + ') for reading; fix the problem and try again; exiting program execution.')

        self.csurResourceDict['logBaseDir'] = logBaseDir
        try:
            mainApplicationLog = self.csurResourceDict['mainApplicationLog']
        except KeyError as err:
            self.__exitOnError('The resource key (' + str(err) + ") was not present in the application's resource file " + csurAppResourceFile + '; fix the problem and try again; exiting program execution.')

        mainApplicationLog = logBaseDir + mainApplicationLog
        mainApplicationHandler = logging.FileHandler(mainApplicationLog)
        logger = logging.getLogger('mainApplicationLogger')
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        mainApplicationHandler.setFormatter(formatter)
        logger.addHandler(mainApplicationHandler)
        versionInformationLog = logBaseDir + 'versionInformationLog.log'
        versionInformationHandler = logging.FileHandler(versionInformationLog)
        versionInformationLogger = logging.getLogger('versionInformationLog')
        versionInformationLogger.setLevel(logging.INFO)
        versionInformationLogger.addHandler(versionInformationHandler)
        getComponentInformation = GetComponentInformation(self.csurResourceDict, self.cursesThread)
        componentListDict = getComponentInformation.getComponentInformation(versionInformationLogOnly, updateOSHarddrives)
        self.csurResourceDict['componentListDict'] = componentListDict
        return self.csurResourceDict

    def __exitOnError(self, message):
        self.cursesThread.insertMessage(['error', message])
        time.sleep(5.0)
        self.cursesThread.join()
        exit(1)