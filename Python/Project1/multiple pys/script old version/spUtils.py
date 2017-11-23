import threading
import time
import sys


#Colors available to use when printing messages to screen.
YELLOW = '\033[33m'
RED = '\033[31m'
GREEN = '\033[32m'
BLUE = '\033[34m'
PURPLE = '\033[35m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
RESETCOLORS = '\033[0m'


'''
This is a custom class for handling the signals we want to catch (SIGINT, SIGQUIT).  It takes an object that should 
not be interrupted, which also creates a timer thread that needs to be paused during the signal handling event.
'''
class SignalHandler():

        def __init__(self, processorObject):
                self.response = ''
                self.processorObject = processorObject
        #End __init__(self, processorObject):


        '''
        This function is used to warn users of the consequences of interrupting the software update process.
        '''
        def signal_handler(self, signum, frame):

                self.processorObject.pauseTimerThread()

                warning = RED + "\nThe update should not be interrupted once started, since it could put the system in an unknown state." + RESETCOLORS
                print warning + '\n'

                while 1:
                        var =  "Do you really want to interrupt the update [y|n]: "
                        self.response = raw_input("Do you really want to interrupt the update [y|n]: ")

                        if self.response.lower() == 'y' or self.response.lower() == 'n':
                                self.processorObject.resumeTimerThread()
                                break

        #End signal_handler(self, signum, frame):


        '''
        This function is used to get the users response to interrupting the software update process.
        '''
        def getResponse(self):
                return self.response
        #End getResponse(self):

#End SignalHandler():


'''
This class is used to provide feedback in time expired during long running tasks.
The componentValue is the component being updated and componentMessage is the
message that one wants to be displayed.
It also takes a thread event when a timer thread is involved for a process that should 
not be interrupted.
'''
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

        #End __init__(self, componentMessage, **kwargs):

	
	'''
	This fuction prints out the timer message when the thread is in a run state.
	'''
        def run(self):

                i = 0

                if self.event != '':
                        self.event.set()

                while self.stop != True:
                        if self.event != '':
                                self.event.wait()
                        timeStamp = time.strftime("%H:%M:%S", time.gmtime(i))

                        if self.componentValue != '':
                                feedbackMessage = self.componentMessage + " " +  self.componentValue + " .... " + timeStamp
                        else:
                                feedbackMessage = self.componentMessage + " .... " + timeStamp
			
			if i == 0:
                                sys.stdout.write(feedbackMessage)
                        else:
                                sys.stdout.write('\r' + feedbackMessage)

                        sys.stdout.flush()

                        time.sleep(1.0)

                        i+=1

        #End run(self):


	'''
	This function cancels the timer.
	'''
        def stopTimer(self):
                self.stop = True
        #End stopTimer(self):


	'''
	This function is used to pause the timer during the time a signal is being handled.
	'''
        def pauseTimer(self):
                self.event.clear()
        #End pauseTimer(self):


	'''
	This function is used to resume the timer after a signal has been handled.
	'''
        def resumeTimer(self):
                self.event.set()
        #End resumeTimer(self):

#End TimeFeedbackThread(threading.Thread)
