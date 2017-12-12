# Embedded file name: ./osPatchUpdate.py
import logging
import os
import optparse
import signal
import re
import subprocess
import sys
import time
from threading import Thread
from modules.spUtils import RED, GREEN, PURPLE, BOLD, UNDERLINE, RESETCOLORS, SignalHandler
from modules.preUpdate import checkOSVersion, setPatchDirectories, removeFusionIOPackages, checkOSVersion, checkDiskSpace, updateBootloaderCFG
from modules.fusionIO import UpdateFusionIO
from modules.deadman import BuildDeadmanDriver
from modules.configureRepository import configureRepositories
from modules.updateZyppConf import updateZyppConf
from modules.applyPatches import ApplyPatches
from modules.createBootloaderConfigFile import configureBootLoader
from modules.updateReleaseInformation import updateVersionInformationFile
from modules.issues import updateSUSE_SLES_SAPRelease, sles12MultipathFix
from modules.oneOffs import OneOffs

def init(applicationResourceFile, loggerName):
    if os.geteuid() != 0:
        print RED + 'You must be root to run this program.' + RESETCOLORS
        exit(1)
    usage = 'usage: %prog [[-a] [-k] [-o] [-p]] [-v] [-h]'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-a', action='store_true', default=False, help='This option will result in the application of both OS and Kernel patches.')
    parser.add_option('-k', action='store_true', default=False, help='This option will result in the application of Kernel patches.')
    parser.add_option('-o', action='store_true', default=False, help='This option will result in the application of OS patches.')
    parser.add_option('-p', action='store_true', default=False, help='This option is used to perform the post update tasks.')
    parser.add_option('-v', action='store_true', default=False, help="This option is used to display the application's version.")
    options, args = parser.parse_args()
    applicationName = os.path.basename(sys.argv[0])
    applicationVersion = 'v1.8-6'
    if options.v:
        print applicationName + ' ' + applicationVersion
        exit(0)
    if options.a and options.k or options.a and options.o or options.k and options.o or options.a and options.p or options.o and options.p or options.k and options.p:
        parser.error('Options -a, -k, -o and -p are mutually exclusive.')
    if not options.a and not options.k and not options.o and not options.p:
        parser.error("Try '" + applicationName + " -h' to get command specific help.")
    if options.p:
        print GREEN + 'Phase 1: Initializing for the post system update.' + RESETCOLORS
    else:
        print GREEN + 'Phase 1: Initializing for the system update.' + RESETCOLORS
    patchResourceDict = {}
    patchResourceDict['options'] = options
    try:
        with open(applicationResourceFile) as f:
            for line in f:
                line = line.strip()
                line = re.sub('[\'"]', '', line)
                if len(line) == 0 or re.match('^\\s*#', line) or re.match('^\\s+$', line):
                    continue
                else:
                    key, val = line.split('=')
                    key = key.strip()
                    patchResourceDict[key] = val.strip()

    except IOError as err:
        print RED + "Unable to access the application's resource file " + applicationResourceFile + '.\n' + str(err) + '\n' + RESETCOLORS
        exit(1)

    try:
        logBaseDir = re.sub('\\s+', '', patchResourceDict['logBaseDir']).rstrip('/')
        patchApplicationLog = re.sub('\\s+', '', patchResourceDict['patchApplicationLog'])
        patchApplicationLog = logBaseDir + '/' + patchApplicationLog
    except KeyError as err:
        print RED + 'The resource key (' + str(err) + ') was not present in the resource file; exiting program execution.' + '\n' + RESETCOLORS
        exit(1)

    if not options.p:
        try:
            logList = os.listdir(logBaseDir)
            for log in logList:
                os.remove(logBaseDir + '/' + log)

        except OSError as err:
            print RED + 'Unable to remove old logs in ' + logBaseDir + '; exiting program execution.\n' + str(err) + '\n' + RESETCOLORS
            exit(1)

    handler = logging.FileHandler(patchApplicationLog)
    logger = logging.getLogger(loggerName)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if options.p:
        return patchResourceDict
    logger.info(applicationName + ' ' + applicationVersion)
    try:
        if len(patchResourceDict['rpmsToRemove']) != 0:
            patchResourceDict['removeRPMs'] = True
        else:
            patchResourceDict['removeRPMs'] = False
        if len(patchResourceDict['rpmsToAdd']) != 0:
            patchResourceDict['addRPMs'] = True
        else:
            patchResourceDict['addRPMs'] = False
    except KeyError as err:
        logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
        print RED + 'A resource key was not present in the resource file, check the log file for errors; exiting program execution.' + '\n' + RESETCOLORS
        exit(1)

