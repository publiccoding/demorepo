#!/usr/bin/python

import logging
import os
import optparse
import subprocess
import time
import socket
import re
import signal
import computeNode
import csurUtils
import csurUpdate


command = "rpm -q hp-health"
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()

if result.returncode == 0:
       command = "/etc/init.d/hp-health stop"

       timedProcessThread = csurUtils.TimedProcessThread(command, 5)
       print "start"

       timedProcessThread.start()
       print "start"

       returncode = timedProcessThread.join()

       print "returncode = ", returncode

print "done with test"

