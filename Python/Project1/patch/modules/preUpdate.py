# Embedded file name: ./preUpdate.py
from spUtils import RED, RESETCOLORS
import subprocess
import shutil
import logging
import os
import re
import datetime

def removeFusionIOPackages(patchResourceDict, loggerName):
    logger = logging.getLogger(loggerName)
    logger.info('Removing FusionIO packages.')
    try:
        fusionIOFirmwareList = patchResourceDict['fusionIOFirmwareVersionList']
        currentFusionIOFirmwareVersion = patchResourceDict['currentFusionIOFirmwareVersion']
        logBaseDir = re.sub('\\s+', '', patchResourceDict['logBaseDir']).rstrip('/')
        postUpdateResumeLog = re.sub('\\s+', '', patchResourceDict['postUpdateResumeLog'])
        postUpdateResumeLog = logBaseDir + '/' + postUpdateResumeLog
        fioStatusLog = re.sub('\\s+', '', patchResourceDict['fioStatusLog'])
        fioStatusLog = logBaseDir + '/' + fioStatusLog
    except KeyError as err:
        logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
        print RED + 'The resource key for the FusionIO firmware list was not present in the resource file; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)

    try:
        open(fioStatusLog, 'w').close()
    except IOError as err:
        logger.error('Unable to access the FusionIO status log (' + fioStatusLog + ') for writing.\n' + str(err))
        print RED + 'Unable to access the FusionIO status log for writing; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)

    command = 'fio-status > ' + fioStatusLog
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to get FusionIO status was: ' + out.strip())
    if result.returncode != 0:
        logger.error("Unable to get the system's FusionIO firmware version.\n" + err)
        print RED + "Unable to get the system's FusionIO firmware version; check the log file for errors; exiting program execution." + RESETCOLORS
        exit(1)
    busList = []
    firmwareUpdateRequired = 'no'
    try:
        with open(fioStatusLog) as f:
            count = 0
            ioDIMMStatusDict = {}
            for line in f:
                line = line.strip()
                if 'Firmware' in line or re.search('PCI:[0-9,a-f]{2}:[0-9]{2}\\.[0-9]{1}', line):
                    if 'Firmware' in line:
                        ioDIMMStatusDict['Firmware'] = line
                    else:
                        ioDIMMStatusDict['bus'] = line
                    count += 1
                if count == 2:
                    fwInstalledVersion = re.match('Firmware\\s+(v.*),\\s+.*[0-9]{6}', ioDIMMStatusDict['Firmware']).group(1)
                    logger.info("The installed FusionIO firmware version was determined to be: '" + fwInstalledVersion + "'.")
                    if fwInstalledVersion not in fusionIOFirmwareList:
                        logger.error('Unable to proceed until the FusionIO firmware is updated, since it is at an unsupported version (' + fwInstalledVersion + ').')
                        print RED + 'Unable to proceed until the FusionIO firmware is updated, since it is at an unsupported version; check the log file for errors; exiting program execution.' + RESETCOLORS
                        exit(1)
                    elif fwInstalledVersion != currentFusionIOFirmwareVersion:
                        firmwareUpdateRequired = 'yes'
                        busList.append(re.match('.*([0-9,a-f]{2}:[0-9]{2}\\.[0-9]{1})', ioDIMMStatusDict['bus']).group(1))
                    ioDIMMStatusDict.clear()
                    count = 0

    except IOError as err:
        logger.error('Unable to get the FusionIO firmware version from the patch resource file.\n' + str(err))
        print RED + 'Unable to get the FusionIO firmware version from the patch resource file; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)

    try:
        f = open(postUpdateResumeLog, 'a')
        f.write('firmwareUpdateRequired = ' + firmwareUpdateRequired + '\n')
        if firmwareUpdateRequired == 'yes':
            f.write("busList = '" + ' '.join(busList) + "'" + '\n')
        dateTimestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        iomemoryCfgBackup = '/etc/sysconfig/iomemory-vsl.' + dateTimestamp
        f.write('iomemory-vslBackup = ' + iomemoryCfgBackup + '\n')
        f.close()
    except IOError as err:
        logger.error('Unable to access the post update resume log (' + postUpdateResumeLog + ') for writing.\n' + str(err))
        print RED + 'Unable to access the post update resume log for writing; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)

    try:
        shutil.copy2('/etc/sysconfig/iomemory-vsl', iomemoryCfgBackup)
    except IOError as err:
        logger.error("Unable to make a backup of the system's iomemory-vsl configuration file.\n" + str(err))
        print RED + "Unable to make a backup of the system's iomemory-vsl configuration file; check the log file for errors; exiting program execution." + RESETCOLORS
        exit(1)

    fusionIOPackageList = ['^fio*',
     '^hp-io-accel-msrv*',
     '^iomemory-vsl*',
     '^libfio*',
     '^libvsl*',
     '^lib32vsl*']
    packageRemovalList = []
    for package in fusionIOPackageList:
        command = 'rpm -qa ' + package
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        var = out.strip().split()
        logger.info('The output of the command (' + command + ') used to get the currently installed FusionIO software was: ' + out.strip())
        if len(var) > 0:
            packageRemovalList.extend(var)

    if firmwareUpdateRequired == 'yes':
        for package in packageRemovalList:
            if 'fio-util' in package:
                packageRemovalList.remove(package)

    packages = ' '.join(packageRemovalList)
    if len(packages) > 0:
        command = 'rpm -e ' + packages
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ') used to remove the currently installed FusionIO software was: ' + out.strip())
        if result.returncode != 0:
            logger.error('Problems were encountered while trying to remove the FusionIO packages.')
            logger.error('The following errors were encountered: ' + err)
            print RED + 'Problems were encountered while trying to remove the FusionIO packages; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)
    return True


