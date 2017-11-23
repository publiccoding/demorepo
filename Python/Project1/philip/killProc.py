#!/usr/bin/python

import subprocess
import os
import signal
import threading


class TimedProcessThread(threading.Thread):

	def __init__(self, cmd, seconds):
		threading.Thread.__init__(self)
		self.cmd = cmd
		self.seconds = seconds
		self.returncode = 1 

	def run(self):
		result = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid, shell=True)
		pid = result.pid
		print "pid = ", pid
		timer = threading.Timer(self.seconds, self.killProcessGroup, [pid])
		try:
			timer.start()
			out, err = result.communicate()
			self.returncode = result.returncode
		finally:
			timer.cancel()

	def killProcessGroup(self, pid):
		pgid = os.getpgid(pid)
		print "pgid = ", pgid
		os.killpg(pgid, signal.SIGKILL)

	def join(self):
		threading.Thread.join(self)
		return self.returncode

#command = "rpm -q hp-health"
#result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
#out, err = result.communicate()
#
#if result.returncode == 0:
#	command = "/etc/init.d/hp-health stop"
#	#command = "./test.sh"
#
#	timedProcessThread = csurUtils.TimedProcessThread(command, 5)
#	print "start"
#
#	timedProcessThread.start()
#	print "start"
#
#	returncode = timedProcessThread.join()
##
#	print "returncode = ", returncode
#
#print "done with test"
#####
