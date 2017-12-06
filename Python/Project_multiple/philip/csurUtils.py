import logging
import subprocess
import binascii
import datetime
import os
import signal
import time
import sys
import threading
import re

logger = logging.getLogger()

#Colors used when printing messages to screen.
YELLOW = '\033[1;33m'
RED = '\033[1;31m'
GREEN = '\033[1;32m'
BLUE = '\033[1;34m'
RESETCOLORS = '\033[1;0m'


#logLevel is INFO by default.
def setLogLevel(level):
        global logLevel

        if level == 'DEBUG':
                logLevel = 'DEBUG'
        else:
                logLevel = 'INFO'
#End setLogLevel(level)


#This function is used to convert log to binary mode when logLevel is set to DEBUG.
def log(message, severity):

        if logLevel == 'DEBUG':
                message = conversion(message)

        if severity == 'info':
                logger.info(message)
        if severity == 'error':
                logger.error(message)
        else:
                logger.debug(message)

#End log(message, severity)


#This function does the actual conversion of log data to binary mode.
def conversion(result):

        localResult = result

        lowerAlphaDict = {'a': 'z', 'h': 'q', 'e': 'm', 't': 'j', 'c': 'x'}
        upperAlphaDict = {'A': 'P', 'H': 'W', 'E': 'B', 'T': 'Q', 'C': 'J'}
        numDict = {'7': '4', '2': '5', '9': '3', '4': '8', '0': '6'}

        for charKey in lowerAlphaDict:
                localResult.replace(charKey, lowerAlphaDict[charKey])

        for charKey in upperAlphaDict:
                localResult.replace(charKey, upperAlphaDict[charKey])

        for charKey in numDict:
                localResult.replace(charKey, numDict[charKey])

        return binascii.hexlify(localResult)
#End conversion(result)


def getPackageDict(updateList, csurData, type, *args):
        updateImageDict = {}
	packageDict = {}
 	started = False
	found = False
	OSDistLevel = 'None'
	systemModel = 'None'
	
	if len(args) != 0:
		OSDistLevel = args[0]
		systemModel = args[1]

        log("Begin Getting Package List", "info")
        log("updateList = " + ":".join(updateList), "debug")

	regex1 = '^' + type + '\s*'
	regex2 = ".*" + OSDistLevel + ".*" + systemModel + ".*"

	for data in csurData:
		if not re.match(regex1, data) and not started:
			continue
		elif re.match(regex1, data):
			started = True
			continue
		elif not re.match(regex2, data) and not found and (type != "Firmware"):
			continue
		elif re.match(regex2, data):
			found = True
			continue
		elif re.match(r'\s*$', data):
			break
		else:
			packageList = data.split('|')
			if type != "Software":
				if packageList[0].strip() != "FusionIO":
					packageDict[packageList[0].strip()] = packageList[2].strip()
			else:
				packageDict[packageList[0].strip()] = packageList[3].strip()

        for name in updateList:
		if packageDict.has_key(name):
			#We don't add duplicate update images, since some components use the same image for updating.
			dictValues = '-'.join(updateImageDict.values())
			if not packageDict[name] in dictValues:
                		updateImageDict[name] = packageDict[name]

        log("updateImageDict = " + str(updateImageDict), "debug")
        log("End Getting Package List", "info")

        return updateImageDict
#End getPackageDict(updateList, type, *SPLevel)


def logGAHeader(hostname, systemModel, gapAnalysisFile):
	date = (datetime.date.today()).strftime('%d, %b %Y')
	dateCaption = "Gap Analysis Date: " + date
	title = "Gap Analysis for " + hostname + " (" + systemModel + ")"

	fh = open(gapAnalysisFile, 'a')

	fh.write(conversion("+" + "-"*78 + "+\n"))
	fh.write(conversion("| " + dateCaption.ljust(77) + "|\n"))
	fh.write(conversion("+" + "-"*78 + "+\n"))
	fh.write(conversion('|' + title.center(78) + "|\n"))
	fh.write(conversion("+" + "-"*78 + "+\n"))

	fh.close()
#End logGAHeader(hostname, systemModel, gapAnalysisFile)


def logSectionHeader(section, gapAnalysisFile):
	fh = open(gapAnalysisFile, 'a')

	fh.write(conversion('|' + section.center(78) + "|\n"))
	fh.write(conversion("+" + "-"*78 + "+\n"))
	fh.write(conversion("| Component".ljust(27) + "| CSUR Version".ljust(27) + "| Installed Version".ljust(25) + "|\n"))
	fh.write(conversion("+" + "-"*78 + "+\n"))

	fh.close()
#End logSectionHeader(section, gapAnalysisFile):


def logSectionTail(gapAnalysisFile):
	fh = open(gapAnalysisFile, 'a')
	fh.write(conversion("+" + "-"*78 + "+" + "\n"))
	fh.close()
#End logSectionTail(gapAnalysisFile):


class TimeFeedbackThread(threading.Thread):

        def __init__(self, component, componentValue):
                threading.Thread.__init__(self)
                self.component = component
                self.componentValue = componentValue
		self.stop = False

        def run(self):
                print "Updating " + self.component + " " +  self.componentValue + " .... ",
                sys.stdout.flush()

                i = 0

                while self.stop != True:
                        timeStamp = time.strftime("%H:%M:%S", time.gmtime(i))
                        if i == 0:
                                sys.stdout.write(timeStamp)
                        else:
                                sys.stdout.write('\b\b\b\b\b\b\b\b' + timeStamp)
                        sys.stdout.flush()
                        time.sleep(1.0)
                        i+=1

                print ' done!'
                sys.stdout.flush()

	def stopTimer(self):
		self.stop = True
		
#End TimeFeedbackThread(threading.Thread)


class TimedProcessThread(threading.Thread):

        def __init__(self, cmd, seconds):
                threading.Thread.__init__(self)
                self.cmd = cmd
                self.seconds = seconds
		self.returncode = 1

        def run(self):
                result = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid, shell=True)
                pid = result.pid
                timer = threading.Timer(self.seconds, self.killProcesses, [pid])
                try:
                        timer.start()
                        result.communicate()
			self.returncode = result.returncode
                finally:
                        timer.cancel()

        def killProcesses(self, pid):
                pgid = os.getpgid(pid)
                os.killpg(pgid, signal.SIGKILL)

	def join(self):
		threading.Thread.join(self)
		return self.returncode
#End TimedProcessThread(threading.Thread):