def checkOSVersion(patchResourceDict, loggerName):
    logger = logging.getLogger(loggerName)
    logger.info('Checking and getting the OS distribution information.')
    command = 'cat /proc/version'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to get the OS distribution information was: ' + out.strip())
    if result.returncode != 0:
        logger.error('Unable to get system OS type.\n' + err)
        print RED + 'Unable to get system OS type; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)
    if 'SUSE' in out:
        if os.path.isfile('/etc/products.d/SUSE_SLES_SAP.prod'):
            productFile = '/etc/products.d/SUSE_SLES_SAP.prod'
        elif os.path.isfile('/etc/products.d/SLES_SAP.prod'):
            productFile = '/etc/products.d/SLES_SAP.prod'
        else:
            logger.error("Unable to determine the SLES OS type, since the SLES product file (SUSE_SLES_SAP.prod or SLES_SAP.prod) was missing from the '/etc/products.d' directory.")
            print RED + 'Unable to determine the SLES OS type; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)
        try:
            with open(productFile) as f:
                for line in f:
                    if 'SLES_SAP-release' in line:
                        version = re.match('^.*version="([0-9]{2}.[0-9]{1}).*', line).group(1)
                        if version in patchResourceDict:
                            osDistLevel = patchResourceDict[version].lstrip()
                        else:
                            logger.error('The SLES Service Pack level (' + version + ') installed is not supported.')
                            print RED + 'The SLES Service Pack level installed is not supported; check the log file for additional information; exiting program execution.' + RESETCOLORS
                            exit(1)
                        break

        except IOError as err:
            logger.error('Unable to determine the SLES OS type.\n' + str(err))
            print RED + 'Unable to determine the SLES OS type; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)

    elif 'Red Hat' in out:
        logger.error('The compute node is installed with Red Hat, which is not yet supported.')
        print RED + 'The compute node is installed with Red Hat, which is not yet supported; exiting program execution.' + RESETCOLORS
        exit(1)
    else:
        logger.error('The compute node is installed with an unsupported OS.')
        print RED + 'The compute node is installed with an unsupported OS; exiting program execution.' + RESETCOLORS
        exit(1)
    logger.info('Done checking and getting the OS distribution information.')
    logger.info('The OS distribution level was determined to be: ' + osDistLevel)
    return osDistLevel


def checkDiskSpace(loggerName):
    logger = logging.getLogger(loggerName)
    logger.info('Checking the available disk space of the root file system.')
    command = 'df /'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ") used to get the root file system's disk usage was: " + out.strip())
    if result.returncode != 0:
        logger.error('Unable to check the available disk space of the root file system.\n' + err)
        print RED + 'Unable to check the available disk space of the root file system; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)
    out = out.strip()
    tmpVar = re.match('(.*\\s+){3}([0-9]+)\\s+', out).group(2)
    availableDiskSpace = round(float(tmpVar) / float(1048576), 2)
    logger.info("The root file system's available disk space was determined to be: " + str(availableDiskSpace) + 'GB')
    if not availableDiskSpace >= 2:
        logger.error('There is not enough disk space (' + availableDiskSpace + 'GB) on the root file system. There needs to be at least 2GB of free space on the root file system.\n')
        print RED + 'There is not enough disk space on the root file system; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)
    logger.info('Done checking the available disk space of the root file system.')


