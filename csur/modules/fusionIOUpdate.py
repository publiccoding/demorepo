# Embedded file name: ./fusionIOUpdate.py
import subprocess
import logging
import re
import os
from threading import Thread

class FusionIODriverUpdate:

    def __init__(self):
        self.pid = 0

    def buildInstallFusionIODriver(self, csurResourceDict, driverDir, computeNodeLogger):
        updateStatus = True
        self.pid = 0
        logger = logging.getLogger(computeNodeLogger)
        logger.info('Building and installing the FusionIO driver.')
        try:
            computeNodeDict = csurResourceDict['componentListDict']['computeNodeList'][0].getComputeNodeDict()
            fusionIODriverSrcRPM = csurResourceDict['fusionIODriverSrcRPM']
        except KeyError as err:
            logger.error('The resource key (' + str(err) + ') was not present in the csurResourceDict.')
            updateStatus = False

        if updateStatus:
            kernel = computeNodeDict['kernel']
            processorType = computeNodeDict['processorType']
            fusionIODriverSrcRPMPath = driverDir + 'src/' + fusionIODriverSrcRPM
            command = 'rpmbuild --rebuild ' + fusionIODriverSrcRPMPath
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
            self.pid = result.pid
            out, err = result.communicate()
            logger.info('The output of the command (' + command + ') used to build the FusionIO driver was: ' + out.strip())
            if result.returncode != 0:
                logger.error('Failed to build the FusionIO driver:\n' + err)
                updateStatus = False
        if updateStatus:
            out = out.strip()
            fusionIODriverRPM = fusionIODriverSrcRPM.replace('iomemory-vsl', '-vsl-' + kernel).replace('src', processorType)
            fusionIODriverPattern = re.compile('.*Wrote:\\s+((/[0-9,a-z,A-Z,_]+)+' + fusionIODriverRPM + ')', re.DOTALL)
            logger.info('The regex used to get the FusionIO driver RPM location was: ' + fusionIODriverPattern.pattern)
            driverRPM = re.match(fusionIODriverPattern, out).group(1)
            logger.info('The FuionIO driver was determined to be: ' + driverRPM)
            command = 'rpm -ivh ' + driverRPM + ' ' + driverDir + 'libvsl-*.rpm'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
            self.pid = result.pid
            out, err = result.communicate()
            logger.info('The output of the command (' + command + ') used to install the FusionIO driver was: ' + out.strip())
            if result.returncode != 0:
                logger.error('Failed to install the FusionIO driver:\n' + err)
                updateStatus = False
        logger.info('Done building and installing the FusionIO driver.')
        return updateStatus

    def getUpdatePID(self):
        return self.pid


class FusionIOFirmwareUpdate(Thread):

    def __init__(self, bus, firmwareImage, updateFailureList, computeNodeLogger):
        Thread.__init__(self)
        self.logger = logging.getLogger(computeNodeLogger)
        self.bus = bus
        self.firmwareImage = firmwareImage
        self.updateFailureList = updateFailureList
        self.pid = 0

    def run(self):
        self.logger.info('Updating the FusionIO firmware for IODIMM ' + self.bus + '.')
        command = 'fio-update-iodrive -y -f -s ' + self.bus + ' ' + self.firmwareImage
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
        self.pid = result.pid
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to update the FusionIO firmware for IODIMM ' + self.bus + ' was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Failed to upgrade the FusionIO firmware for IODIMM ' + self.bus + ':\n' + err)
            self.updateFailureList.append(self.bus)
        self.logger.info('Done updating the FusionIO firmware for IODIMM ' + self.bus + '.')

    def getUpdatePID(self):
        return self.pid