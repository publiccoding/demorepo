#!/usr/bin/python


import logging
import optparse
import os
import sys
from modules.rootLogin import ConfigureRootLogin
from modules.hardeningUtils import (RED, GREEN, RESETCOLORS)
from modules.hardeningInitialize import Initialize
from modules.ctrlAltDel import ConfigureCtrlAltDel
from modules.umaskHome import ConfigureUmaskHomeDir
from modules.systemFiles import ConfigureSystemFiles


'''
This function is used to initialize the program.  It performs the following:
	1.  Ensures that the program is being ran as root.
	2.  Sets up logging.
	3.  Returns a dictionary (hash) containing the resource files resources and other references needed later on in the program.
'''
def init():
	#The program can only be ran by root.
	if os.geteuid() != 0:
		print(RED + "You must be root to run this program." + RESETCOLORS)
		exit(1)

	usage = 'usage: %prog [-d] [-v] [-h]'

	parser = optparse.OptionParser(usage=usage)

	parser.add_option('-d', action='store_true', default=False, help='This option is used when problems are encountered and additional debug information is needed.')
	parser.add_option('-v', action='store_true', default=False, help='This option is used to display the program\'s version.')

	(options, args) = parser.parse_args()

	programName = os.path.basename(sys.argv[0])

	programVersion = 'v1.0-rc1'

	hardeningBasePath = '/hp/support/hardening'

	if options.v:
		print programName + " " + programVersion
		exit(0)

        if options.d:
                debug = True
        else:
                debug = False

	initialize = Initialize()

	return initialize.init(hardeningBasePath, debug, programVersion)

#End init()

def main():
	hardeningResourceDict = init()

	try:
		loggerName = hardeningResourceDict['loggerName']
		osDistLevel = hardeningResourceDict['osDistLevel']
		permissionsResourceFile = hardeningResourceDict['hardeningBasePath'] + '/resourceFiles/' + hardeningResourceDict['permissionsResourceFile']
		logBaseDir = hardeningResourceDict['logBaseDir']
	except AttributeError as err:
		print(RED + "An AttributeError was encountered; exiting program execution: " + str(err) + RESETCOLORS)
		exit(1)
	except KeyError as err:
		print(RED + "An KeyError was encountered; exiting program execution: " + str(err) + RESETCOLORS)
		exit(1)

	logger = logging.getLogger(loggerName)

	configureRootLogin = ConfigureRootLogin(loggerName)

	if not configureRootLogin.configureSSHLogin():
		print("Errors were encountered while configuring root login for ssh.")

	if not configureRootLogin.configureTTYLogin():
		print("Errors were encountered while configuring root login for tty1.")
	
	conifgureCtrlAtlDel = ConfigureCtrlAltDel()

	if not conifgureCtrlAtlDel.disableCtrlAltDel(loggerName, osDistLevel):
		print("Errors were encountered while disabling the ctrl+alt+del key sequence.")

	configureUmaskHomeDir = ConfigureUmaskHomeDir(loggerName)

	if not configureUmaskHomeDir.updateUmask():
		print("Errors were encountered while setting the system's umask.")

	if not configureUmaskHomeDir.updateHomeDir():
		print("Errors were encountered while setting the permissions for /home and the user's home directory.")

	configureSystemFiles = ConfigureSystemFiles(loggerName)

	if not configureSystemFiles.updatePermissions(permissionsResourceFile, logBaseDir):
		print("Errors were encountered while setting the permissions for system files.")
		
	
#End main()


#####################################################################################################
# Main program starts here.
#####################################################################################################
main()