#from modules.preUpdate import checkOSVersion, setPatchDirectories, removeFusionIOPackages, checkOSVersion, checkDiskSpace, updateBootloaderCFG


    checkDiskSpace(loggerName)  # Preupgrade  1
    osDistLevel = checkOSVersion(patchResourceDict.copy(), loggerName) # Preupgrade  2
    patchResourceDict['osDistLevel'] = osDistLevel
    command = 'dmidecode -s system-product-name'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ") used to get the system's model was: " + out.strip())
    if result.returncode != 0:
        logger.error("Unable to get the system's model information.\n" + err)
        print RED + "\nUnable to get the system's model information; check the log file for errors; exiting program execution.\n" + RESETCOLORS
        exit(1)
    systemModel = re.match('[a-z,0-9]+\\s+(.*)', out, re.IGNORECASE).group(1).replace(' ', '')
    logger.info("The system's model was determined to be: " + systemModel + '.')
    patchResourceDict['systemModel'] = systemModel

#from modules.issues import updateSUSE_SLES_SAPRelease, sles12MultipathFix
    if osDistLevel == 'SLES_SP1':
        sles12MultipathFix(loggerName)  # issues 1
    if options.a or options.k:
        if systemModel == 'DL580G7' or systemModel == 'DL980G7' or systemModel == 'DL380pGen8' or systemModel == 'DL360pGen8':
            patchResourceDict['postUpdateRequired'] = 'yes'
            try:
                logBaseDir = re.sub('\\s+', '', patchResourceDict['logBaseDir']).rstrip('/')
                postUpdateResumeLog = re.sub('\\s+', '', patchResourceDict['postUpdateResumeLog'])
                postUpdateResumeLog = logBaseDir + '/' + postUpdateResumeLog
            except KeyError as err:
                logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
                print RED + 'The resource key for the post update resume log was not present in the resource file; check the log file for errors; exiting program execution.' + RESETCOLORS
                exit(1)

            try:
                f = open(postUpdateResumeLog, 'a')
                if systemModel == 'DL380pGen8' or systemModel == 'DL360pGen8':
                    f.write('isServiceguardSystem = yes\n')
                else:
                    f.write('isServiceguardSystem = no\n')
                if systemModel == 'DL580G7' or systemModel == 'DL980G7':
                    f.write('isFusionIOSystem = yes\n')

#from modules.preUpdate import checkOSVersion, setPatchDirectories, removeFusionIOPackages, checkOSVersion, checkDiskSpace, updateBootloaderCFG

                    removeFusionIOPackages(patchResourceDict.copy(), loggerName) # Preupgrade  3
                else:
                    f.write('isFusionIOSystem = no\n')
                f.close()
            except IOError as err:
                logger.error('Unable to access the post update resume log.\n' + str(err))
                print RED + 'Unable to access the post update resume log; check the log file for errors; exiting program execution.' + RESETCOLORS
                exit(1)

        else:
            patchResourceDict['postUpdateRequired'] = 'no'
    else:
        patchResourceDict['postUpdateRequired'] = 'no'
    if (options.a or options.o) and patchResourceDict['suseSLESSAPReleaseRPM'] != '':
        command = 'rpm -q SUSE_SLES_SAP-release'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode == 0:
            updateSUSE_SLES_SAPRelease(patchResourceDict.copy(), loggerName) # issues 2
        elif 'package SUSE_SLES_SAP-release is not installed' not in out:
            logger.error('Unable to determine if the SUSE_SLES_SAP-release RPM is installed.\n' + out)
            print RED + 'Unable to determine if the SUSE_SLES_SAP-release RPM is installed; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)
    patchDirList = setPatchDirectories(patchResourceDict.copy(), loggerName) # Preupgrade 4 

#from modules.configureRepository import configureRepositories

    configureRepositories(patchDirList[:], loggerName)  # configureRepository 
    repositoryList = []
    for dir in patchDirList:
        repositoryList.append(dir.split('/').pop())

    patchResourceDict['repositoryList'] = repositoryList

	
#from modules.updateZyppConf import updateZyppConf

	updateZyppConf(loggerName)  # updateZyppConf
    if osDistLevel == 'SLES_SP4':
	

        updateBootloaderCFG(loggerName)   # Preupgrade 5
    return patchResourceDict


def main():
    applicationResourceFile = '/hp/support/patches/resourceFiles/patchResourceFile'
    loggerName = 'patchLogger'
    patchResourceDict = init(applicationResourceFile, loggerName)
    logger = logging.getLogger(loggerName)
    options = patchResourceDict['options']
    if not options.p:
        print GREEN + 'Phase 2: Updating system with patches.' + RESETCOLORS
        osDistLevel = patchResourceDict['osDistLevel']
        if not options.k:
            if patchResourceDict['removeRPMs'] or patchResourceDict['addRPMs']:
