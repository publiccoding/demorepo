# Embedded file name: ./updateZyppConf.py
from spUtils import RED, RESETCOLORS
import subprocess
import logging
import datetime
import shutil

def updateZyppConf(loggerName):
    logger = logging.getLogger(loggerName)
    zyppConfigurationFile = '/etc/zypp/zypp.conf'
    logger.info("Updating the system's zypper configuration file.")
    dateTimestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    try:
        shutil.copy2(zyppConfigurationFile, zyppConfigurationFile + '.' + dateTimestamp)
    except IOError as err:
        logger.error("Unable to make a backup of the system's zypper configuration file.\n" + str(err))
        print RED + "Unable to make a backup of the system's zypper configuration file; check the log file for errors; exiting program execution." + RESETCOLORS
        exit(1)

    command = 'egrep "^\\s*multiversion\\s*=\\s*" ' + zyppConfigurationFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to get the multiversion resource from ' + zyppConfigurationFile + ' was: ' + out.strip())
    if result.returncode == 0:
        command = "sed -i '0,/^\\s*multiversion\\s*=\\s*.*$/s//multiversion = provides:multiversion(kernel)/' " + zyppConfigurationFile
    else:
        command = "sed -i '0,/^\\s*#\\+\\s*multiversion\\s*=\\s*.*$/s//multiversion = provides:multiversion(kernel)/' " + zyppConfigurationFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to update the multiversion resource was: ' + out.strip())
    if result.returncode != 0:
        logger.error("Unable to update the system's zypper configuration file " + zyppConfigurationFile + '.\n' + err)
        print RED + "Unable to the system's zypper configuration file ; check the log file for errors; exiting program execution." + RESETCOLORS
        exit(1)
    command = 'egrep "^\\s*multiversion.kernels\\s*=\\s*" ' + zyppConfigurationFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to get the multiversion.kernels resource from ' + zyppConfigurationFile + ' was: ' + out.strip())
    if result.returncode == 0:
        command = "sed -i '0,/^\\s*multiversion.kernels\\s*=\\s*.*$/s//multiversion.kernels = latest,latest-1,running/' " + zyppConfigurationFile
    else:
        command = "sed -i '0,/^\\s*#\\+\\s*multiversion.kernels\\s*=\\s*.*$/s//multiversion.kernels = latest,latest-1,running/' " + zyppConfigurationFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to update the multiversion.kernels resource was: ' + out.strip())
    if result.returncode != 0:
        logger.error("Unable to update the system's zypper configuration file " + zyppConfigurationFile + '.\n' + err)
        print RED + "Unable to the system's zypper configuration file ; check the log file for errors; exiting program execution." + RESETCOLORS
        exit(1)
    logger.info("Done updating the system's zypper configuration file.")