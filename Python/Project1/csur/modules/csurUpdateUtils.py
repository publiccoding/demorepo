# Embedded file name: ./csurUpdateUtils.py
import time
import sys
import threading
import logging
import subprocess
import signal
import os
import re
YELLOW = '\x1b[33m'
RED = '\x1b[31m'
GREEN = '\x1b[32m'
BLUE = '\x1b[34m'
PURPLE = '\x1b[35m'
BOLD = '\x1b[1m'
UNDERLINE = '\x1b[4m'
RESETCOLORS = '\x1b[0m'

class SignalHandler:

    def __init__(self, cursesThread):
        self.response = ''
        self.cursesThread = cursesThread

    def signal_handler(self, signum, frame):
        regex = '^(y|n)$'
        self.cursesThread.insertMessage(['error', 'The update should not be interrupted once started, since it could put the system in an unknown state.'])
        while 1:
            self.cursesThread.insertMessage(['info', '    Do you really want to interrupt the update [y|n]: '])
            self.cursesThread.getUserInput(['info', ' '])
            while not self.cursesThread.isUserInputReady():
                time.sleep(0.1)

            self.response = self.cursesThread.getUserResponse().strip()
            self.response = self.response.lower()
            if not re.match(regex, self.response):
                self.cursesThread.insertMessage(['error', '    A valid response is y|n.  Please try again.'])
                continue
            break

    def getResponse(self):
        return self.response


class TimeFeedbackThread(threading.Thread):

    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        if 'componentMessage' in kwargs:
            self.componentMessage = kwargs['componentMessage']
        else:
            self.componentMessage = ''
        if 'componentValue' in kwargs:
            self.componentValue = kwargs['componentValue']
        else:
            self.componentValue = ''
        if 'event' in kwargs:
            self.event = kwargs['event']
        else:
            self.event = ''
        self.stop = False

    def run(self):
        i = 0
        if self.event != '':
            self.event.set()
        while self.stop != True:
            if self.event != '':
                self.event.wait()
            timeStamp = time.strftime('%H:%M:%S', time.gmtime(i))
            if self.componentValue != '':
                feedbackMessage = self.componentMessage + ' ' + self.componentValue + ' .... ' + timeStamp
            else:
                feedbackMessage = self.componentMessage + ' .... ' + timeStamp
            sys.stdout.write('\r' + feedbackMessage)
            sys.stdout.flush()
            time.sleep(1.0)
            i += 1

    def stopTimer(self):
        self.stop = True

    def pauseTimer(self):
        self.event.clear()

    def resumeTimer(self):
        self.event.set()

    def updateComponentMessage(self, message):
        self.componentMessage = message


class TimedProcessThread(threading.Thread):

    def __init__(self, cmd, seconds, loggerName):
        threading.Thread.__init__(self)
        self.cmd = cmd
        self.seconds = seconds
        self.loggerName = loggerName
        self.logger = logging.getLogger(self.loggerName)
        self.returncode = 1
        self.done = False
        self.timedOut = False
        self.err = ''
        self.out = ''
        self.pid = 0

    def run(self):
        result = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid, shell=True)
        self.pid = result.pid
        timer = threading.Timer(self.seconds, self.killProcesses, [self.pid])
        try:
            timer.start()
            self.out, self.err = result.communicate()
            self.returncode = result.returncode
            self.done = True
        finally:
            timer.cancel()

    def killProcesses(self, pid):
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGKILL)
        self.timedOut = True
        self.done = True

    def getCompletionStatus(self):
        while not self.timedOut and not self.done:
            time.sleep(2)

        self.logger.info('The output of the timed process command (' + self.cmd + ') was: ' + self.out.strip())
        if self.timedOut:
            return ['timedOut']
        elif self.returncode == 0:
            return ['Succeeded']
        else:
            return ['Failed', self.err]

    def getProcessPID(self):
        return self.pid


class InvalidPasswordError(Exception):

    def __init__(self, message):
        self.message = message


class InUseError(Exception):

    def __init__(self, message):
        self.message = message


class CouldNotDetermineError(Exception):

    def __init__(self, message):
        self.message = message


class FileUploadError(Exception):

    def __init__(self, message):
        self.message = message


class TimerThread(threading.Thread):

    def __init__(self, message):
        threading.Thread.__init__(self)
        self.stop = False
        self.timeStampe = None
        self.message = message
        return

    def run(self):
        i = 0
        while self.stop != True:
            self.timeStamp = time.strftime('%H:%M:%S', time.gmtime(i))
            time.sleep(1.0)
            i += 1

    def stopTimer(self):
        self.stop = True

    def getTimeStamp(self):
        return self.timeStamp

    def getMessage(self):
        return self.message