#from modules.oneOffs import OneOffs
                oneOffs = OneOffs(loggerName) # oneOffs
                if patchResourceDict['removeRPMs']:
                    if not oneOffs.removeRPMs(patchResourceDict.copy()):
                        print RED + BOLD + '\nProblems were encountered while removing the RPMs which were identified by the patch resource file for removal; check the log file for errors; exiting program execution.' + RESETCOLORS
                        exit(1)
                if patchResourceDict['addRPMs']:
                    if not oneOffs.addRPMs(patchResourceDict.copy()):
                        print RED + BOLD + '\nProblems were encountered while adding the RPMs which were identified by the patch resource file for addition; check the log file for errors; exiting program execution.' + RESETCOLORS
                        exit(1)
        original_sigint_handler = signal.getsignal(signal.SIGINT)
        original_sigquit_handler = signal.getsignal(signal.SIGQUIT)
#from modules.applyPatches import ApplyPatches

		applyPatches = ApplyPatches()  # applyPatches
        s = SignalHandler(applyPatches)
        signal.signal(signal.SIGINT, s.signal_handler)
        signal.signal(signal.SIGQUIT, s.signal_handler)
        workerThread = Thread(target=applyPatches.applyPatches, args=(patchResourceDict['repositoryList'], loggerName))
        workerThread.start()
        while 1:
            time.sleep(0.1)
            if not workerThread.is_alive():
                if applyPatches.getExitStatus() != 0:
                    exit(1)
                else:
                    break
            response = s.getResponse()
            if response != '':
                if response == 'y':
                    applyPatches.endTask()
                    exit(1)

        signal.signal(signal.SIGINT, original_sigint_handler)
        signal.signal(signal.SIGQUIT, original_sigquit_handler)
        print ''
        updateTaskStatusDict = {}
        if (options.a or options.k) and osDistLevel == 'SLES_SP4':
            print GREEN + "Phase 3: Updating the system's bootloader." + RESETCOLORS

#from modules.createBootloaderConfigFile import configureBootLoader

            updateTaskStatusDict['configureBootLoader'] = configureBootLoader(loggerName)
        if (options.a or options.k) and osDistLevel == 'SLES_SP4':
            print GREEN + 'Phase 4: Updating the patch bundle information file.' + RESETCOLORS
        else:
            print GREEN + 'Phase 3: Updating the patch bundle information file.' + RESETCOLORS
        
#from modules.updateReleaseInformation import updateVersionInformationFile


		if options.a:
            updateTaskStatusDict['updateVersionInformationFile'] = updateVersionInformationFile(patchResourceDict.copy(), 'all', loggerName)
        elif options.k:
            updateTaskStatusDict['updateVersionInformationFile'] = updateVersionInformationFile(patchResourceDict.copy(), 'kernel', loggerName)
        elif options.o:
            updateTaskStatusDict['updateVersionInformationFile'] = updateVersionInformationFile(patchResourceDict.copy(), 'os', loggerName)
        taskFailureList = ''
        for key, value in updateTaskStatusDict.iteritems():
            if value == 'Failure':
                if taskFailureList == '':
                    taskFailureList += key
                else:
                    taskFailureList += ', ' + key

        if taskFailureList == '':
            if patchResourceDict['postUpdateRequired'] == 'yes':
                print GREEN + '\nThe system update has completed.  Reboot the system for the changes to take affect.\n' + RESETCOLORS
                print PURPLE + BOLD + UNDERLINE + "Make sure to run the program again with the '-p' option after the system reboots to complete the update procedure!\n" + RESETCOLORS
            else:
                print GREEN + '\nThe system update has successfully completed.  Reboot the system for the changes to take affect.\n' + RESETCOLORS
        elif patchResourceDict['postUpdateRequired'] == 'yes':
            print RED + BOLD + '\nThe system update failed to complete successfully.  Address the failed update tasks (' + taskFailureList + ') and then reboot the system for the changes to take affect.\n' + RESETCOLORS
            print PURPLE + BOLD + UNDERLINE + "Make sure to run the program again with the '-p' option after the system reboots to complete the update procedure!\n" + RESETCOLORS
        else:
            print RED + BOLD + '\nThe system update failed to complete successfully.  Address the failed update tasks (' + taskFailureList + ') and then reboot the system for the changes to take affect.\n' + RESETCOLORS
    else:
        try:
            logBaseDir = re.sub('\\s+', '', patchResourceDict['logBaseDir']).rstrip('/')
            postUpdateResumeLog = re.sub('\\s+', '', patchResourceDict['postUpdateResumeLog'])
            postUpdateResumeLog = logBaseDir + '/' + postUpdateResumeLog
        except KeyError as err:
            logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
            print RED + 'The resource key for the post update resume log was not present in the resource file; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)

        resumeDict = {}
        try:
            with open(postUpdateResumeLog) as f:
                for line in f:
                    line = line.strip()
                    if len(line) == 0 or re.match('^\\s*#', line) or re.match('^\\s+$', line):
                        continue
                    else:
                        line = re.sub('[\'"]', '', line)
                        key, val = line.split('=')
                        key = key.strip()
                        resumeDict[key] = val.strip()

        except IOError as err:
            logger.error('Unable to get the post update information from resume log.\n' + str(err))
            print RED + 'Unable to get the post update information from resume log; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)

        count = 2
        postUpdateTaskStatusDict = {}
        if 'isServiceguardSystem' in resumeDict:
            if resumeDict['isServiceguardSystem'] == 'yes':
                original_sigint_handler = signal.getsignal(signal.SIGINT)
                original_sigquit_handler = signal.getsignal(signal.SIGQUIT)

				
