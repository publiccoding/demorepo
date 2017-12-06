# Embedded file name: ./spUtils.py
import threading
import time
import sys
YELLOW = '\x1b[33m'
RED = '\x1b[31m'
GREEN = '\x1b[32m'
BLUE = '\x1b[34m'
PURPLE = '\x1b[35m'
BOLD = '\x1b[1m'
UNDERLINE = '\x1b[4m'
RESETCOLORS = '\x1b[0m'

class SignalHandler:

    def __init__(self, processorObject):
        self.response = ''
        self.processorObject = processorObject

    def signal_handler(self, signum, frame):
        self.processorObject.pauseTimerThread()
        warning = RED + '\nThe update should not be interrupted once started, since it could put the system in an unknown state.' + RESETCOLORS
        print warning + '\n'
        while 1:
            var = 'Do you really want to interrupt the update [y|n]: '
            self.response = raw_input('Do you really want to interrupt the update [y|n]: ')
            if self.response.lower() == 'y' or self.response.lower() == 'n':
                self.processorObject.resumeTimerThread()
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
            if i == 0:
                sys.stdout.write(feedbackMessage)
            else:
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