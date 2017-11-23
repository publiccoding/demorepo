#!/usr/bin/python

import re
import shutil
import os
import sys
import subprocess

#
# RED = '\033[31m'
# GREEN = '\033[32m'
# RESETCOLORS = '\033[0m'



#Get the root file system's usage.  There must be at least 10GB free in order to do the csur update.
command = "df /"
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()

if result.returncode != 0:
	print("Unable to check the available disk space of the root file system; fix the problem and try again.\n"+ err + )
	exit(1)

out = out.strip()

tmpVar = re.match('(.*\s+){3}([0-9]+)\s+', out).group(2)

availableDiskSpace = round(float(tmpVar)/float(1024*1024), 2)

if not availableDiskSpace >= 10:
	print("There is not enough disk space (" + str(availableDiskSpace) + "GB) on the root file system; There needs to be at least 10GB of free space on the root file system; fix the problem and try again.")
	exit(1)
