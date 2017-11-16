# Embedded file name: ./serviceguard.py
import subprocess
import logging
import re
import os
import shutil
import datetime
import distutils
from distutils.dir_util import copy_tree

class Serviceguard:

    def __init__(self, logger):
        self.logger = logger
        self.sgBinPath = ''
        self.hanfs = ''
        self.hanaNFSDir = ''

    def upgradeServiceguard(self, csurResourceDict):
        self.logger.info('Upgrading Serviceguard.')
        computeNodeDict = csurResourceDict['componentListDict']['computeNodeList'][0].getComputeNodeDict()
        componentUpdateDict = computeNodeDict['componentUpdateDict']
        sgSoftwareList = componentUpdateDict['sgSoftware']
        sgNFSSoftwareList = componentUpdateDict['sgNFSSoftware']
        osDistLevel = computeNodeDict['osDistLevel']
        csurBasePath = csurResourceDict['csurBasePath']
        if not self.__backupSGConfig(osDistLevel):
            return False
        if len(sgSoftwareList) != 0:
            if not self.__upgradeServiceguard(csurBasePath, sgSoftwareList):
                return False
        if len(sgNFSSoftwareList) != 0:
            if not self.__upgradeSGNFSToolKit(csurBasePath, sgNFSSoftwareList):
                return False
        if csurResourceDict['sgNode1']:
            if not self.__reconfigureNFSPackage():
                return False
        self.logger.info('Done upgrading Serviceguard.')
        return True

    def __backupSGConfig(self, osDistLevel):
        dateTimestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        self.logger.info('Making a backup of the Serviceguard configuration.')
        if 'SLES' in osDistLevel:
            self.sgBinPath = '/opt/cmcluster/bin'
            self.hanfs = '/opt/cmcluster/nfstoolkit/hanfs.sh'
            self.hanaNFSDir = '/opt/cmcluster/conf/hananfs'
            try:
                copy_tree(self.hanaNFSDir, self.hanaNFSDir + '_' + dateTimestamp)
            except distutils.errors.DistutilsFileError as err:
                self.logger.error('Failed to make a backup of the Serviceguard HANA NFS directory (' + self.hanaNFSDir + ').\n' + str(err))
                return False

            try:
                shutil.copy2(self.hanfs, self.hanfs + '_' + dateTimestamp)
            except IOError as err:
                self.logger.error('Failed to make a backup of the Serviceguard toolkit hanfs configuration file (' + self.hanfs + ').\n' + str(err))
                return False

        else:
            self.sgBinPath = '/usr/local/cmcluster/bin'
            self.hanfs = '/usr/local/cmcluster/nfstoolkit/hanfs.sh'
            self.hanaNFSDir = '/usr/local/cmcluster/conf/hananfs'
            try:
                copy_tree(self.hanaNFSDir, self.hanaNFSDir + '_' + dateTimestamp)
            except distutils.errors.DistutilsFileError as err:
                self.logger.error('Failed to make a backup of the Serviceguard HANA NFS directory (' + self.hanaNFSDir + ').\n' + str(err))
                return False

            try:
                shutil.copy2(self.hanfs, self.hanfs + '_' + dateTimestamp)
            except IOError as err:
                self.logger.error('Failed to make a backup of the Serviceguard toolkit hanfs configuration file (' + self.hanfs + ').\n' + str(err))
                return False

        self.logger.info('Done making a backup of the Serviceguard configuration.')
        return True

    def __upgradeServiceguard(self, csurBasePath, sgSoftwareList):
        sgSoftwareDir = csurBasePath + '/software/computeNode/serviceGuard/'
        self.logger.info('Upgrading the Serviceguard packages.')
        for rpm in sgSoftwareList:
            command = 'rpm -U --quiet --oldpackage --replacefiles --replacepkgs --nosignature ' + sgSoftwareDir + rpm
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
            out, err = result.communicate()
            self.logger.info('The output of the command (' + command + ') used to upgrade Serviceguard RPM ' + rpm + ' was: ' + out.strip())
            if result.returncode != 0:
                self.logger.error('Problems were encountered while upgrading Serviceguard.\n' + err)
                return False

        self.logger.info('Done upgrading the Serviceguard packages.')
        return True

    def __updateSGLicense(self, sgLicenseFile):
        self.logger.info('Updating the Serviceguard license.')
        command = self.sgBinPath + '/cmsetlicense -i ' + sgLicenseFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to update the Serviceguard license was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Problems were encountered while updating the Serviceguard license.\n' + err)
            return False
        self.logger.info('Done updating the Serviceguard license.')
        return True

    def __upgradeSGNFSToolKit(self, csurBasePath, sgNFSSoftwareList):
        sgSoftwareDir = csurBasePath + '/software/computeNode/serviceGuard/'
        self.logger.info('Upgrading the Serviceguard NFS Toolkit package(s).')
        for rpm in sgNFSSoftwareList:
            command = 'rpm -U --quiet --oldpackage --replacefiles --replacepkgs --nosignature ' + sgSoftwareDir + rpm
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
            out, err = result.communicate()
            self.logger.info('The output of the command (' + command + ') used to upgrade the Serviceguard NFS Toolkit RPM ' + rpm + ' was: ' + out.strip())
            if result.returncode != 0:
                self.logger.error('Problems were encountered while upgrading the Serviceguard NFS Toolkit.\n' + err)
                return False

        command = "sed -i '0,/^\\s*RPCNFSDCOUNT\\s*=\\s*[0-9]\\+$/s//RPCNFSDCOUNT=64/' " + self.hanfs
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to update the RPCNFSDCOUNT variable in ' + self.hanfs + ' was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Problems were encountered while updating the RPCNFSDCOUNT variable in ' + self.hanfs + '.\n' + err)
            return False
        self.logger.info('Done upgrading the Serviceguard NFS Toolkit package(s).')
        return True

    def __reconfigureNFSPackage(self):
        self.logger.info('Reconfiguring the NFS package.')
        command = self.sgBinPath + '/cmruncl'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to start the cluster was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Problems were encountered while starting the cluster.\n' + err)
            return False
        command = self.sgBinPath + '/cmviewcl -f line -l node'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to check that both nodes were running was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Problems were encountered while checking to see if both nodes were running.\n' + err)
            return False
        count = 0
        cmviewclList = out.split()
        for line in cmviewclList:
            if 'state=running' in line:
                count += 1
                if count == 2:
                    break

        if count != 2:
            self.logger.error('Problems were encountered while checking to see if both nodes were running; both nodes do not appear to be running.')
            return False
        command = self.sgBinPath + '/cmhaltpkg nfs'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to halt the nfs package was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Problems were encountered while halting the nfs package.\n' + err)
            return False
        command = self.sgBinPath + '/cmcheckconf -v -P ' + self.hanaNFSDir + '/nfs/nfs.conf'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to check the nfs package configuration was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Problems were encountered while checking the nfs package configuration.\n' + err)
            return False
        command = self.sgBinPath + '/cmapplyconf -v -f -P ' + self.hanaNFSDir + '/nfs/nfs.conf'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to verify and distribute the nfs package configuration was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Problems were encountered while verifying and distributing the nfs package configuration.\n' + err)
            return False
        command = self.sgBinPath + '/cmrunpkg nfs'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to run the nfs package was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Problems were encountered while starting the nfs package.\n' + err)
            return False
        command = self.sgBinPath + '/cmmodpkg -e nfs'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
        out, err = result.communicate()
        self.logger.info('The output of the command (' + command + ') used to enable AUTO_RUN of the nfs package was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Problems were encountered while enabling AUTO_RUN for the nfs package.\n' + err)
            return False
        self.logger.info('Done reconfiguring the NFS package.')
        return True