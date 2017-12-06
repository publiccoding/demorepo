#!/usr/bin/python


import re
import shutil
import os
import sys
import subprocess
import shutil


RED = '\033[31m'
GREEN = '\033[32m'
RESETCOLORS = '\033[0m'

#This is the base path for the patch directory.
patchDir = '/hp/support/patches'

#Get the location of where the archive was extracted to, so that we can add it to the archive image name.
executableFullPath = os.path.abspath(sys.argv[0])
executableName = os.path.basename(sys.argv[0])
executablePath = re.sub(executableName, '', executableFullPath)

#These are the license files that should be present and that will be installed in /var/share/doc/hpe.
gplLicenses = 'GPL_licenses.txt'
writtenOffer = 'Written_offer.txt'
licenseFileList = [executablePath + gplLicenses, executablePath + writtenOffer]

#This is the directory where the license files will copied to.
hpeLicenseDir = '/usr/share/doc/hpe'

#The program can only be ran by root.
if os.geteuid() != 0:
	print RED + "You must be root to run this program." + RESETCOLORS
	exit(1)

'''
Delete the current patch bundle directory contents, except for the bin directory, so that we start clean.
Also, we want to delete the patch bundle directories that may of been left behind so that they do not contribute
to the root file system's usage check.
'''
if os.path.exists(patchDir):
        dirs = os.listdir(patchDir)

        for dir in dirs:
		#We do not want to delete the bin directory hosting the patch bundle application.
                if dir == 'bin':
                        continue
                else:
			dir = patchDir + '/' + dir

                        try:
                                shutil.rmtree(dir)
                        except IOError as err:
                                print RED + "Unable to delete the current patch bundle related directory (" + dir + "); fix the problem and try again.\n" + str(err) + RESETCOLORS
                                exit(1)

#Get the root file system's usage.  There must be at least 3GB free in order to do the patch update.
command = "df /"
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()

if result.returncode != 0:
	print RED + "Unable to check the available disk space of the root file system; fix the problem and try again.\n" + err + RESETCOLORS
	exit(1)

out = out.strip()

tmpVar = re.match('(.*\s+){3}([0-9]+)\s+', out).group(2)

availableDiskSpace = round(float(tmpVar)/float(1024*1024), 2)

if not availableDiskSpace >= 3:
	print RED + "There is not enough disk space (" + str(availableDiskSpace) + "GB) on the root file system; There needs to be at least 3GB of free space on the root file system; fix the problem and try again." + RESETCOLORS
	exit(1)

command = 'ls ' + executablePath + '*.tgz'
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()

if result.returncode != 0:
	print RED + "Unable to get the patch archive name; fix the problem and try again.\n" + err + RESETCOLORS
	exit(1)

patchArchive = out.strip()
patchArchiveName = re.match(r'.*/(.*\.tgz)', patchArchive).group(1)
patchArchiveMd5sumFile = re.sub('tgz', 'md5sum', patchArchiveName)

#Check the md5sum of the patch archive to make sure it is not corrupt.
command = 'md5sum ' + patchArchive
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()

if result.returncode != 0:
        print RED + "Unable to determine the md5sum of the patch archive (" + patchArchive + "); fix the problem and try again.\n" + err + RESETCOLORS
        exit(1)

patchArchiveMd5sum = re.match('([0-9,a-f]*)\s+', out).group(1)

try:
	with open(patchArchiveMd5sumFile) as f:
		for line in f:
			line = line.strip()
			if patchArchiveName in line:
				patchMd5sum = re.match('([0-9,a-f]*)\s+', out).group(1)
except IOError as err:
        print RED + "Unable to get the md5sum of the patch archive from (" + patchArchiveMd5sumFile + "); fix the problem and try again.\n" + str(err) + RESETCOLORS
        exit(1)

if patchArchiveMd5sum != patchMd5sum:
        print RED + "The patch archive (" + patchArchive + ") is corrupt; fix the problem and try again." + RESETCOLORS
        exit(1)

#Change into the root directory and extract the patch archive.
try:
	os.chdir('/')
except OSError as err:
	print RED + "Could not change into the root (/) directory; fix the problem and try again.\n" + str(err) + RESETCOLORS
	exit(1)

command = 'tar -zxvf ' + patchArchive
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()

if result.returncode != 0:
	print RED + "Unable to extract the patch archive (" + patchArchive + "); fix the problem and try again.\n" + err + RESETCOLORS
	exit(1)

if not os.isdir(hpeLicenseDir):
	try:
		os.mkdir(hpeLicenseDir, 0755)
	except OSError as err:
		print RED + "Unable to create the license directory " + hpeLicenseDir + "; fix the problem and try again.\n" + str(err) + RESETCOLORS
		exit(1)

for file in licenseFileList:
	try:
		shutil.copy(file, hpeLicenseDir)	
	except IOError as err:
		print RED + "Unable to license file " + file + " to " + hpeLicenseDir +"; fix the problem and try again.\n" + str(err) + RESETCOLORS
		exit(1)

print GREEN + "The patch archive has successfully been extracted to (" + patchDir + ") and is ready to install.\n\n" + RESETCOLORS

print RED + "Before installing patches make sure the following tasks have been completed:\n"
print "\t1. The SAP HANA application has been shut down.\n"
print "\t2. The system has been backed up.\n"
print "\t3. If the system is a Gen 1.0 Scale-up, then make sure the log partition is completely backed up.\n"
print "\t4. If the system is a Serviceguard system, then make sure the cluster has been shutdown.\n" 
print RESETCOLORS
