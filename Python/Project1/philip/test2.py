#!/usr/bin/python

import subprocess
import os
import socket
import datetime

command = "ifconfig -a|egrep -v \"^\s+|^bond|^lo|^\s*$\"|awk '{print $1}'"
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()

nicList = out.splitlines()

print nicList

command = "lspci -v |grep \"Intel Corporation 82599\"|uniq -w 2|awk '{print $1}'"
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()

pciBusList = out.splitlines()

#print pciBusList

nicCheckList = []

for bus in pciBusList:
	for nic in nicList:
		command = "ethtool -i " + nic + "|grep " + bus
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode == 0:
			nicCheckList.append(nic)
			break

print nicCheckList	

for nic in nicCheckList:
	command = "ethtool -i " + nic + "|grep firmware-version|awk '{print $NF}'"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	print out.strip()


def print_format_table():
    """
    prints table of formatted text format options
    """
    for style in xrange(2):
        for fg in xrange(30,38):
            s1 = ''
	    format2 = ''
            for bg in xrange(40,48):
                format = ';'.join([str(style), str(fg), str(bg)])
		format2 += format
          #      s1 += '\x1b[%sm %s \x1b[0m' % (format, format)
            #print s1
            print format2
        print '\n'

#print_format_table()

YELLOW = '\033[1;33m'
RED = '\033[1;31m'
GREEN = '\033[1;32m'
RESETCOLORS = '\033[1;0m'

SOFTWAREUPDATE = 'Software Updated'
SOFTWARENAME = 'Software'
VERSIONTEXT = 'Version'

date = (datetime.date.today()).strftime('%d, %b %Y')
hostname = socket.gethostname()
title = 'Gap Analysis for ' + hostname
os.system('clear')

#print GREEN  + 'Hi Bill' + RESETCOLORS
#print YELLOW + 'Hi Bill' + RESETCOLORS
#print RED + 'Hi Bill' + RESETCOLORS
#print TITLE.center(80, '-')

print 'Gap Analysis Date: ' + date
print '-'*80
print '-' + title.center(78) + '-' 
print '-'*80
print SOFTWARENAME.ljust(40, '*') + VERSIONTEXT.ljust(20, '+') + '|'.rjust(20, '&')
print ('-'*len(SOFTWARENAME))
print ("+" + "-"*78 + "+")
print 'hp-smh-templates'.ljust(40) + '10.1.0-1415.23'
