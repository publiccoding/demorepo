# Embedded file name: ./createBootloaderConfigFile.py
from spUtils import RED, RESETCOLORS
import subprocess
import logging
import os
import shutil
import re
import datetime

def configureBootLoader(loggerName):
    logger = logging.getLogger(loggerName)
    logger.info("Configuring the system's bootloader.")
    command = 'rpm -qa kernel-bigsmp-base kernel-default-base kernel'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to get a list of installed kernels was: ' + out.strip())
    if result.returncode != 0:
        logger.error("Unable to get the system's installed kernel information.\n" + err)
        return 'Failure'
    out = out.strip()
    kernelList = out.split()
    logger.info('The installed kernel list was determined to be: ' + str(kernelList))
    try:
        with open('/etc/sysconfig/bootloader') as f:
            for line in f:
                if 'LOADER_TYPE' in line:
                    loader = re.match('^.*="\\s*([a-zA-Z]+)".*', line).group(1)
                    loader = loader.lower()
                    break

    except IOError as err:
        logger.error("Unable to determine the system's loader type.\n" + str(err))
        return 'Failure'

    logger.info('The bootloader type was determined to be: ' + loader)
    if loader == 'grub':
        if not configureGrubBootLoader(kernelList, loggerName):
            logger.error("Unable to configure the system's bootloader.")
            return 'Failure'
    elif not configureEliloBootLoader(kernelList, loggerName):
        logger.error("Unable to configure the system's bootloader.")
        return 'Failure'
    logger.info("Done configuring the system's bootloader.")
    return 'Success'


def configureGrubBootLoader(kernelList, loggerName):
    logger = logging.getLogger(loggerName)
    dateTimestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    try:
        shutil.copy2('/boot/grub/menu.lst', '/boot/grub/menu.lst.' + dateTimestamp)
    except IOError as err:
        logger.error("Unable to make a backup of the system's bootloader configuration file.\n" + str(err))
        return False

    command = 'uname -r'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to get the currently used kernel was: ' + out.strip())
    if result.returncode != 0:
        logger.error("Unable to get the system's current kernel version.\n" + err)
        return False
    currentKernel = out.strip()
    kernelVersionList = []
    for kernelPackage in kernelList:
        kernelVersionList.append(re.match('([a-z]+-){1,4}(.*)', kernelPackage).group(2))

    finalKernelList = kernelSort(kernelVersionList)
    logger.info('The final kernel list was determined to be: ' + str(finalKernelList))
    vmlinuzList = []
    initrdList = []
    for kernelVersion in finalKernelList:
        kernelVersion = kernelVersion[:-2]
        vmlinuzList.append('vmlinuz-' + kernelVersion + '-default')
        initrdList.append('initrd-' + kernelVersion + '-default')

    bootloaderConfig = ['default 0', 'timeout 15']
    gfxmenu = ''
    failsafeResources = 'ide=nodma apm=off noresume edd=off powersaved=off nohz=off highres=off processsor.max+cstate=1 nomodeset x11failsafe'
    try:
        with open('/boot/grub/menu.lst') as f:
            for line in f:
                line = line.strip()
                logger.info('The current line of menu.lst = ' + line)
                if 'gfxmenu' in line:
                    gfxmenu = line
                elif 'kernel' in line and 'resume' in line and currentKernel in line:
                    kernel = re.sub(' +', ' ', line)
                    failsafeKernel = re.sub('resume=(/[a-z0-9-_]*)+\\s+', failsafeResources + ' ', kernel)
                    failsafeKernelList = failsafeKernel.split()
                    tmpList = []
                    objects = set()
                    for object in failsafeKernelList:
                        if object not in objects:
                            tmpList.append(object)
                            objects.add(object)

                    failsafeKernel = ' '.join(tmpList)
                elif 'initrd' in line:
                    initrd = re.sub(' +', ' ', line)
                try:
                    if gfxmenu != '' and kernel and initrd:
                        break
                except NameError:
                    pass

    except IOError as err:
        logger.error("Unable to access the system's bootloader.\n" + str(err))
        return False

    if gfxmenu != '':
        bootloaderConfig.append(gfxmenu)
    for i in range(len(vmlinuzList)):
        bootloaderConfig.append('')
        bootloaderConfig.append('')
        bootloaderConfig.append('title SAP HANA kernel(' + vmlinuzList[i] + ')')
        bootloaderConfig.append('\t' + re.sub('vmlinuz.*-default', vmlinuzList[i], kernel))
        bootloaderConfig.append('\t' + re.sub('initrd-.*-default', initrdList[i], initrd))
        bootloaderConfig.append('')
        bootloaderConfig.append('title Failsafe SAP HANA kernel(' + vmlinuzList[i] + ')')
        bootloaderConfig.append('\t' + re.sub('vmlinuz.*-default', vmlinuzList[i], failsafeKernel))
        bootloaderConfig.append('\t' + re.sub('initrd-.*-default', initrdList[i], initrd))

    logger.info('The final grub bootloader configuration was determined to be: ' + str(bootloaderConfig))
    try:
        f = open('/boot/grub/menu.lst', 'w')
        for item in bootloaderConfig:
            f.write(item + '\n')

    except IOError as err:
        logger.error("Unable to write the system's bootloader configuration file.\n" + str(err))
        return False

    f.close()
    return True


