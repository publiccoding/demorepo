# Embedded file name: ./csurUpdate.py
import re
import signal
import time
import sys
import os
import optparse
import subprocess
import traceback
import datetime
from threading import Thread
from modules.csurUpdateUtils import RED, RESETCOLORS, SignalHandler
from modules.csurUpdateInitialize import Initialize
from modules.computeNodeUpdate import ComputeNodeUpdate
from modules.updateReleaseInformation import updateVersionInformationFile
from modules.cursesThread import CursesThread

def main():
    if os.geteuid() != 0:
        print RED + 'You must be root to run this program; exiting program execution.' + RESETCOLORS
        exit(1)
    programVersion = '1.4-3'
    usage = 'usage: %prog [[-h] [-r] [-s] [-u] [-v]]'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-r', action='store_true', default=False, help='This option is used to generate a version report.')
    parser.add_option('-s', action='store_true', default=False, help='This option is used when upgrading Servicegaurd nodes to indicate which node is the primary node; the secondary node should already be upgraded before envoking this option.')
    parser.add_option('-u', action='store_true', default=False, help='This option is used to update the local OS hard drives before the mirror is split.')
    parser.add_option('-v', action='store_true', default=False, help="This option is used to display the application's version.")
    options, args = parser.parse_args()
    if options.v:
        print os.path.basename(sys.argv[0]) + ' ' + programVersion
        exit(0)
    if options.r and options.u or options.r and options.s or options.s and options.u:
        print RED + "Options 'r', 's', and 'u' are mutually exclusive; please try again; exiting program execution." + RESETCOLORS
        exit(1)
    if options.r:
        versionInformationLogOnly = True
    else:
        versionInformationLogOnly = False
    if options.u:
        updateOSHarddrives = True
    else:
        updateOSHarddrives = False
    if options.s:
        command = 'dmidecode -s system-product-name'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        out = out.strip()
        if result.returncode != 0:
            print RED + "Unable to get the system's model information (dmidecode -s system-product-name); exiting program execution." + RESETCOLORS
            exit(1)
        try:
            systemModel = re.match('[a-z,0-9]+\\s+(.*)', out, re.IGNORECASE).group(1).replace(' ', '')
        except AttributeError as err:
            print RED + "There was a system model match error when trying to match against '" + out + "':\n" + str(err) + '.' + RESETCOLORS
            exit(1)

        if systemModel != 'DL380pGen8' and systemModel != 'DL360pGen8':
            print RED + "The '-s' option can only be used on NFS Serviceguard systems (DL380pGen8 or DL360pGen8)." + RESETCOLORS
            exit(1)
    csurBasePath = '/hp/support/csur'
    currentLogDir = datetime.datetime.now().strftime('Date_%d%H%M%S%b%Y')
    logBaseDir = csurBasePath + '/log/' + currentLogDir + '/'
    sessionScreenLog = logBaseDir + 'sessionScreenLog.log'
    cursesLog = logBaseDir + 'cursesLog.log'
    try:
        os.mkdir(logBaseDir)
    except OSError as err:
        print RED + 'Unable to create the current log directory ' + logBaseDir + '; fix the problem and try again; exiting program execution.\n' + str(err) + RESETCOLORS
        exit(1)

    try:
        cursesThread = CursesThread(sessionScreenLog, cursesLog)
        cursesThread.daemon = True
        cursesThread.start()
        initialize = Initialize(cursesThread)
        csurResourceDict = initialize.init(csurBasePath, logBaseDir, programVersion, versionInformationLogOnly, updateOSHarddrives)
        if options.s:
            csurResourceDict['sgNode1'] = True
        else:
            csurResourceDict['sgNode1'] = False
        if options.r:
            cursesThread.insertMessage(['informative', 'The system version report has been created and is in the log directory.'])
            cursesThread.insertMessage(['info', ' '])
            if len(csurResourceDict['hardDrivesMissingFirmware']) != 0:
                cursesThread.insertMessage(['warning', 'Hard drive firmware was missing for the following hard drives: ' + csurResourceDict['hardDrivesMissingFirmware'] + '; make sure to file a bug report.'])
                cursesThread.insertMessage(['info', ' '])
        elif len(csurResourceDict['componentListDict']['computeNodeList']) == 0 and len(csurResourceDict['hardDrivesMissingFirmware']) != 0:
            cursesThread.insertMessage(['error', "The compute node's local OS hard drives are not being updated, since firmware for the hard drives was missing."])
            cursesThread.insertMessage(['info', ' '])
            cursesThread.insertMessage(['error', 'Hard drive firmware was missing for the following hard drives: ' + csurResourceDict['hardDrivesMissingFirmware'] + '; make sure to file a bug report.'])
        elif len(csurResourceDict['componentListDict']['computeNodeList']) == 0:
            cursesThread.insertMessage(['informative', 'The compute node is already up to date; no action taken.'])
        else:
            timerThreadLocation = 1
            computeNodeDict = csurResourceDict['componentListDict']['computeNodeList'][0].getComputeNodeDict()
            hostname = computeNodeDict['hostname']
            if updateOSHarddrives:
                cursesThread.insertMessage(['informative', 'Phase 2: Updating compute node ' + hostname + "'s hard drives that need to be updated."])
            elif len(csurResourceDict['hardDrivesMissingFirmware']) != 0:
                cursesThread.insertMessage(['warning', 'Phase 2: Updating the compute node ' + hostname + "'s components that need to be updated, however, hard drive firmware was missing for the following hard drives: " + csurResourceDict['hardDrivesMissingFirmware'] + '; make sure to file a bug report.'])
            else:
                cursesThread.insertMessage(['informative', 'Phase 2: Updating the compute node ' + hostname + "'s components that need to be updated."])
            computeNodeUpdate = ComputeNodeUpdate(cursesThread, csurResourceDict.copy(), timerThreadLocation)
            original_sigint_handler = signal.getsignal(signal.SIGINT)
            original_sigquit_handler = signal.getsignal(signal.SIGQUIT)
            s = SignalHandler(cursesThread)
            signal.signal(signal.SIGINT, s.signal_handler)
            signal.signal(signal.SIGQUIT, s.signal_handler)
            workerThread = Thread(target=computeNodeUpdate.updateComputeNodeComponents)
            workerThread.start()
            while 1:
                time.sleep(0.1)
                if not workerThread.is_alive():
                    break
                response = s.getResponse()
                if response != '':
                    if response == 'y':
                        computeNodeUpdate.endTask()
                        cursesThread.join()
                        exit(1)

            signal.signal(signal.SIGINT, original_sigint_handler)
            signal.signal(signal.SIGQUIT, original_sigquit_handler)
            componentProblemDict = computeNodeUpdate.getUpdateComponentProblemDict()
            if not updateOSHarddrives:
                updateVersionInformationFileResult = updateVersionInformationFile(csurResourceDict.copy())
            cursesThread.insertMessage(['info', ' '])
            if len(componentProblemDict['Software']) == 0 and len(componentProblemDict['Drivers']) == 0 and len(componentProblemDict['Firmware']) == 0:
                if not updateOSHarddrives:
                    if not updateVersionInformationFileResult:
                        cursesThread.insertMessage(['warning', 'The update of compute node ' + hostname + ' completed succesfully, however, the version information file update failed; check the log file for errors and update the file manually.'])
                        cursesThread.insertMessage(['info', ' '])
                        if computeNodeDict['externalStoragePresent']:
                            cursesThread.insertMessage(['final', 'Once the version information file is updated, power cycle the attached storage controller(s) and reboot the system for the changes to take effect.'])
                        else:
                            cursesThread.insertMessage(['final', 'Once the version information file is updated, reboot the system for the changes to take effect.'])
                    else:
                        cursesThread.insertMessage(['informative', 'The update of compute node ' + hostname + ' completed succesfully.'])
                        cursesThread.insertMessage(['info', ' '])
                        if computeNodeDict['externalStoragePresent']:
                            cursesThread.insertMessage(['final', 'Power cycle the attached storage controller(s) and reboot the system for the changes to take effect.'])
                        else:
                            cursesThread.insertMessage(['final', 'Reboot the system for the changes to take effect.'])
                else:
                    cursesThread.insertMessage(['informative', 'The update of compute node ' + hostname + ' completed succesfully.'])
                    cursesThread.insertMessage(['info', ' '])
                    cursesThread.insertMessage(['final', 'Reboot the system for the changes to take effect.'])
            elif not updateOSHarddrives:
                errorMessage = 'The following components encountered errors during the update of compute node ' + hostname + '; check the log file for errors:\n'
                if len(componentProblemDict['Software']) != 0:
                    if 'rpmRemovalFailure' not in componentProblemDict['Software']:
                        errorMessage += 'Software: ' + ', '.join(componentProblemDict['Software'].keys()) + '\n'
                    elif len(componentProblemDict['Software']) == 1:
                        errorMessage += 'Software: ' + componentProblemDict['Software']['rpmRemovalFailure'] + '\n'
                    else:
                        errorMessage += 'Software: ' + componentProblemDict['Software']['rpmRemovalFailure'] + ', '
                        del componentProblemDict['Software']['rpmRemovalFailure']
                        errorMessage += ', '.join(componentProblemDict['Software'].keys()) + '\n'
                if len(componentProblemDict['Drivers']) != 0:
                    errorMessage += 'Drivers: ' + ', '.join(componentProblemDict['Drivers'].keys()) + '\n'
                if len(componentProblemDict['Firmware']) != 0:
                    errorMessage += 'Firmware: ' + ', '.join(componentProblemDict['Firmware'].keys()) + '\n'
                if not updateVersionInformationFileResult:
                    errorMessage += 'Also, the version information file update failed; check the log file for errors and update the file manually.'
                cursesThread.insertMessage(['error', errorMessage])
            else:
                cursesThread.insertMessage(['error', 'Errors were encountered while updating compute node ' + hostname + "'s hard drive firmware; check the log file for errors."])
        cursesThread.insertMessage(['info', ' '])
        cursesThread.getUserInput(['informative', 'Press enter to exit.'])
        while not cursesThread.isUserInputReady():
            time.sleep(0.1)

    except Exception:
        cursesThread.join()
        traceback.print_exc()
        exit(1)
    finally:
        cursesThread.join()


main()