#from modules.deadman import BuildDeadmanDriver

                buildDeadmanDriver = BuildDeadmanDriver()
                s = SignalHandler(buildDeadmanDriver)
                signal.signal(signal.SIGINT, s.signal_handler)
                signal.signal(signal.SIGQUIT, s.signal_handler)
                print GREEN + 'Phase ' + str(count) + ': Building and installing the deadman driver.' + RESETCOLORS
                workerThread = Thread(target=buildDeadmanDriver.buildDeadmanDriver, args=(loggerName,))
                workerThread.start()
                while 1:
                    time.sleep(0.1)
                    if not workerThread.is_alive():
                        postUpdateTaskStatusDict['buildDeadmanDriver'] = buildDeadmanDriver.getCompletionStatus()
                        break
                    response = s.getResponse()
                    if response != '':
                        if response == 'y':
                            buildDeadmanDriver.endTask()

                signal.signal(signal.SIGINT, original_sigint_handler)
                signal.signal(signal.SIGQUIT, original_sigquit_handler)
                count += 1
#from modules.fusionIO import UpdateFusionIO
        if 'isFusionIOSystem' in resumeDict:
            if resumeDict['isFusionIOSystem'] == 'yes':
                original_sigint_handler = signal.getsignal(signal.SIGINT)
                original_sigquit_handler = signal.getsignal(signal.SIGQUIT)
				


                updateFusionIO = UpdateFusionIO()
                s = SignalHandler(updateFusionIO)
                signal.signal(signal.SIGINT, s.signal_handler)
                signal.signal(signal.SIGQUIT, s.signal_handler)
                if resumeDict['firmwareUpdateRequired'] == 'yes':
                    print GREEN + 'Phase ' + str(count) + ': Updating FusionIO firmware, driver, and software.' + RESETCOLORS
                    workerThread = Thread(target=updateFusionIO.updateFusionIO, args=(patchResourceDict.copy(), loggerName), kwargs={'firmwareUpdateRequired': resumeDict['firmwareUpdateRequired'],
                     'busList': resumeDict['busList'],
                     'iomemory-vslBackup': resumeDict['iomemory-vslBackup']})
                    workerThread.start()
                else:
                    print GREEN + 'Phase ' + str(count) + ': Updating FusionIO driver and software.' + RESETCOLORS
                    workerThread = Thread(target=updateFusionIO.updateFusionIO, args=(patchResourceDict.copy(), loggerName), kwargs={'firmwareUpdateRequired': resumeDict['firmwareUpdateRequired'],
                     'iomemory-vslBackup': resumeDict['iomemory-vslBackup']})
                    workerThread.start()
                while 1:
                    time.sleep(0.1)
                    if not workerThread.is_alive():
                        postUpdateTaskStatusDict['updateFusionIO'] = updateFusionIO.getCompletionStatus()
                        break
                    response = s.getResponse()
                    if response != '':
                        if response == 'y':
                            updateFusionIO.endTask()

                signal.signal(signal.SIGINT, original_sigint_handler)
                signal.signal(signal.SIGQUIT, original_sigquit_handler)
        taskFailureList = ''
        for key, value in postUpdateTaskStatusDict.iteritems():
            if value == 'Failure':
                if taskFailureList == '':
                    taskFailureList += key
                else:
                    taskFailureList += ', ' + key

        if taskFailureList == '':
            print GREEN + '\nThe system update has successfully completed.  Reboot the system for the changes to take affect.\n' + RESETCOLORS
        else:
            print RED + BOLD + '\nThe system update failed to complete successfully.  Address the failed post update tasks (' + taskFailureList + ') and then reboot the system for the changes to take affect.\n' + RESETCOLORS


main()