def setPatchDirectories(patchResourceDict, loggerName):
    logger = logging.getLogger(loggerName)
    logger.info('Setting and getting the patch directories.')
    patchDirList = []
    options = patchResourceDict['options']
    if options.a or options.k:
        command = 'dmidecode -s system-product-name'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ") used to get the system's product type was: " + out.strip())
        if result.returncode != 0:
            logger.error('Unable to get the system product type.\n' + err)
            print RED + 'Unable to get the system product type; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)
        try:
            patchBaseDir = re.sub('\\s+', '', patchResourceDict['patchBaseDir']).rstrip('/')
            kernelDir = re.sub('\\s+', '', patchResourceDict['kernelSubDir'])
            osDistLevel = re.sub('\\s+', '', patchResourceDict['osDistLevel'])
            kernelDir = patchBaseDir + '/' + osDistLevel + '/' + kernelDir
        except KeyError as err:
            logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
            print RED + 'A resource key was not present in the resource file; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)

    if options.a or options.o:
        try:
            patchBaseDir = re.sub('\\s+', '', patchResourceDict['patchBaseDir']).rstrip('/')
            osDir = re.sub('\\s+', '', patchResourceDict['osSubDir'])
            additionalRPMSDir = re.sub('\\s+', '', patchResourceDict['additionalSubDir'])
            osDistLevel = re.sub('\\s+', '', patchResourceDict['osDistLevel'])
            osDir = patchBaseDir + '/' + osDistLevel + '/' + osDir
            additionalRPMSDir = patchBaseDir + '/' + additionalRPMSDir
        except KeyError as err:
            logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
            print RED + 'A resource key was not present in the resource file; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)

    if options.a:
        if os.path.exists(kernelDir):
            os.path.exists(osDir) and (os.path.exists(additionalRPMSDir) or logger.error('Option -a was selected, however, all of the RPM directories (' + kernelDir + ', ' + osDir + ', ' + additionalRPMSDir + ') are not present.'))
            print RED + 'Option -a was selected, however, all of the RPM directories are not present; check the log file for further information; exiting program execution.\n' + RESETCOLORS
            exit(1)
        else:
            patchDirList.append(kernelDir)
            patchDirList.append(osDir)
            patchDirList.append(additionalRPMSDir)
    elif options.k:
        if not os.path.exists(kernelDir):
            logger.error('Option -k was selected, however, the kernel RPM directory (' + kernelDir + ') is not present.')
            print RED + 'Option -k was selected, however, the kernel RPM directory is not present; check the log file for further information; exiting program execution.\n' + RESETCOLORS
            exit(1)
        else:
            patchDirList.append(kernelDir)
    elif os.path.exists(osDir):
        os.path.exists(additionalRPMSDir) or logger.error('Option -o was selected, however, both the OS and additional RPM directory (' + osDir + ', ' + additionalRPMSDir + ') are not present.')
        print RED + 'Option -o was selected, however, both the OS and additional RPM directory are not present; check the log file for further information; exiting program execution.\n' + RESETCOLORS
        exit(1)
    else:
        patchDirList.append(osDir)
        patchDirList.append(additionalRPMSDir)
    logger.info('Done setting and getting the patch directories.')
    logger.info('The patch directory list was determined to be: ' + str(patchDirList))
    return patchDirList


