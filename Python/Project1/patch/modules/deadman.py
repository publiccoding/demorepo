# Embedded file name: ./deadman.py
from spUtils import RED, GREEN, RESETCOLORS, TimeFeedbackThread
import subprocess
import logging
import os
import signal
import threading

class BuildDeadmanDriver:
    """
    Use the constructor to create a threading event that will be used to stop and restart the timer thread
    when a signal (SIGINT, SIGQUIT) is captured.
    """

    def __init__(self):
        self.timerController = threading.Event()
        self.timeFeedbackThread = TimeFeedbackThread(componentMessage='Rebuilding and installing the deadman driver', event=self.timerController)
        self.pid = ''
        self.cancelled = 'no'
        self.completionStatus = ''

    def buildDeadmanDriver(self, loggerName):
        sgDriverDir = '/opt/cmcluster/drivers'
        logger = logging.getLogger(loggerName)
        logger.info('Rebuilding and installing the deadman driver for the new kernel.')
        cwd = os.getcwd()
        try:
            os.chdir(sgDriverDir)
        except OSError as err:
            logger.error('Could not change into the deadman drivers directory (' + sgDriverDir + ').\n' + str(err))
            print RED + 'Could not change into the deadman drivers directory; check the log file for errors; the deadman driver will have to be manually built/installed.' + RESETCOLORS
            self.completionStatus = 'Failure'
            return

        driverBuildCommandsList = ['make modules', 'make modules_install', 'depmod -a']
        self.timeFeedbackThread.start()
        for command in driverBuildCommandsList:
            buildCommand = command
            result = subprocess.Popen(buildCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=self.preexec, shell=True)
            self.pid = result.pid
            out, err = result.communicate()
            logger.info('The output of the command (' + command + ') used in building and installing the deadman driver was: ' + out.strip())
            if result.returncode != 0:
                self.timeFeedbackThread.stopTimer()
                self.timeFeedbackThread.join()
                print ''
                if self.cancelled == 'yes':
                    logger.info('The deadman driver build and install was cancelled by the user.')
                    print RED + 'The deadman driver build and install was cancelled; the deadman driver will have to be manually built/installed.' + RESETCOLORS
                else:
                    logger.error('Failed to build and install the deadman driver.\n' + err)
                    print RED + 'Failed to build and install the deadman driver; check the log file for errors; the deadman driver will have to be manually built/installed.' + RESETCOLORS
                self.completionStatus = 'Failure'
                return

        self.timeFeedbackThread.stopTimer()
        self.timeFeedbackThread.join()
        print ''
        try:
            os.chdir(cwd)
        except:
            pass

        logger.info('Done rebuilding and installing the deadman driver for the new kernel.')
        self.completionStatus = 'Success'

    def endTask(self):
        try:
            self.cancelled = 'yes'
            pgid = os.getpgid(self.pid)
            os.killpg(pgid, signal.SIGKILL)
        except OSError:
            pass

    def preexec(self):
        os.setpgrp()

    def getCompletionStatus(self):
        return self.completionStatus

    def pauseTimerThread(self):
        self.timeFeedbackThread.pauseTimer()

    def resumeTimerThread(self):
        self.timeFeedbackThread.resumeTimer()