def configureEliloBootLoader(kernelList, loggerName):
    logger = logging.getLogger(loggerName)
    dateTimestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    try:
        shutil.copy2('/etc/elilo.conf', '/etc/elilo.conf.' + dateTimestamp)
    except IOError as err:
        logger.error("Unable to make a backup of the system's bootloader configuration file.\n" + str(err))
        return False

    command = 'uname -r'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to get the currently used kernel was: ' + out.strip())
    if result.returncode != 0:
        logger.error("Unable to get the system's current kernel version.\n" + err)
        return False
    currentKernel = out.strip()
    currentKernel = 'vmlinuz-' + currentKernel
    kernelVersionList = []
    for kernelPackage in kernelList:
        kernelVersionList.append(re.match('([a-z]+-){1,4}(.*)', kernelPackage).group(2))

    finalKernelList = kernelSort(kernelVersionList)
    logger.info('The final kernel list was determined to be: ' + str(finalKernelList))
    vmlinuzList = []
    initrdList = []
    for kernelVersion in finalKernelList:
        kernelVersion = kernelVersion[:-2]
        vmlinuzList.append('vmlinuz-' + kernelVersion + '-default')
        initrdList.append('initrd-' + kernelVersion + '-default')

    logger.info('The kernel list was determined to be: ' + str(vmlinuzList))
    logger.info('The initrd list was determined to be: ' + str(initrdList))
    bootloaderConfig = ['timeout = 150', 'secure-boot = on', 'prompt']
    failsafeResources = 'ide=nodma apm=off noresume edd=off powersaved=off nohz=off highres=off processsor.max+cstate=1 nomodeset x11failsafe'
    try:
        f = open('/boot/efi/EFI/SuSE/elilo.conf', 'r')
        eliloConfData = f.readlines()
        f.close()
    except IOError as err:
        logger.error("Unable to access the system's bootloader.\n" + str(err))
        return False

    logger.info('The elilo.conf data was determined to be: ' + str(eliloConfData))
    kernelPresent = 'no'
    for line in eliloConfData:
        if 'image' in line and currentKernel in line:
            kernelPresent = 'yes'

    if kernelPresent == 'no':
        currentKernel = 'vmlinuz'
    logger.info('The current kernel reference in elilo.conf was determined to be: ' + currentKernel)
    currentKernelPattern = re.compile(currentKernel + '\\s*$')
    for line in eliloConfData:
        line = line.strip()
        if 'root' in line and 'append' not in line:
            root = re.sub(' +', ' ', line)
        elif 'append' in line and 'noresume' not in line:
            append = re.sub(' +', ' ', line)
            append = re.sub('" ', '"', append)
            append = re.sub(' "$', '"', append)
            failsafeAppend = re.sub('resume=(/[a-z0-9-_]*)+\\s+', failsafeResources + ' ', append)
            failsafeAppendList = failsafeAppend.split()
            tmpList = []
            objects = set()
            for object in failsafeAppendList:
                if object not in objects:
                    tmpList.append(object)
                    objects.add(object)

            failsafeAppend = ' '.join(tmpList)
        try:
            if root and append:
                break
        except NameError:
            pass

    logger.info('append has been determined to be: ' + append)
    logger.info('failsafeAppend has been determined to be: ' + failsafeAppend)
    for i in range(len(vmlinuzList)):
        bootloaderConfig.append('')
        bootloaderConfig.append('')
        bootloaderConfig.append('image = /boot/' + vmlinuzList[i])
        bootloaderConfig.append('\tlabel = Linux_' + str(i + 1))
        bootloaderConfig.append('\tdescription = "SAP HANA kernel(' + vmlinuzList[i] + ')"')
        bootloaderConfig.append('\t' + append)
        bootloaderConfig.append('\tinitrd = /boot/' + initrdList[i])
        bootloaderConfig.append('\t' + root)
        bootloaderConfig.append('')
        bootloaderConfig.append('image = /boot/' + vmlinuzList[i])
        bootloaderConfig.append('\tlabel = Linux_Failsafe_' + str(i + 1))
        bootloaderConfig.append('\tdescription = "Failsafe SAP HANA kernel(' + vmlinuzList[i] + ')"')
        bootloaderConfig.append('\t' + failsafeAppend)
        bootloaderConfig.append('\tinitrd = /boot/' + initrdList[i])
        bootloaderConfig.append('\t' + root)

    logger.info('The final elilo bootloader configuration was determined to be: ' + str(bootloaderConfig))
    try:
        f = open('/etc/elilo.conf', 'w')
        for item in bootloaderConfig:
            f.write(item + '\n')

    except IOError as err:
        logger.error("Unable to write the system's bootloader configuration file.\n" + str(err))
        return False

    f.close()
    command = '/sbin/elilo'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to install the new elilo bootloader was: ' + out.strip())
    if result.returncode != 0:
        logger.error("Unable to install/update the system's bootloader.\n" + err)
        return False
    return True


def kernelSort(verList):
    versionList = []
    revisionList = []
    finalVersionList = verList
    for ver in verList:
        version, revision = re.split('-', ver)
        versionList.append(re.sub('\\.', '', version))
        revisionList.append(re.sub('\\.', '', revision))

    versionList = map(int, versionList)
    revisionList = map(int, revisionList)
    for j in range(len(versionList)):
        for i in range(j + 1, len(versionList)):
            if versionList[i] > versionList[j] or versionList[i] == versionList[j] and revisionList[i] > revisionList[j]:
                versionList[i], versionList[j] = versionList[j], versionList[i]
                revisionList[i], revisionList[j] = revisionList[j], revisionList[i]
                finalVersionList[i], finalVersionList[j] = finalVersionList[j], finalVersionList[i]

    del finalVersionList[2:]
    return finalVersionList