def checkSystemConfiguration(patchResourceDict, loggerName):
    logger = logging.getLogger(loggerName)
    logger.info("Checking the system's configuration.")
    postUpdateRequired = ''
    try:
        logBaseDir = re.sub('\\s+', '', patchResourceDict['logBaseDir']).rstrip('/')
        postUpdateResumeLog = re.sub('\\s+', '', patchResourceDict['postUpdateResumeLog'])
        postUpdateResumeLog = logBaseDir + '/' + postUpdateResumeLog
    except KeyError as err:
        logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
        print RED + 'The resource key for the post update resume log was not present in the resource file; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)

    command = 'rpm -q serviceguard'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to determine if Serviceguard was installed was: ' + out.strip())
    try:
        f = open(postUpdateResumeLog, 'a')
        if result.returncode == 0:
            f.write('isServiceguardSystem = yes\n')
            postUpdateRequired = 'yes'
        else:
            f.write('isServiceguardSystem = no\n')
        f.close()
    except IOError as err:
        logger.error('Unable to access the post update resume log.\n' + str(err))
        print RED + 'Unable to access the post update resume log; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)

    try:
        f = open(postUpdateResumeLog, 'a')
        fioStatus = '/usr/bin/fio-status'
        if os.path.exists(fioStatus):
            command = fioStatus + ' -c'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            logger.info('The output of the command (' + command + ') used to determine then number of FusionIO cards was: ' + out.strip())
            if result.returncode == 0:
                if out.strip() > 0:
                    f.write('isFusionIOSystem = yes\n')
                    postUpdateRequired = 'yes'
                    removeFusionIOPackages(patchResourceDict.copy(), loggerName)
                else:
                    logger.info('fio-status was present, but it appears the system does not have any FusionIO cards.\n')
            else:
                logger.error('Unable to determine the number of FusionIO cards installed.\n' + err)
                print RED + 'Unable to determine the number of FusionIO cards installed; check the log file for errors; exiting program execution.' + RESETCOLORS
                exit(1)
        else:
            f.write('isFusionIOSystem = no\n')
    except IOError as err:
        logger.error('Unable to access the post update resume log.\n' + str(err))
        print RED + 'Unable to access the post update resume log; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)

    f.close()
    logger.info("Done checking the system's configuration.")
    return postUpdateRequired


def updateBootloaderCFG(loggerName):
    logger = logging.getLogger(loggerName)
    logger.info("Updating the system's bootloader configuration file (/etc/sysconfig/bootloader).")
    dateTimestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    failsafeResources = 'ide=nodma apm=off noresume edd=off powersaved=off nohz=off highres=off processsor.max+cstate=1 nomodeset x11failsafe'
    bootloaderCfgBackup = '/etc/sysconfig/bootloader.' + dateTimestamp
    try:
        shutil.copy2('/etc/sysconfig/bootloader', bootloaderCfgBackup)
    except IOError as err:
        logger.error("Unable to backup the system's bootloader configuration file.\n" + str(err))
        print RED + "Unable to backup the system's bootloader configuration file; check the log file for errors; exiting program execution." + RESETCOLORS
        exit(1)

    command = 'cat /proc/cmdline'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to get the parameters passed to the kernel during startup was: ' + out.strip())
    if result.returncode != 0:
        logger.error('Unable to get the parameters passed to the kernel during startup.\n' + err)
        print RED + 'Unable to get the parameters passed to the kernel during startup; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)
    out = out.strip()
    out = re.sub('\\s+', ' ', out)
    if re.match('.*(root=.*)', out) == None:
        logger.error('Unable to find root in the kernel command line (/proc/cmdline); a reboot may fix this issue if ramdisk entries are found in the following output.\n' + out)
        print RED + 'Unable to get the parameters passed to the kernel during startup; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)
    defaultAppend = re.match('.*(root=.*)', out).group(1)
    failsafeAppend = re.sub('resume=(/[a-zA-Z0-9\\-_]*)+\\s+', failsafeResources + ' ', defaultAppend)
    bootloaderConfig = []
    try:
        f = open('/etc/sysconfig/bootloader', 'r')
        bootloaderConfData = f.readlines()
        f.close()
    except IOError as err:
        logger.error("Unable to read the system's bootloader configuration file.\n" + str(err))
        print RED + "Unable to read the system's bootloader configuration file; check the log file for errors; exiting program execution." + RESETCOLORS
        exit(1)

    for line in bootloaderConfData:
        line.strip()
        if 'DEFAULT_APPEND' in line:
            bootloaderConfig.append('DEFAULT_APPEND="' + defaultAppend + '"')
        elif 'FAILSAFE_APPEND' in line:
            bootloaderConfig.append('FAILSAFE_APPEND="' + failsafeAppend + '"')
        else:
            bootloaderConfig.append(line)

    try:
        f = open('/etc/sysconfig/bootloader', 'w')
        for line in bootloaderConfig:
            f.write(line + '\n')

        f.close()
    except IOError as err:
        logger.error("Unable to write the system's bootloader configuration file.\n" + str(err))
        print RED + "Unable to write the system's bootloader configuration file; check the log file for errors; exiting program execution." + RESETCOLORS
        exit(1)

    logger.info("Done updating the system's bootloader configuration file (/etc/sysconfig/bootloader).")
    return