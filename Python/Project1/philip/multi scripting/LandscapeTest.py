
from hwval_client import AbstractCheck
VERBOSITY = 0
OMIT = None
DEBUG = False


class EvalOs(AbstractCheck):
    def configure(self, config={}):
        import os
        self.config = {}
        self.config.update(config)
        self.__info = {}
        self.hostname = ""
        self.mem = None
        self.net = None
        self.linux = None
        self.cpu= None
        self.system = None
        self.ARCHITECTURE = ""
        f = os.popen("uname -m")
        for line in f :
            if "ppc64" in line:
               self.ARCHITECTURE = "ppc64"
               break
            else :
               self.ARCHITECTURE = "x86"
               break
        f.close()

        # (name):{status:"SUCESS|FAILED|NOTAPPLICABLE", host:"hostname"})
        self.report = {}

        # (name):{type:"WARNING|HIGH|MEDIUM", reason:"hint_text"})
        self.exceptions = {}



    def setUpMaster(self):
        pass

    def setUp(self):

        import subprocess
        import sys, os, re
        from subprocess import Popen, PIPE, STDOUT
        try:
            f = subprocess.Popen(["hostname"],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            line = f.stdout.readline()

            while line:
                self.hostname=line.rstrip("\n")
                line = f.stdout.readline()
            return True
        except Exception,e:
            return False


    def runTest(self):
        self.gatherInfo()
        self.chainValidation()
        pass

    def chainValidation(self):
        self.validateDistribution()
        self.validateLinuxKernelVersion()
        self.validateRuntime()
        self.validateCPU()
        self.validateHypervisor()
        self.validateHTT()
        self.validateMemory()
        self.validateCoreMemoryRatio()
        self.validateMemoryDistribution()
        self.validateClocksource() 
        if self.ARCHITECTURE == "x86":
            self.validateApplianceSystemType()
            self.validateTHP()          # nothing to do for Power on SUSE 
            self.validateCPUgovernor()  # nothing to do on Power
        pass

    def validateDistribution(self):
        linuxInformationContainer = self.getLINUXInfo()
        tmp_exception = {}
        tmp_report = {}

        try:

            if "SUSE Linux Enterprise Server 11" in linuxInformationContainer["distribution_name"]:
                #ppc branch
                if self.ARCHITECTURE == "ppc64":
                   if linuxInformationContainer["distribution_patchlevel"] > "2":
                      tmp_report["status"] = "SUCESS"
                      tmp_report["host"] = self.hostname
                      self.report["validateDistribution"] = tmp_report
                      return ("CHECK_DISTRIBUTION",self.hostname,"distribution_patchlevel", linuxInformationContainer["distribution_patchlevel"],0,"" )
                   else:
                      tmp_exception["type"] = "HIGH"
                      tmp_exception["reason"] = "SUSE SLES11 SP %s is not sufficient to operate SAP HANA for production environments. Please see SAP Note 2055470 for more details." % linuxInformationContainer["distribution_patchlevel"]
                      self.exceptions["validateDistribution"] = tmp_exception
                      tmp_report["status"] = "FAILED"
                      tmp_report["host"] = self.hostname
                      self.report["validateDistribution"] = tmp_report
                      return ("CHECK_DISTRIBUTION",self.hostname,"distribution_patchlevel",linuxInformationContainer["distribution_patchlevel"],4,tmp_exception["reason"] )

                #intel branch 
                elif self.ARCHITECTURE == "x86":
                   if linuxInformationContainer["distribution_patchlevel"] in ["1","2","3"]:

                       tmp_report["status"] = "SUCESS"
                       tmp_report["host"] = self.hostname
                       self.report["validateDistribution"] = tmp_report

                       return ("CHECK_DISTRIBUTION",self.hostname,"distribution_patchlevel", linuxInformationContainer["distribution_patchlevel"],0,"" )
                   else:
                       tmp_exception["type"] = "HIGH"
                       tmp_exception["reason"] = "Distribution Servicepack %s is not supported." % linuxInformationContainer["distribution_patchlevel"]
                       self.exceptions["validateDistribution"] = tmp_exception

                       tmp_report["status"] = "FAILED"
                       tmp_report["host"] = self.hostname
                       self.report["validateDistribution"] = tmp_report
                       return ("CHECK_DISTRIBUTION",self.hostname,"distribution_patchlevel", linuxInformationContainer["distribution_patchlevel"],4,"OSDistribution Servicepack is not supported" )
                else: # ARCHITECTURE not set
                    print "Script Error in validateDistribution. Variable ARCHITECTURE not valid. Continue ..."
                    return ("CHECK_DISTRIBUTION",self.hostname,"ARCHITECTURE","",5,"Script Error in validateDistribution. Variable ARCHITECTURE not valid. Continue ...")

            elif linuxInformationContainer["distribution_name"] == "Red Hat Enterprise Linux Server release 6.5 (Santiago)":

                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateDistribution"] = tmp_report
                return ("CHECK_DISTRIBUTION",self.hostname,"distribution_name", linuxInformationContainer["distribution_name"],0,"" )
            elif linuxInformationContainer["distribution_name"] == "Red Hat Enterprise Linux Server release 6.6 (Santiago)":

                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateDistribution"] = tmp_report
                return ("CHECK_DISTRIBUTION",self.hostname,"distribution_name", linuxInformationContainer["distribution_name"],0,"" )
            elif linuxInformationContainer["distribution_name"] == "SUSE Linux Enterprise Server 12 (x86_64)":
                if linuxInformationContainer["distribution_patchlevel"] in ["0"]:
                    
                    tmp_report["status"] = "SUCESS"
                    tmp_report["host"] = self.hostname
                    self.report["validateDistribution"] = tmp_report
                    return ("CHECK_DISTRIBUTION",self.hostname,"distribution_name", linuxInformationContainer["distribution_name"],0,"" )
            else:

                tmp_exception["type"] = "HIGH"
                tmp_exception["reason"] = "Distribution %s is not supported." % linuxInformationContainer["distribution_name"]
                self.exceptions["validateDistribution"] = tmp_exception

                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateDistribution"] = tmp_report

                return ("CHECK_DISTRIBUTION",self.hostname,"distribution_name", linuxInformationContainer["distribution_name"],4,"OSDistribution Servicepack is not supported" )
        except Exception,e:
            tmp_exception["type"] = "HIGH"
            tmp_exception["reason"] = "Distribution is not supported."
            self.exceptions["validateDistribution"] = tmp_exception

            tmp_report["status"] = "FAILED"
            tmp_report["host"] = self.hostname
            self.report["validateDistribution"] = tmp_report

            return ("CHECK_DISTRIBUTION",self.hostname,"distribution_name", linuxInformationContainer["distribution_name"],5,tmp_exception["reason"] )
        pass

    def validateRuntime(self):
        import os
        linuxInformationContainer = self.getLINUXInfo()
        tmp_exception = {}
        tmp_report = {}
        libgcc_sles = ["libstdc++6-4.7.2_20130108","libgcc_s1-4.7.2_20130108"]
        libgcc_version = ["0.17.2","0.19.3"]
        libgcc_sles_ppc = ["libgcc_s1, 4.7.2, 0.17.2","libstdc++6, 4.7.2, 0.17.2","multipath-tools, 0, 0", "glibc, 2.11.3, 17.87.3","powerpc-utils, 0, 0"] #Format: Name, min. Version, min. Release
        libgcc_rhel = ["compat-sap-c++-4.7.2-10.el6_5.x86_64"]
#print linuxInformationContainer["rpm"]

        if self.report["validateDistribution"]["status"] == "SUCESS" and "SUSE Linux Enterprise Server 11" in linuxInformationContainer["distribution_name"]:
                #ppc branch
                if self.ARCHITECTURE == "ppc64":
                    missing_list = []
                    for item in libgcc_sles_ppc:
                        itemname, itemversion, itemrelease = map(str.strip, item.split(",",3))
                        exists = 0
                        for rpmitem in linuxInformationContainer["rpm-ppc"]:
                            rpmname, rpmversion, rpmrelease = map(str.strip, rpmitem.split(",",3))
                            if itemname == rpmname:
                                exists = 1
                                #remove PTF Number
                                itemversion = itemversion.split("_",1)[0]
                                itemrelease = itemrelease.split("_",1)[0]
                                rpmversion = rpmversion.split("_",1)[0]
                                rpmversion = rpmversion.split("+",1)[0]
                                rpmrelease = rpmrelease.split("_",1)[0]
                                #convert to integer
                                itemrelease = int(itemrelease.replace('.',''))
                                rpmrelease = int(rpmrelease.replace('.',''))
                                itemversion = int(itemversion.replace('.',''))
                                rpmversion = int(rpmversion.replace('.',''))
                                if (itemrelease > rpmrelease) or (itemversion > rpmversion):
                                    missing_list.append(' Update ')
                                    missing_list.append(rpmitem)
                                    missing_list.append(' to ')
                                    missing_list.append(item) 
                                break
                        if exists == 0:
                            missing_list.append(' Install ') 
                            missing_list.append(item)

                    #exit with a list of missing items
                    if (len(missing_list) > 0) :
                        return_string = ''.join(missing_list)
                        tmp_exception["type"] = "HIGH"
                        tmp_exception["reason"] = return_string
                        self.exceptions["validateRuntime"] = tmp_exception
                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateRuntime"] = tmp_report
                        return ("CHECK_RUNTIME",self.hostname,"Runtime","",4,tmp_exception["reason"])
                    #verify for SUSE Sles 11 SP3 on P8 ptf is installed
                    linuxInformationContainer = self.getLINUXInfo()
                    CPUInformationContainer = self.getCPUInfo()
                    if linuxInformationContainer["distribution_patchlevel"] == "3" and "SUSE Linux Enterprise Server 11 (ppc64)" == linuxInformationContainer["distribution_name"]  and (int(CPUInformationContainer["cpu_vers"]) == 8):
                        f = os.popen("uname -r")
                        for line in f :
                            if "3.0.101-63-default" not in line:
                                f.close()
                                tmp_exception["type"] = "HIGH"
                                tmp_exception["reason"] = "Runtime environment in this Distribution seems to be not ready for SAP HANA. This system requires a kernel ptf to run in P8 native mode. Please see SAP Note 2055470 for more details and newer options."
                                self.exceptions["validateRuntime"] = tmp_exception
                                tmp_report["status"] = "FAILED"
                                tmp_report["host"] = self.hostname
                                self.report["validateRuntime"] = tmp_report
                                return ("CHECK_RUNTIME",self.hostname,"Runtime", "",4,tmp_exception["reason"])
                            else:
                                f.close()
                    #return at the end in case all was fine.
                    tmp_report["status"] = "SUCESS"
                    tmp_report["host"] = self.hostname
                    self.report["validateRuntime"] = tmp_report
                    return ("CHECK_RUNTIME",self.hostname,"Runtime", "",0,"" )
                #intel branch
                elif self.ARCHITECTURE == "x86":
                    rpmFound = []
                    for item in libgcc_sles:
                        for rpmitem in linuxInformationContainer["rpm"]:
                            if item in rpmitem:
                                if not str(rpmitem.split("-",2)[2]) in libgcc_version:
                                    tmp_report["status"] = "FAILED"
                                    tmp_report["host"] = self.hostname
                                    self.report["validateRuntime"] = tmp_report
                                    return ("CHECK_RUNTIME",self.hostname,"runtime", "",4,"Please see SAP Note 2001528  for more details" )
                                else:
                                    rpmFound.append(item)
                    
                    if len(rpmFound) != len(libgcc_sles):
                        tmp_exception["type"] = "HIGH"
                        tmp_exception["reason"] = "Runtime environment in this Distribution is not ready for HANA DSPS07 Revisions and HANA SPS08. Please see SAP Note 2001528 for more details"
                        self.exceptions["validateRuntime"] = tmp_exception

                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateRuntime"] = tmp_report
                        return ("CHECK_RUNTIME",self.hostname,"runtime", "",4,"Please see SAP Note 2001528  for more details" ) 
                    tmp_report["status"] = "SUCESS"
                    tmp_report["host"] = self.hostname
                    self.report["validateRuntime"] = tmp_report

                    return ("CHECK_RUNTIME",self.hostname,"runtime", "",0,"" ) 
                else: # ARCHITECTURE not set
                    print "Script Error in validateRuntime. Variable ARCHITECTURE not valid. Continue ..."
                    return ("CHECK_RUNTIME",self.hostname,"ARCHITECTURE","",5,"Script Error in validateRuntime. Variable ARCHITECTURE not valid. Continue ...")

        elif self.report["validateDistribution"]["status"] == "SUCESS" and linuxInformationContainer["distribution_name"] == "Red Hat Enterprise Linux Server release 6.5 (Santiago)":

                for item in libgcc_rhel:
                    if item in linuxInformationContainer["rpm"]:
                        continue

                    else:
                        tmp_exception["type"] = "HIGH"
                        tmp_exception["reason"] = "Runtime environment in this Distribution is not ready for HANA SPS07 Revisions and HANA SPS08. Please see SAP Note 2001528 for more details."
                        self.exceptions["validateRuntime"] = tmp_exception

                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateRuntime"] = tmp_report
                        return ("CHECK_RUNTIME",self.hostname,"runtime", "",4,"Please see SAP Note 2001528  for more details" )


                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateRuntime"] = tmp_report

                return ("CHECK_RUNTIME",self.hostname,"runtime", "",0,"" )
        elif self.report["validateDistribution"]["status"] == "SUCESS" and linuxInformationContainer["distribution_name"] == "SUSE Linux Enterprise Server 12 (x86_64)":
                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateRuntime"] = tmp_report
                return ("CHECK_RUNTIME",self.hostname,"Runtime", "",0,"" )
        else:     
                tmp_exception["type"] = "HIGH"
                tmp_exception["reason"] = "Problem in identifying Runtime Environment in OS Distribution."
                self.exceptions["validateRuntime"] = tmp_exception

                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateRuntime"] = tmp_report

                return ("CHECK_RUNTIME",self.hostname,"runtime","",5,tmp_exception["reason"])
        pass

    def validateLinuxKernelVersion(self):
        linuxInformationContainer = self.getLINUXInfo()
        tmp_exception = {}
        tmp_report = {}
        try:
            if self.report["validateDistribution"]["status"] == "SUCESS" and "SUSE Linux Enterprise Server 11" in linuxInformationContainer["distribution_name"]:
                if linuxInformationContainer["distribution_patchlevel"] == "1":
                    value, _ = map(str.strip, linuxInformationContainer["kernelrelease"].split("-",1))
                    kernelversion, majorversion, minorrevison, patchlevel = map(str.strip, value.split(".",3))
                    if (int(kernelversion) >= 2) and (int(majorversion) >= 6) and (int(minorrevison) >= 32) and (int(patchlevel) >= 36):
                        #print patchlevel
                        tmp_report["status"] = "SUCESS"
                        tmp_report["host"] = self.hostname
                        self.report["validateLinuxKernelVersion"] = tmp_report
                        return ("CHECK_LINUXKERENEL",self.hostname,"linuxkernelversion", linuxInformationContainer["kernelrelease"],"",0,"" ) 
                    else:
                        tmp_exception["type"] = "MEDIUM"
                        tmp_exception["reason"] = "Kernelversion %s is too low and might have bugs related to XFS" %  value
                        self.exceptions["validateLinuxKernelVersion"] = tmp_exception
                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateLinuxKernelVersion"] = tmp_report
                        return ("CHECK_LINUXKERENEL",self.hostname,"linuxkernelversion", linuxInformationContainer["kernelrelease"],"",4,"Kernelversion is too low and might have bugs related to XFS" ) 
                elif linuxInformationContainer["distribution_patchlevel"] == "2":
                    value, _ = map(str.strip, linuxInformationContainer["kernelrelease"].split("-",1))
                    kernelversion, majorversion, minorrevison = map(str.strip, value.split(".",2))
                    if (int(kernelversion) >= 3) and (int(majorversion) >= 0) and (int(minorrevison) >= 101):
                        tmp_report["status"] = "SUCESS"
                        tmp_report["host"] = self.hostname
                        self.report["validateLinuxKernelVersion"] = tmp_report
                        return ("CHECK_LINUXKERENEL",self.hostname,"linuxkernelversion", linuxInformationContainer["kernelrelease"],"",0,"" )
                    else:
                        tmp_exception["type"] = "MEDIUM"
                        tmp_exception["reason"] = "Kernelversion %s is too low and has some bugs that might affect the installation. For More details: SAP Note 1824819" % value
                        self.exceptions["validateLinuxKernelVersion"] = tmp_exception
                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateLinuxKernelVersion"] = tmp_report
                        return ("CHECK_LINUXKERENEL",self.hostname,"linuxkernelversion", linuxInformationContainer["kernelrelease"],"",4,"Kernelversion is too low and might have bugs related to XFS For More details: SAP Note 1824819" )
                elif linuxInformationContainer["distribution_patchlevel"] == "3":
                    value, _ = map(str.strip, linuxInformationContainer["kernelrelease"].split("-",1))
                    kernelversion, majorversion, minorrevison = map(str.strip, value.split(".",2))
                    # expect to have a minor of 101 to fix xfs bug also in SP03.
                    if (int(kernelversion) >= 3) and (int(majorversion) >= 0) and (int(minorrevison) >= 101):
                        tmp_report["status"] = "SUCESS"
                        tmp_report["host"] = self.hostname
                        self.report["validateLinuxKernelVersion"] = tmp_report
                        return ("CHECK_LINUXKERENEL",self.hostname,"linuxkernelversion", linuxInformationContainer["kernelrelease"],"",0,"" ) 
                    else:
                        tmp_exception["type"] = "MEDIUM"
                        tmp_exception["reason"] = "\nKernelversion %s is too low and has some bugs that might affect the \ninstallation. For More details: SAP Note 1954788. \nFor Power also review SAP Note 2055470 in addition."  % value
                        self.exceptions["validateLinuxKernelVersion"] = tmp_exception
                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateLinuxKernelVersion"] = tmp_report
                        return ("CHECK_LINUXKERENEL",self.hostname,"linuxkernelversion", linuxInformationContainer["kernelrelease"],"",4,tmp_exception["reason"])
            elif self.report["validateDistribution"]["status"] == "SUCESS" and "SUSE Linux Enterprise Server 12" in linuxInformationContainer["distribution_name"]:
                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateLinuxKernelVersion"] = tmp_report
            else:
                tmp_report["status"] = "NOTAPPLICABLE"
                tmp_report["host"] = self.hostname
                self.report["validateLinuxKernelVersion"] = tmp_report
                return ("CHECK_LINUXKERENEL",self.hostname,"linuxkernelversion", linuxInformationContainer["kernelrelease"],"",1,"SUSE SLES 11 kernel not in validation list. Verify minimum kernel requirements manually." )
        except Exception,e:
                tmp_exception["type"] = "HIGH"
                tmp_exception["reason"] = "Problem in identifying Distribution and Linuxkernel relations"
                self.exceptions["validateLinuxKernelVersion"] = tmp_exception
                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateLinuxKernelVersion"] = tmp_report
                return ("CHECK_LINUXKERENEL",self.hostname,"linuxkernelversion","",5,tmp_exception["reason"] )
        pass
    def validateCPU(self):
        CPUInformationContainer = self.getCPUInfo()
        tmp_exception = {}
        tmp_report = {} 
        if self.ARCHITECTURE == "x86":
            cpu_name, _ = map(str.strip, CPUInformationContainer["cpu_name"].split("@", 2))
            if cpu_name in ["Intel(R) Xeon(R) CPU E7- 8870","Intel(R) Xeon(R) CPU E7- 4870","Intel(R) Xeon(R) CPU E7- 2870",
                             "Intel(R) Xeon(R) CPU E7-8880 v2","Intel(R) Xeon(R) CPU E7-4880 v2","Intel(R) Xeon(R) CPU E7-2880 v2",
                             "Intel(R) Xeon(R) CPU E7-8890 v2","Intel(R) Xeon(R) CPU E7-4890 v2","Intel(R) Xeon(R) CPU E7-2890 v2",
                             "Intel(R) Xeon(R) CPU E7-8890 v3","Intel(R) Xeon(R) CPU E7-8880 v3","Intel(R) Xeon(R) CPU E7-4890 v3",
                             "Intel(R) Xeon(R) CPU E7-2890 v3","Intel(R) Xeon(R) CPU E7-4880 v3","Intel(R) Xeon(R) CPU E7-2880 v3",
                             "Intel(R) Xeon(R) CPU E5-2670 v3","Intel(R) Xeon(R) CPU E5-2680 v3","Intel(R) Xeon(R) CPU E5-2687 v3",
                             "Intel(R) Xeon(R) CPU E5-2690 v3","Intel(R) Xeon(R) CPU E5-2670 v2","Intel(R) Xeon(R) CPU E5-2680 v2",
                             "Intel(R) Xeon(R) CPU E5-2687 v2","Intel(R) Xeon(R) CPU E5-2690 v2"]:
                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateCPU"] = tmp_report

                return ("CHECK_CPU",self.hostname,"cpu_name",CPUInformationContainer["cpu_name"],0,"" )
            else:
                tmp_exception["type"] = "HIGH"
                tmp_exception["reason"] = "CPU Model %s is not supported for productive usage" % (CPUInformationContainer["cpu_name"])
                self.exceptions["validateCPU"] = tmp_exception
                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateCPU"] = tmp_report
                return ("CHECK_CPU",self.hostname,"cpu_name",CPUInformationContainer["cpu_name"],4,tmp_exception["reason"])
                
        elif self.ARCHITECTURE == "ppc64": 
            #import pdb; pdb.set_trace()
            CPU = 0
            nbr, _ = map(str.strip, CPUInformationContainer["cpus"].split(".", 2))
            CPU += int(nbr)

            if "power7+" in CPUInformationContainer["cpu_name"]:
                if (CPU < 2):
                    tmp_exception["type"] = "WARNING"
                    tmp_exception["reason"] = "Not enough cores (SAP Note 2133369)."
                    self.exceptions["validateCPU"] = tmp_exception
                    tmp_report["status"] = "FAILED"
                    tmp_report["host"] = self.hostname
                    self.report["validateCPU"] = tmp_report
                    return ("CHECK_CPU",self.hostname,"cpucount",str(CPU),4,tmp_exception["reason"])
                else: 
                    tmp_exception["type"] = "WARNING"
                    tmp_exception["reason"] = "\nPOWER 7+ processor architecture systems can only be used \nfor none-production systems."
                    self.exceptions["validateCPU"] = tmp_exception
                    tmp_report["status"] = "FAILED"
                    tmp_report["host"] = self.hostname
                    self.report["validateCPU"] = tmp_report
                    return ("CHECK_CPU",self.hostname,"processor","POWER 7+",1,tmp_exception["reason"])

            elif (int(CPUInformationContainer["cpu_vers"]) > 7):
                # verify ceiling and floog CPU configuration
                if (CPU < 4) and (CPU > 1):
                    tmp_exception["type"] = "WARNING"
                    tmp_exception["reason"] = "\nLess than 4 cores are configured to this HANA machine.\nFour cores is the entry sizing for production systems.\nFor none-production the CPU allocation might be sufficient."
                    self.exceptions["validateCPU"] = tmp_exception
                    tmp_report["status"] = "FAILED"
                    tmp_report["host"] = self.hostname
                    self.report["validateCPU"] = tmp_report
                    return ("CHECK_CPU",self.hostname,"cpucount",str(CPU),2,tmp_exception["reason"])
                if (CPU > 96):
                    tmp_exception["type"] = "WARNING"
                    tmp_exception["reason"] = "\nMore than 96 cores are configured to this HANA machine.\nIn order to run above please apply SAP Note 1903576.\nAlso verify SAP Note 2133369 if the default ceiling configuration has changed."
                    self.exceptions["validateCPU"] = tmp_exception
                    tmp_report["status"] = "FAILED"
                    tmp_report["host"] = self.hostname
                    self.report["validateCPU"] = tmp_report
                    return ("CHECK_CPU",self.hostname,"cpucount",str(CPU),2,tmp_exception["reason"]) 
                if (int(CPUInformationContainer["cpu_vers"]) > int(CPUInformationContainer["cpu_mode_no"])):
                    tmp_exception["type"] = "WARNING"
                    tmp_exception["reason"] = "This systems operates in %s mode, but is capable to operate in a higher mode with better performance characteristics. Please verify if the mode can be adjusted to the processor's capabilities. This conifguration has to automated core to memeory verification. Skip \"validateCoreMemoryRatio\"." % CPUInformationContainer["cpu_mode"]
                    self.exceptions["validateCPU"] = tmp_exception
                    tmp_report["status"] = "FAILED"
                    tmp_report["host"] = self.hostname
                    self.report["validateCPU"] = tmp_report
                    return ("CHECK_CPU",self.hostname,"cpucount",str(CPU),3,tmp_exception["reason"])
                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateCPU"] = tmp_report
                return ("CHECK_CPU",self.hostname,"cpu_name",CPUInformationContainer["cpu_name"],0,"" )          
            else:
                tmp_exception["type"] = "HIGH"
                tmp_exception["reason"] = "CPU Model %s is not Supported" % (CPUInformationContainer["cpu_name"])
                self.exceptions["validateCPU"] = tmp_exception
                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateCPU"] = tmp_report
                return ("CHECK_CPU",self.hostname,"cpu_name",CPUInformationContainer["cpu_name"],4,tmp_exception["reason"]) 
        else:
            print "Script Error in validateRuntime. Variable ARCHITECTURE not valid. Continue ..."
            return ("CHECK_RUNTIME",self.hostname,"ARCHITECTURE","",5,"Script Error in validateRuntime. Variable ARCHITECTURE not valid. Continue ...")
        pass

    def validateHTT(self):
        CPUInformationContainer = self.getCPUInfo()
        MEMInformationContainer = self.getMEMInfo()
        tmp_exception = {}
        tmp_report = {}
        if self.ARCHITECTURE == "x86":
            if self.report["validateHypervisor"]["status"] == "SUCESS":
                tmp_report["status"] = "NOTAPPLICABLE"
                tmp_report["host"] = self.hostname
                self.report["validateHTT"] = tmp_report
                return ("CHECK_HTT",self.hostname,"Hyperthreading","",1,"" ) 
                
            if  CPUInformationContainer["logical"] == 2*CPUInformationContainer["physical"] and " ht " in CPUInformationContainer["flags"]:
                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateHTT"] = tmp_report
                return ("CHECK_HTT",self.hostname,"Hyperthreading","",0,"" ) 
            else:
                tmp_exception["type"] = "HIGH"
                tmp_exception["reason"] = "Hyperthreading is not enabled"
                self.exceptions["validateHTT"] = tmp_exception
                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateHTT"] = tmp_report
                return ("CHECK_HTT",self.hostname,"Hyperthreading","",4,"" )
        elif self.ARCHITECTURE == "ppc64": #ppc
            warning_txt = []
            if  "Dedicated" not in CPUInformationContainer["lpar_type"]:
               warning_txt.append('\nFor production systmes only dedicated or dedicated donating \npartitions are supported.')
            if  ( CPUInformationContainer["smt"] < 8 ) :
               warning_txt.append('\nThis LPAR runs on less than eight SMTs. Use lscpu to verify \nCPU settings and decide for the preferred value. \nThe command ppc64_cpu --smt=x can be used to dynamically \nincrease SMT settings.')
            if CPUInformationContainer["power_mode"] != "off" :
                 warning_txt.append('\nThis partition is using AEM (IBM Active Energy Manager). \nThis can decrease or increase performance \ncharacteristics of this partition dynamically during operations.')
            if MEMInformationContainer["ams"] != "disabled" :
                 warning_txt.append('\nMemory sharing is not supported for SAP HANA production \nsystems due to performance degregation.')
            if MEMInformationContainer["ame"] != "disabled" :
                 warning_txt.append('\nMemory compresion is not supported for SAP HANA production \nsystems due to performance degregation.')
            if (CPUInformationContainer["cpu_dscr"] > 0 ) :
                 warning_txt.append('\nThe recommended DSCR CPU setting is 0. \nYou can change this using ppc64_cpu --dscr=0.\n Risk: Performance degregation if > 0.')
            if (len(warning_txt) == 0) :
               tmp_report["status"] = "SUCESS"
               tmp_report["host"] = self.hostname
               self.report["validateHTT"] = tmp_report
               return ("CHECK_HTT",self.hostname,"Hyperthreading","",0,"" )
            else:
               return_string = ''.join(warning_txt)
               tmp_exception["type"] = "WARNING"
               tmp_exception["reason"] = return_string
               self.exceptions["validateHTT"] = tmp_exception
               tmp_report["status"] = "FAILED"
               tmp_report["host"] = self.hostname
               self.report["validateHTT"] = tmp_report
               return ("CHECK_HTT",self.hostname,"Hyperthreading","",4,tmp_exception["reason"])
        else: # ARCHITECTURE not set
            print "Script Error in validateHTT. Variable ARCHITECTURE not valid. Continue ..."
            return ("CHECK_HTT",self.hostname,"ARCHITECTURE","",5,"Script Error in validateHTT. Variable ARCHITECTURE not valid. Continue ...")
        pass


    def validateMemory(self):
        try:
            import re, os
            MEMInformationContainer = self.getMEMInfo()
            tmp_exception = {}
            tmp_report = {}
            AllowedMemoryConfiguration = [24576,49152,65536,131072,196608,262144,327680,393216,524288,1048576,1572864,2097152,3145728,4194304,6291456,9437184,12582912]
            TotalMemory = 0
            if self.ARCHITECTURE == "x86":
                r =self.validateHypervisor()
                if r[4] == 1:
                    tmp_report["status"] = "NOTAPPLICABLE"
                    tmp_report["host"] = self.hostname
                    self.report["validateMemory"] = tmp_report
                    return ("CHECK_MEMORY",self.hostname,"hypervisormemory","",3,"Memory rules for hypervisor configurations have to follow hypervisor specific guidelines. Please look into the SAP note for your hypervisor" ) 
                for i in MEMInformationContainer["dimmSize"]:
                   TotalMemory += int(i)
                if len(list(set(MEMInformationContainer["dimmSize"]))) == 1:
                   tmp_report["status"] = "SUCESS"
                   tmp_report["host"] = self.hostname
                else:
                   tmp_exception["type"] = "HIGH"
                   tmp_exception["reason"] = "Different Memory Modules are used! This will have impact on Memory performance"
                   self.exceptions["validateMemory"] = tmp_exception
                   tmp_report["status"] = "FAILED"
                   tmp_report["host"] = self.hostname
                   self.report["validateMemory"] = tmp_report
                   return ("CHECK_MEMORY",self.hostname,"modulesizes",MEMInformationContainer["dimmSize"],4,"Different Memory Modules are used! This will have impact on Memory performance" ) 
                if MEMInformationContainer["dimmSpeedPysical"] >= 1066:
                   tmp_report["status"] = "SUCESS"
                   tmp_report["host"] = self.hostname
                else:
                   tmp_exception["type"] = "HIGH"
                   tmp_exception["reason"] = "DIMM Speed to slow! This will have impact on Memory performance"
                   self.exceptions["validateMemory"] = tmp_exception
                   tmp_report["status"] = "FAILED"
                   tmp_report["host"] = self.hostname
                   self.report["validateMemory"] = tmp_report
                   return ("CHECK_MEMORY",self.hostname,"modulespeed",MEMInformationContainer["dimmSpeedPysical"],4,"DIMM Speed to slow! This will have impact on Memory performance" )
                if TotalMemory in AllowedMemoryConfiguration:
                   tmp_report["status"] = "SUCESS"
                   tmp_report["host"] = self.hostname
                   self.report["validateMemory"] = tmp_report
                   return ("CHECK_MEMORY",self.hostname,"memorycheck","",0,"" )
                else:
                   tmp_exception["type"] = "HIGH"
                   tmp_exception["reason"] = "TotalMemory Size is not an allowed memory configuration"
                   self.exceptions["validateMemory"] = tmp_exception
                   tmp_report["status"] = "FAILED"
                   tmp_report["host"] = self.hostname
                   self.report["validateMemory"] = tmp_report
                   return ("CHECK_MEMORY",self.hostname,"totalmemory",str(TotalMemory),4,"TotalMemory Size is not an allowed memory configuration" )
 

            elif self.ARCHITECTURE == "ppc64":
               TotalMemory =  re.sub("[^0-9]", "",MEMInformationContainer["MemTotal"])
               # validate floor configuration
               if (int(TotalMemory) < 134217728) :     #value is in kb for production 128GB * 1024
                   if (int(TotalMemory) >= 64000000) :    # value is for in kb for none-production 64GB *1000
                       tmp_exception["type"] = "WARNING"
                       tmp_exception["reason"] = "\nLess than 128 GB memory are configured to this HANA machine.\n128 GB is the entry sizing for production systems.\nFor none-production the memory allocation might be sufficient."
                       self.exceptions["validateMemory"] = tmp_exception
                       tmp_report["status"] = "FAILED"
                       tmp_report["host"] = self.hostname
                       self.report["validateMemory"] = tmp_report
                       return ("CHECK_MEMORY",self.hostname,"memorysize",str(TotalMemory),2,tmp_exception["reason"]) 
                   else:
                       tmp_exception["type"] = "HIGH"
                       tmp_exception["reason"] = "\nTotalMemory Size (%s kb) is not an allowed memory \nconfiguration (SAP Note 2133369)." % (TotalMemory)
                       self.exceptions["validateMemory"] = tmp_exception
                       tmp_report["status"] = "FAILED"
                       tmp_report["host"] = self.hostname
                       self.report["validateMemory"] = tmp_report
                       return ("CHECK_MEMORY",self.hostname,"totalmemory",str(TotalMemory),4,tmp_exception["reason"]) 
               #validate ceiling configuration
               elif (int(TotalMemory) > 3221225472) : #value is in kb *1024
                   tmp_exception["type"] = "WARNING"
                   tmp_exception["reason"] = "\nTotalMemory Size is (%s kb). This is above the ceiling memory \nconfiguration (SAP Note 2133369). Ensure to have SAP Note 1903576 applied to run on a supported configuration." % (TotalMemory)
                   self.exceptions["validateMemory"] = tmp_exception
                   tmp_report["status"] = "FAILED"
                   tmp_report["host"] = self.hostname
                   self.report["validateMemory"] = tmp_report
                   return ("CHECK_MEMORY",self.hostname,"totalmemory",str(TotalMemory),1,tmp_exception["reason"])
               else:
                   tmp_report["status"] = "SUCESS"
                   tmp_report["host"] = self.hostname
                   self.report["validateMemory"] = tmp_report
                   return ("CHECK_MEMORY",self.hostname,"memorysize",TotalMemory,0,"" )
            else:
                print "Script Error in validateMemory. Variable ARCHITECTURE not valid. Continue ..."
                return ("CHECK_MEMORY",self.hostname,"ARCHITECTURE","",5,"Script Error in validateMemory. Variable ARCHITECTURE not valid. Continue ...")
        except Exception,e:
            return ("CHECK_MEMORY",self.hostname,"","",5,"" )
        pass




    def validateMemoryDistribution(self):
        MEMInformationContainer = self.getMEMInfo()
        tmp_exception = {}
        tmp_report = {}
        TotalMemory = 0
        import os
        if self.ARCHITECTURE == "x86": 
            AllowedMemoryConfiguration = [24576,49152,65536,131072,196608,262144,327680,393216,524288,1048576,1572864,2097152,3145728,4194304,6291456,9437184,12582912]
            for i in MEMInformationContainer["dimmSize"]:
                TotalMemory += int(i)

            if self.report["validateMemory"]["status"] == "SUCESS":

                if len(list(set(MEMInformationContainer["nodeSize"]))) == 1:

                    tmp_report["status"] = "SUCESS"
                    tmp_report["host"] = self.hostname
                    self.report["validateMemoryDistribution"] = tmp_report
                    return ("CHECK_MEMORYDISTRIBUTION",self.hostname,"memorysize","",0,"" )
                elif len(list(set(MEMInformationContainer["nodeSize"]))) == 2:
                    if int(MEMInformationContainer["nodeSize"][0]) < int(MEMInformationContainer["nodeSize"][1]) and int(MEMInformationContainer["nodeSize"][0]) > int(MEMInformationContainer["nodeSize"][1]) - int(MEMInformationContainer["dimmSize"][0]):
                        tmp_report["status"] = "SUCESS"
                        tmp_report["host"] = self.hostname
                        self.report["validateMemoryDistribution"] = tmp_report
                        return ("CHECK_MEMORYDISTRIBUTION",self.hostname,"memorydistribution","",0,"" )
                    else:

                        tmp_exception["type"] = "MEDIUM"
                        tmp_exception["reason"] = "Memory distribution is not fully balanced. This may impact memory performance"
                        self.exceptions["validateMemoryDistribution"] = tmp_exception
                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateMemoryDistribution"] = tmp_report
                        return ("CHECK_MEMORYDISTRIBUTION",self.hostname,"memorydistribution","",1,"Memory distribution is not fully balanced. This may impact memory performance")

                else:
                    tmp_exception["type"] = "MEDIUM"
                    tmp_exception["reason"] = "Memory distribution is not fully balanced. This may impact memory performance"
                    self.exceptions["validateMemoryDistribution"] = tmp_exception
                    tmp_report["status"] = "FAILED"
                    tmp_report["host"] = self.hostname
                    self.report["validateMemoryDistribution"] = tmp_report

                    return ("CHECK_MEMORYDISTRIBUTION",self.hostname,"memorydistribution","",1,"Memory distribution is not fully balanced. This may impact memory performance")

 
                if MEMInformationContainer["dimmSpeedPysical"] >= 1066:
                    tmp_report["status"] = "SUCESS"
                    tmp_report["host"] = self.hostname

                else:
                    tmp_exception["type"] = "HIGH"
                    tmp_exception["reason"] = "DIMM Speed to slow! This will have impact on Memory performance"
                    self.exceptions["validateMemoryDistribution"] = tmp_exception
                    tmp_report["status"] = "FAILED"
                    tmp_report["host"] = self.hostname
                    self.report["validateMemoryDistribution"] = tmp_report
                    return ("CHECK_MEMORYDISTRIBUTION",self.hostname,"memoryspeed","",4,"DIMM Speed to slow! This will have impact on Memory performance" )


                if TotalMemory in AllowedMemoryConfiguration:
                    tmp_report["status"] = "SUCESS"
                    tmp_report["host"] = self.hostname
                    self.report["validateMemoryDistribution"] = tmp_report
                    return ("CHECK_MEMORYDISTRIBUTION",self.hostname,"memorysize","",0,"" )
                else:
                    tmp_exception["type"] = "HIGH"
                    tmp_exception["reason"] = "TotalMemory Size is not an allowed memory configuration"
                    self.exceptions["validateMemoryDistribution"] = tmp_exception
                    tmp_report["status"] = "FAILED"
                    tmp_report["host"] = self.hostname
                    self.report["validateMemoryDistribution"] = tmp_report
                    return ("CHECK_MEMORYDISTRIBUTION",self.hostname,"memorysize","",4,"TotalMemory Size is not an allowed memory configuration" )
 

            else:
                tmp_report["status"] = "NOTAPPLICABLE"
                tmp_report["host"] = self.hostname
                self.report["validateMemoryDistribution"] = tmp_report
                return ("CHECK_MEMORYDISTRIBUTION",self.hostname,"","",5,"" ) 

        elif self.ARCHITECTURE == "ppc64":
            #Verify if there are numa Nodes without memory
            f = os.popen("numactl --hardware | grep \"size: 0\"")
            for line in f.readlines():
                tmp_exception["type"] = "HIGH"
                tmp_exception["reason"] = "Numa node without memory detected. \nVerify using numactl --hardware. Use DPO to rearrange topology. "
                self.exceptions["validateMemoryDistribution"] = tmp_exception
                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateMemoryDistribution"] = tmp_report
                f.close()
                return ("CHECK_MEMORYDISTRIBUTION",self.hostname,"numanode","",4,tmp_exception["reason"] )
            f.close()
            tmp_report["status"] = "SUCESS"
            tmp_report["host"] = self.hostname
            self.report["validateMemoryDistribution"] = tmp_report
            return ("CHECK_MEMORYDISTRIBUTION",self.hostname,"memorysize","",0,"" )
        else: # ARCHITECTURE not set
            print "Script Error in validateMemoryDistribution. Variable ARCHITECTURE not valid. Continue ..."
            return ("CHECK_MEMORYDISTRIBUTION",self.hostname,"ARCHITECTURE","",5,"Script Error in validateMemoryDistribution. Variable ARCHITECTURE not valid. Continue ...")

    pass

    def validateHypervisor(self):
        import subprocess
        import sys, os
        from subprocess import Popen, PIPE, STDOUT
        CPUInformationContainer = self.getCPUInfo()
        tmp_exception = {}
        tmp_report = {}
        vendorid = None
        hypervisor = None
        if self.ARCHITECTURE == "x86":

            f = subprocess.Popen(["{cwd}scanhypervisor".format(cwd=self.config["remote_base_dir"])],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            line = f.stdout.readline()
            while line:
                if "Vendor ID" in line:
                    _, vendorid = map(str.strip, line.split(":", 1))

                if "Hypervisor" in line:
                    _, hypervisor = map(str.strip, line.split(":", 1))


                line = f.stdout.readline()

            try:
                if "hypervisor" in CPUInformationContainer["flags"] or hypervisor is not None:
                    if vendorid is not None and vendorid in ["XEN","VMwareVMware","VmwareVmware"]:
                        tmp_report["status"] = "SUCESS"
                        tmp_report["host"] = self.hostname
                        self.report["validateHypervisor"] = tmp_report
                        return ("CHECK_HYPERVISOR",self.hostname,"hypervisor",vendorid,1,"" )
                    else:
                        tmp_exception["type"] = "HIGH"
                        tmp_exception["reason"] = "Hypervisor '%s' is not supported" % (vendorid)
                        self.exceptions["validateHypervisor"] = tmp_exception
                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateHypervisor"] = tmp_report
                        return ("CHECK_HYPERVISOR",self.hostname,"hypervisor",vendorid,4,"Hypervisor not supported" )
                else:
                    tmp_report["status"] = "NOTAPPLICABLE"
                    tmp_report["host"] = self.hostname
                    self.report["validateHypervisor"] = tmp_report
                    return ("CHECK_HYPERVISOR",self.hostname,"hypervisor","",0,"" ) 
            except Exception,e:
                print e
        elif self.ARCHITECTURE == "ppc64": #ppc branch
            f = os.popen("lscpu")
            for line in f.readlines():
                if "pHyp" in line:
                    tmp_report["status"] = "SUCESS"
                    tmp_report["host"] = self.hostname
                    self.report["validateHypervisor"] = tmp_report
                    return ("CHECK_HYPERVISOR",self.hostname,"hypervisor",line,0,"" )
            f.close()
            tmp_exception["type"] = "HIGH"
            tmp_exception["reason"] = "Could not detect PowerVM Hypervisor. Verify to have valid Hypervisor in place."
            self.exceptions["validateHypervisor"] = tmp_exception
            tmp_report["status"] = "FAILED"
            tmp_report["host"] = self.hostname
            self.report["validateHypervisor"] = tmp_report
            return ("CHECK_HYPERVISOR",self.hostname,"hypervisor","",4,tmp_exception["reason"])
        else: # ARCHITECTURE not set
            print "Script Error in validateHypervisor. Variable ARCHITECTURE not valid. Continue ..."
            return ("CHECK_HYPERVISOR",self.hostname,"ARCHITECTURE","",5,"Script Error in validateHypervisor. Variable ARCHITECTURE not valid. Continue ...")

        pass


    def validateCoreMemoryRatio(self): 
        import decimal
        import math
        MEMInformationContainer = self.getMEMInfo()
        CPUInformationContainer = self.getCPUInfo()
        tmp_exception = {}
        tmp_report = {}
        TotalMemory = 0
        CPU = 0
        try:
            if self.ARCHITECTURE == "x86":
                r =self.validateHypervisor()
                if r[4] == 1:
                    tmp_report["status"] = "NOTAPPLICABLE"
                    tmp_report["host"] = self.hostname
                    self.report["validateCoreMemoryRatio"] = tmp_report
                    return ("CHECK_COREMEMORYRATIO",self.hostname,"corememoryratio","",3,"The core to memory ratio for analytics does not apply for Virtual environments" ) 
            
            if self.report["validateCPU"]["status"] == "SUCESS":# this checks the ratio only for production systems (128GB for Power, 24576 for Intel 
                if self.ARCHITECTURE == "x86":
                    nbr, _ = map(str.strip, MEMInformationContainer["MemTotal"].split(" ", 2))
                    TotalMemory += int(int(nbr) / 1024 / 1024) # value in GB
                    cpu_name, _ = map(str.strip, CPUInformationContainer["cpu_name"].split("@", 2))
                    if "E7" and "v2" in cpu_name:
                        ratio = int(TotalMemory/int(CPUInformationContainer["logical"]))
                        if ratio <= 8.54:
                            tmp_report["status"] = "SUCESS"
                            tmp_report["host"] = self.hostname
                            self.report["validateCoreMemoryRatio"] = tmp_report
                            return ("CHECK_COREMEMORYRATIO",self.hostname,"corememoryratio","",0,"" )
                        else:
                            tmp_exception["type"] = "HIGH"
                            tmp_exception["reason"] = "The system has a non valid core-memory ratio for analytics"
                            self.exceptions["validateCoreMemoryRatio"] = tmp_exception
                            tmp_report["status"] = "FAILED"
                            tmp_report["host"] = self.hostname
                            self.report["validateCoreMemoryRatio"] = tmp_report
                            return ("CHECK_COREMEMORYRATIO",self.hostname,"corememoryratio","",4,"The system has a non valid core-memory ratio for analytics" )
                            
                    elif  "E7" and "v3" in cpu_name:
                        ratio = int(TotalMemory/int(CPUInformationContainer["logical"]))
                        if ratio <= 10.67:
                            tmp_report["status"] = "SUCESS"
                            tmp_report["host"] = self.hostname
                            self.report["validateCoreMemoryRatio"] = tmp_report
                            return ("CHECK_COREMEMORYRATIO",self.hostname,"corememoryratio","",0,"" )
                        else:
                            tmp_exception["type"] = "HIGH"
                            tmp_exception["reason"] = "The system has a non valid core-memory ratio for analytics"
                            self.exceptions["validateCoreMemoryRatio"] = tmp_exception
                            tmp_report["status"] = "FAILED"
                            tmp_report["host"] = self.hostname
                            self.report["validateCoreMemoryRatio"] = tmp_report
                            return ("CHECK_COREMEMORYRATIO",self.hostname,"corememoryratio","",4,"The system has a non valid core-memory ratio for analytics" )
                    elif "E5" in cpu_name:
                        tmp_report["status"] = "NOTAPPLICABLE"
                        tmp_report["host"] = self.hostname
                        self.report["validateCoreMemoryRatio"] = tmp_report
                        return ("CHECK_COREMEMORYRATIO",self.hostname,"corememoryratio","",3,"The core to memory ratio for analytics does not apply for E5 processors. Please check Note for correct configuration" ) 
                    elif "E7" in cpu_name:
                        print "hit"
                        ratio = int(TotalMemory/int(CPUInformationContainer["logical"]))
                        if ratio <= 6.4:
                            tmp_report["status"] = "SUCESS"
                            tmp_report["host"] = self.hostname
                            self.report["validateCoreMemoryRatio"] = tmp_report
                            return ("CHECK_COREMEMORYRATIO",self.hostname,"corememoryratio","",0,"" )
                        else:
                            tmp_exception["type"] = "HIGH"
                            tmp_exception["reason"] = "The system has a non valid core-memory ratio for analytics"
                            self.exceptions["validateCoreMemoryRatio"] = tmp_exception
                            tmp_report["status"] = "FAILED"
                            tmp_report["host"] = self.hostname
                            self.report["validateCoreMemoryRatio"] = tmp_report
                            return ("CHECK_COREMEMORYRATIO",self.hostname,"corememoryratio","",4,"The system has a non valid core-memory ratio for analytics" )
                    else:
                        tmp_exception["type"] = "HIGH"
                        tmp_exception["reason"] = "The system has a non valid core-memory ratio for analytics"
                        self.exceptions["validateCoreMemoryRatio"] = tmp_exception
                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateCoreMemoryRatio"] = tmp_report
                        return ("CHECK_COREMEMORYRATIO",self.hostname,"corememoryratio","",5,"The system has a non valid core-memory ratio for analytics" )
                        
                elif self.ARCHITECTURE == "ppc64":
                    nbr, _ = map(str.strip, MEMInformationContainer["MemTotal"].split(" ", 2))
                    TotalMemory += int(nbr)
                    nbr, _ = map(str.strip, CPUInformationContainer["cpus"].split(".", 2))
                    CPU += int(nbr)
                    ratio =  int(TotalMemory/CPU) # value in KB
                    ratio = int(ratio/1024) # Value in MB
                    if (TotalMemory <= 3 * 1024**3): # for configurations smaller than 3 TB the following ratio applies value in KB
                        if (ratio <= 32768): # the target is 32GB/1core value in MB
                            tmp_report["status"] = "SUCESS"
                            tmp_report["host"] = self.hostname
                            self.report["validateCoreMemoryRatio"] = tmp_report
                            return ("CHECK_COREMEMORYRATIO",self.hostname,"","",0,"" )
                        else:
                            tmp_exception["type"] = "MEDIUM"
                            tmp_exception["reason"] = "\nThe core to memory ratio of this system is 1 core/%s MB.\nPlease read SAP Note 2133369 for the default core to memory \nratio. Alternatively apply SAP Note 1903576 to configure this ratio differently in a supported manner." % (ratio)
                            self.exceptions["validateCoreMemoryRatio"] = tmp_exception
                            tmp_report["status"] = "FAILED"
                            tmp_report["host"] = self.hostname
                            self.report["validateCoreMemoryRatio"] = tmp_report
                            return ("CHECK_COREMEMORYRATIO",self.hostname,"corememoryratio","",3,tmp_exception["reason"])
                    else:
                        tmp_report["status"] = "NOTAPPLICABLE"
                        tmp_report["host"] = self.hostname
                        self.report["validateCoreMemoryRatio"] = tmp_report
                        return ("CHECK_COREMEMORYRATIO",self.hostname,"corememoryratio","",1,"Memory configuration is outside the range the core to memory ratio applies. This configuration is valid if SAP Note 2133369 and SAP Note 1903576 have been applied." )
                else: # ARCHITECTURE not set
                    print "Script Error in validateCoreMemoryRatio. Variable ARCHITECTURE not valid. Continue ..."
                    return ("CHECK_COREMEMORYRATIO",self.hostname,"ARCHITECTURE","",5,"Script Error in validateCoreMemoryRatio. Variable ARCHITECTURE not valid. Continue ...")
            else:
                tmp_report["status"] = "NOTAPPLICABLE"
                tmp_report["host"] = self.hostname
                self.report["validateCoreMemoryRatio"] = tmp_report
                return ("CHECK_COREMEMORYRATIO",self.hostname,"corememoryratio","",3,"This configuration can be run only for none-production systems. This is no supported production system." ) 
        except Exception,e:
            print e
        pass

    def validateApplianceSystemType(self):
        SystemInfromationContainer = self.getSYSTEMInfo()
        SupportedSystem = ['Express5800/A1080a [NE3100-xxxx]','Express5800/A1040a [NE3100-xxxx]','BladeSymphony E57A2', '7143',
                            '7147', '7145', '7148','7383','7914','7915','5460','3837','ProLiant DL580 Gen8','ProLiant DL580 Gen9',
                            'PowerEdge R920','PowerEdge R930','ProLiant ML350p Gen8','Compute Blade 2000 X57A2', 'Compute Blade E57A2',
                            'Lenovo WQ R680 G7','PowerEdge R620','PowerEdge T620','PRIMERGY RX600 S5', 'PRIMERGY RX900 S1', '738325Z]-',
                            'PRIMERGY RX900 S2','PRIMERGY RX600 S6','PRIMERGY RX300 S6','PRIMERGY RX350 S7', 'PRIMERGY TX300 S6',
                            'PRIMERGY TX300 S7','ProLiant DL980 G7','ProLiant DL580 G7','ProLiant BL680c G7','UCSC-BASE-M2-C460',
                            'C260-BASE-2646','B440-BASE-M2','Compute Blade 520XB1','R460-4640810','CH242 V3 8HDD','PowerEdge R910',
                            '-[7145]-','System x3850 X6','System x3950 X6','x3950 X6','x3850 X6','System x3690 X5','System x3650 M4',
                            'System x3550 M4','IBM System x3550 M4','System x3500 M4','System x3850 X5','System x3850 X5 / x3950 X5',
                            'Tecal RH5885 V2','Tecal RH5885 V3','VMware Virtual Platform','System x3950 X5','PRIMEQUEST 2400S',
                            'PRIMEQUEST 2400E','PRIMEQUEST 2400L','PRIMEQUEST 2800B','PRIMEQUEST 2800E','PRIMEQUEST 2800E2','PRIMEQUEST 2800L',
                            'bullion S','Cisco C880 M4','Compute Blade 520XB1','Flex System x880 X6 Compute Node -[7903FT6]-',
                            'NX7700x/A2010M-60 [NE3400-001Y]','PRIMERGY RX4770 M1','PRIMERGY RX4770 M2','RH8100 V3','Superdome2 16s',
                            'Superdome2 16s x86','System x3950 X6 -[3837AC4]-','Tecal RH5885H V3','RH5885H V3','UCSB-EX-M4-1','UCSC-C460-M4',
                            'UV300','3590R G3','Compute Blade 520XB2']
        tmp_exception = {}
        tmp_report = {}

        if SystemInfromationContainer["product_name"] in SupportedSystem:

            tmp_report["status"] = "SUCESS"
            tmp_report["host"] = self.hostname
            self.report["validateApplianceSystemType"] = tmp_report
            return ("CHECK_APPLIANCETYPE",self.hostname,"appliancetype",SystemInfromationContainer["product_name"],0,"" )
        else:
            tmp_exception["type"] = "HIGH"
            tmp_exception["reason"] = "'%s' is not a certified HANA Server. Due to new Validations this information can be outdated please look into the SAP HANA PAM for more details" % (SystemInfromationContainer["product_name"])
            self.exceptions["validateApplianceSystemType"] = tmp_exception
            tmp_report["status"] = "FAILED"
            tmp_report["host"] = self.hostname
            self.report["validateApplianceSystemType"] = tmp_report
            return ("CHECK_APPLIANCETYPE",self.hostname,"appliancetype",SystemInfromationContainer["product_name"],4," This is not a certified HANA Server. Due to new Validations this information can be outdated please look into the SAP HANA PAM for more details" )
        pass

    def validateCPUgovernor(self):
        CPUInformationContainer = self.getCPUInfo()
        frequency = []
        frequency2 = []
        tmp_exception = {}
        tmp_report = {}
        cmdline = []
        with open("/proc/cpuinfo") as file:
            lines = file.readlines()
            for line in lines:
                if ":" not in line:
                    continue
                key, value = map(str.strip, line.split(":", 2))
                if key == "cpu MHz":
                    frq, _ = map(str.strip, value.split(".", 2))
                    frequency.append(int(frq))

        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq") as file:
                lines = file.readlines()
                for line in lines:
                    frequency2.append(int(line)/1000)
        except Exception,e:
               pass
            
        with open("/proc/cmdline") as file:
            lines = file.readlines()
            for line in lines:
                cmdline.append(line)
        #print frequency
        if len(set(frequency)) != 1:
            tmp_exception["type"] = "HIGH"
            tmp_exception["reason"] = "CPUs are not running with nominal frequency"
            self.exceptions["validateCPUgovernor"] = tmp_exception
            tmp_report["status"] = "FAILED"
            tmp_report["host"] = self.hostname
            self.report["validateCPUgovernor"] = tmp_report
            return ("CHECK_CPUGOVERNOR",self.hostname,"frequencys","",4,"CPU power governor allows switching C-states, or CPUs are not running with nominal frequency" )
        elif (set(frequency) == CPUInformationContainer["frequency"]) or (set(frequency2) == set(frequency)) or ("max_cstate=0" in "\n".join(cmdline)):
            tmp_report["status"] = "SUCESS"
            tmp_report["host"] = self.hostname
            self.report["validateCPUgovernor"] = tmp_report
            return ("CHECK_CPUGOVERNOR",self.hostname,"cstate","",0,"" )
        else:
            tmp_exception["type"] = "HIGH"
            tmp_exception["reason"] = "CPU power governor allows switching C-states, or CPUs are not running with nominal frequency"
            self.exceptions["validateCPUgovernor"] = tmp_exception
            tmp_report["status"] = "FAILED"
            tmp_report["host"] = self.hostname
            self.report["validateCPUgovernor"] = tmp_report
            return ("CHECK_CPUGOVERNOR",self.hostname,"cstates","",4,"CPU power governor allows switching C-states, or CPUs are not running with nominal frequency" )
        pass


    def validateClocksource(self):
        LINUXInformationContainer = self.getLINUXInfo()
        tmp_exception = {}
        tmp_report = {}

        if self.ARCHITECTURE == "ppc64":
	    validClockSource = "timebase"
        else:
	    validClockSource = "tsc"

        if validClockSource in LINUXInformationContainer["clock"]:
            tmp_report["status"] = "SUCESS"
            tmp_report["host"] = self.hostname
            self.report["validateClocksource"] = tmp_report
            return ("CHECK_CLOCK",self.hostname,"clocksource",LINUXInformationContainer["clock"],0,"" )
        else:
            tmp_exception["type"] = "MEDIUM"
            tmp_exception["reason"] = "The clocksource %s can have a significant performance impact. " % (LINUXInformationContainer["clock"])
            self.exceptions["validateClocksource"] = tmp_exception
            tmp_report["status"] = "FAILED"
            tmp_report["host"] = self.hostname
            self.report["validateClocksource"] = tmp_report
            return ("CHECK_CLOCK",self.hostname,"clocksource",LINUXInformationContainer["clock"],4,"The clocksource can have a significant performance impact." )

        pass

    def validateTHP(self):
        LINUXInformationContainer = self.getLINUXInfo()
        tmp_exception = {}
        tmp_report = {}

        if "SUSE Linux Enterprise Server 11" in LINUXInformationContainer["distribution_name"] and LINUXInformationContainer["distribution_patchlevel"] == "3":

            value, _ = map(str.strip, LINUXInformationContainer["kernelrelease"].split("-",1))
            kernelversion, majorversion, minorrevison = map(str.strip, value.split(".",2))

            if (int(kernelversion) >= 3) and (int(majorversion) >= 0) and (int(minorrevison) >= 999):

                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateTHP"] = tmp_report

                return ("CHECK_THP",self.hostname,"thp",LINUXInformationContainer["thp"],0,"" )
            else:
                if "[never]" in LINUXInformationContainer["thp"]:
                    tmp_report["status"] = "SUCESS"
                    tmp_report["host"] = self.hostname
                    self.report["validateTHP"] = tmp_report
                    return ("CHECK_THP",self.hostname,"thp",LINUXInformationContainer["thp"],0,"" )
                else:
                    tmp_exception["type"] = "HIGH"
                    tmp_exception["reason"] = "Transparent hugepages is enabled, this can lead to a system stall \nduring memory defragmentation operation. \nFor More details: SAP Note 1954788 "
                    self.exceptions["validateTHP"] = tmp_exception
                    tmp_report["status"] = "FAILED"
                    tmp_report["host"] = self.hostname
                    self.report["validateTHP"] = tmp_report
                    return ("CHECK_THP",self.hostname,"thp",LINUXInformationContainer["thp"],4,"Transparent hugepages is enabled, this can lead to a system stall during memory defragmentation operation. For More details: SAP Note 1954788 " )

        elif "SUSE Linux Enterprise Server 11" in LINUXInformationContainer["distribution_name"] and LINUXInformationContainer["distribution_patchlevel"] == "2":

            value, _ = map(str.strip, LINUXInformationContainer["kernelrelease"].split("-",1))
            kernelversion, majorversion, minorrevison = map(str.strip, value.split(".",2))

            if (int(kernelversion) >= 3) and (int(majorversion) >= 0) and (int(minorrevison) >= 999):

                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateTHP"] = tmp_report

                return ("CHECK_THP",self.hostname,"thp",LINUXInformationContainer["thp"],0,"" )
            else:
                if "[never]" in LINUXInformationContainer["thp"]:
                    tmp_report["status"] = "SUCESS"
                    tmp_report["host"] = self.hostname
                    self.report["validateTHP"] = tmp_report

                    return ("CHECK_THP",self.hostname,"thp",LINUXInformationContainer["thp"],0,"" )

                else:
                    tmp_exception["type"] = "HIGH"
                    tmp_exception["reason"] = "Transparent hugepages is enabled, this can lead to a system stall \nduring memory defragmentation operation. \nFor More details: SAP Note 1824819"
                    self.exceptions["validateTHP"] = tmp_exception
                    tmp_report["status"] = "FAILED"
                    tmp_report["host"] = self.hostname
                    self.report["validateTHP"] = tmp_report
                    return ("CHECK_THP",self.hostname,"thp",LINUXInformationContainer["thp"],4,"Transparent hugepages is enabled, this can lead to a system stall during memory defragmentation operation. For More details: SAP Note 1824819 " )

        elif LINUXInformationContainer["distribution_name"] == "Red Hat Enterprise Linux Server release 6.5 (Santiago)":

            if "[never]" in LINUXInformationContainer["thp"]:
                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateTHP"] = tmp_report

                return ("CHECK_THP",self.hostname,"thp",LINUXInformationContainer["thp"],0,"" )
            else:
                tmp_exception["type"] = "HIGH"
                tmp_exception["reason"] = "Transparent hugepages is enabled, this can lead to a system stall \nduring memory defragmentation operation. \nFor More details: SAP Note 1824819"
                self.exceptions["validateTHP"] = tmp_exception
                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateTHP"] = tmp_report

                return ("CHECK_THP",self.hostname,"thp",LINUXInformationContainer["thp"],4,"Transparent hugepages is enabled, this can lead to a system stall during memory defragmentation operation. For More details: SAP Note 1824819 " )

        tmp_report["status"] = "SUCESS"
        tmp_report["host"] = self.hostname
        self.report["validateTHP"] = tmp_report
        return ("CHECK_THP",self.hostname,"thp",LINUXInformationContainer["thp"],0,"" )



    def getResult(self):

        self.__info["report"] = self.report
        self.__info["exceptions"] = self.exceptions

        return self.__info


    def tearDown(self):
        pass


    def tearDownMaster(self):
        pass


    def getMEMInfo(self):
       import os
       if self.mem is None:
           mem = {}
           dimmSize = []
           nodeSize = []
           dimmSpeedPys = []
           dimmSpeedConf = []
 
           f = os.popen("cat /proc/meminfo|grep MemTotal")

           for line in f.readlines():
               key, value = map(str.strip, line.split(":",1))
               if key == "MemTotal":
                   mem["MemTotal"] = value
               f.close()
 
               f = os.popen("numactl --hardware")
               for line in f.readlines():
                   if "size" in line:
                       if "MB" in line:
                           _, value = map(str.strip, line.split(":",1))
                           value, _ = map(str.strip, value.split(" ",1))
                           nodeSize.append(value)
               f.close()
               mem["nodeSize"] = nodeSize

           if self.ARCHITECTURE == "x86":
               f = os.popen("dmidecode --type 17")
               for line in f.readlines():
                   if "Size" in line:
                       if "MB" in line:
                            _, value = map(str.strip, line.split(":",1))
                            value, _ = map(str.strip, value.split(" ",1))
                            dimmSize.append(value)

                       if "GB" in line:
                            _, value = map(str.strip, line.split(":",1))
                            value, _ = map(str.strip, value.split(" ",1))
                            dimmSize.append(int(value)*1024)
 
                   if "Configured Clock Speed" in line:
                       if "MHz" in line:
                            _, value = map(str.strip, line.split(":",1))
                            value, _ = map(str.strip, value.split(" ",1))
                            dimmSpeedConf.append(value)
                       elif "Speed" in line:
                            if "MHz" in line:
                                 _, value = map(str.strip, line.split(":",1))
                                 value, _ = map(str.strip, value.split(" ",1))
                                 dimmSpeedPys.append(value)
 
               f.close()
               #these are collected only for x86
               mem["dimmSize"] = dimmSize
               mem["dimmSpeedPysical"] = dimmSpeedPys
               mem["dimmSpeedConfigured"] = dimmSpeedConf

           elif self.ARCHITECTURE == "ppc64":
               #check for AME/AMS
               f = os.popen("/usr/sbin/lparstat -i")
               for line in f:
                   key, value = map(str.strip, line.split(":",1))
                   if key == "Memory Mode" :
                       if "Expanded" in value:
                            mem["ame"] = value
                       else:
                            mem["ame"] = "disabled"
               f.close()
               f = os.popen("amsstat")
               for line in f:
                   if "not enabled" in line:
                       mem["ams"] = "disabled"
                   else:
                       mem["ams"] = "enabled"
               f.close()
           else:

               print "ERROR variable ARCHITECTURE not set or value not in list."

           self.mem = mem
           return mem
       else:
           return self.mem


    def getNETInfo(self):

        if self.net is None:

            import os

            net = {}
            slaves = []

            f = os.popen("ifconfig | grep eth")
            for line in f.readlines():
                iface, _ = map(str.strip, line.split(" ",1))
                if iface is not None and "eth" in iface:
                    net[iface] = {}
            f.close()


            f = os.popen("ifconfig | grep bond")
            for line in f.readlines():
                iface, _ = map(str.strip, line.split(" ",1))
                if iface is not None and "bond" in iface and ":" not in iface:
                    net[iface] = {}
                    slaves = []

                    f1 = os.popen("cat /proc/net/bonding/%s" % iface)

                    for line in f1.readlines():
                        if ":" not in line:
                            continue
                        _, slave = map(str.strip, line.split(":",1))

                        if "Slave Interface" in _:
                            slaves.append(slave)

                    f1.close()
                    net[iface]["slaves"] = slaves
            f.close()

            for ifacekey in net:

                f = os.popen("ethtool -i %s" % (ifacekey))
                for line in f.readlines():
                    key, value = map(str.strip, line.split(":",1))
                    if key == "bus-info":
                        if ":" in value:
                            _ , value = map(str.strip, value.split(":",1))
                            net[ifacekey]["bus-info"] = value
                f.close()

            #print net
            self.net = net
            return net
        else:
            return self.net

    def getLINUXInfo(self):

        if self.linux is None:


            import os

            linux = {}
            rpmlist = []
            rpmlist_ppc = []

            f = os.popen("uname -r")
            for line in f.readlines():
                linux["kernelrelease"] = line.rstrip()
            f.close()


            f = os.popen("cat /sys/devices/system/clocksource/clocksource0/current_clocksource")
            for line in f.readlines():
                linux["clock"] = line.rstrip()
            f.close()

            f = os.popen("rpm -qa")
            for line in f.readlines():
                 rpmlist.append(line.rstrip())
            f.close()
            linux["rpm"] = rpmlist

            f = os.popen("rpm -qa --qf '%{NAME}, %{VERSION}, %{RELEASE}\n'")
            for line in f.readlines():
                  rpmlist_ppc.append(line)
            f.close()
            linux["rpm-ppc"] = rpmlist_ppc

            # on ppc this package might not exists. initialize it to SUCCESS criteria
            linux["thp"] = "[never]"
            if os.path.exists("/sys/kernel/mm/transparent_hugepage/enabled"):
                f = os.popen("cat /sys/kernel/mm/transparent_hugepage/enabled")
                for line in f.readlines():
                    linux["thp"] = line.rstrip()
                f.close()


            f = os.popen("cat /etc/SuSE-release 2>/dev/null")
            for line in f.readlines():
                if "VERSION" in line:
                     _, value = map(str.strip, line.split("=",1))
                     linux["distribution_version"]= value

                elif "PATCHLEVEL" in line:
                     _, value = map(str.strip, line.split("=",1))
                     linux["distribution_patchlevel"] = value

                elif "SUSE" in line:
                     linux["distribution_name"] = line.rstrip()
            f.close()


            f = os.popen("cat /etc/redhat-release 2>/dev/null")
            for line in f.readlines():
                if "Red Hat" in line:
                    linux["distribution_name"] = line.rstrip()
            f.close()


            self.linux = linux
            return linux
        else:
            return self.linux


    def getSYSTEMInfo(self):

        if self.system is None:

            import os

            system = {}

            f = os.popen("dmidecode -s system-manufacturer")
            for line in f.readlines():
                system["manufacturer"] = line.rstrip()
            f.close()

            f = os.popen("dmidecode -s system-product-name")
            for line in f.readlines():
                system["product_name"] = line.rstrip()
            f.close()

            f = os.popen("dmidecode -s chassis-type")
            for line in f.readlines():
                system["chassis_type"] = line.rstrip()
            f.close()

            self.system = system
            return system
        else:
            return self.system


    def getCPUInfo(self):
      if self.cpu is None:

          import os
          import re
          cpu_name = "Unknown"
          cpu = {}
          flags = ""
          if self.ARCHITECTURE == "x86":
              cpus = []
              logical = []
              frequency = []
              physical = {}
              last_cpu = 0
              f=os.popen("cat /proc/cpuinfo")
              for line in f:
                  if ":" not in line:
                      continue
                  key, value = map(str.strip, line.split(":", 2))
                  if key == "physical id":
                      cpus.append(value)
                      last_cpu = value

                  elif key == "processor":
                      logical.append(value)

                  elif key == "cpu cores":
                      physical[last_cpu] = int(value)

                  elif key == "model name":
                      cpu_name = value

                  elif key == "flags":
                      flags = value
              f.close()
              f = os.popen("dmidecode -s processor-frequency")
              for line in f.readlines():
                  if "MHz" in line:
                      value, _ = map(str.strip, line.split(" ",1))
                      frequency.append(int(value))
              f.close()

              cpu["logical"] = len(set(logical))
              cpu["physical"] = reduce(lambda counter, item:counter + item[1], physical.items(), 0)
              cpu["cpus"] = len(set(cpus))
              cpu["cpu_name"] = cpu_name
              cpu["flags"] = flags 
              cpu["frequency"] = set(frequency)
              cpu["cpu_vers"] = ""
              self.cpu = cpu
              return cpu

          elif self.ARCHITECTURE == "ppc64":
              cpu_vers = ""
              cpu_name = ""
              lpar_type = ""
              cpus = ""
              smt = ""
              cpu_mode = ""
              cpu_mode_no = ""
              power_mode = "off"
              cpu_dscr = ""

              f = os.popen("LD_SHOW_AUXV=1 /bin/true")
              for line in f:
                  key, value = map(str.strip, line.split(":", 2))
                  if key == "AT_BASE_PLATFORM" :
                      cpu_name = value   #e.g. power7
                      cpu_vers = re.sub("[^0-9]", "",cpu_name)  #e.g. 7, 8, ..
                  if key == "AT_PLATFORM":
                      cpu_mode = value
                      cpu_mode_no =  re.sub("[^0-9]", "",cpu_mode)  #e.g. 7, 8, ..
              f.close()
              f = os.popen("/usr/sbin/lparstat -i")
              for line in f:
                  key, value = map(str.strip, line.split(":", 2))
                  if key == "Type" :
                      lpar_type = value   #e.g. dedicated
                  elif key == "Entitled Capacity" :
                      cpus = value   #e.g. number of dedicated CPUs
                  elif key == "Power Saving Mode" :
                      power_mode = value
              f.close()
              f = os.popen("/usr/bin/lscpu")
              for line in f:
                  key, value = map(str.strip, line.split(":", 2))
                  if key == "Thread(s) per core" :
                      smt = int(value)   # 1, 2, 4 8
              f.close()
              f = os.popen("/usr/sbin/ppc64_cpu --dscr")
              for line in f:
                  key, value = map(str.strip, line.split("is", 2))
                  if key == "DSCR" :
                      dscr = int(value)        
              cpu["cpu_name"] = cpu_name
              cpu["cpu_vers"] = cpu_vers
              cpu["lpar_type"] = lpar_type
              cpu["cpus"] = cpus
              cpu["smt"] = smt
              cpu["power_mode"] = power_mode
              cpu["cpu_mode"] = cpu_mode
              cpu["cpu_mode_no"] = cpu_mode_no
              cpu["cpu_dscr"] = dscr
              self.cpu = cpu
              return cpu

          else: # ARCHITECTURE not set
              print "Script Error in gatherCPUInfo. Variable ARCHITECTURE not valid. Continue ..."
              return ("CHECK_CPU",self.hostname,"ARCHITECTURE","",5,"Script Error in gatherCPUInfo. Variable ARCHITECTURE not valid. Continue ...")
      else:
          return self.cpu



    def gatherInfo(self):

        #Import needed libraries

        try:
            import subprocess
        except Exception, e:
            print "Import Failed"
            return False
        linux = {}
        log = ""


        #---------------------------Define Target Architecture-------------------------------
        f = subprocess.Popen(["uname -m"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()

        while line:
             if "ppc64" in line:
                 linux["ARCHITECTURE"] = "ppc64"
                 break
             else :
                 linux["ARCHITECTURE"] = "x86"
                 break

             line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()



        #---------------------------Distribution-------------------------------
        f = subprocess.Popen(["cat /etc/SuSE-release | grep -i SUSE"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()

        while line:
            linux["distribution"] = line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()


        #-----------------------Distribution-Version---------------------------
        f = subprocess.Popen(["cat /etc/SuSE-release | grep -i VERSION"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()

        while line:
            linux["distribution-version"] = line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------Distribution-Patchlevel------------------------
        f = subprocess.Popen(["cat /etc/SuSE-release | grep -i PATCHLEVEL"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()

        while line:
            linux["distribution-patchlevel"] = line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #---------------------------Distribution-------------------------------
        f = subprocess.Popen(["cat /etc/redhat-release"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()

        while line:
            linux["distribution"] = line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()


        #-----------------------RPM-List---------------------------------------
        f = subprocess.Popen(["rpm -qa"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["rpmlist"] = ""
        while line:
            linux["rpmlist"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------Kernelversion----------------------------------
        f = subprocess.Popen(["uname -r"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()

        while line:
            linux["kernelversion"] = line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------LSB_release----------------------------------
        f = subprocess.Popen(["lsb_release"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["lsb_release"] = ""
        while line:
            linux["lsb_release"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------Kernel-commandline---------------------------
        f = subprocess.Popen(["cat /proc/cmdline"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()

        while line:
            linux["kernel-command"] = line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------Date--------------------------------------
        f = subprocess.Popen(["date"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()

        while line:
            linux["date"] = line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------uptime--------------------------------------
        f = subprocess.Popen(["uptime"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()

        while line:
            linux["uptime"] = line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------ntp--------------------------------------
        f = subprocess.Popen(["ps -ef | grep -i ntp | grep -v grep"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["ntp"] = ""
        while line:
            linux["ntp"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------sysctl--------------------------------------
        f = subprocess.Popen(["cat /etc/sysctl.conf"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["sysctl"] = ""
        while line:
            linux["sysctl"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------mounts--------------------------------------
        f = subprocess.Popen(["cat /proc/mounts"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["mounts"] = ""
        while line:
            linux["mounts"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()
        #-----------------------localdisks--------------------------------------
        f = subprocess.Popen(["df -hl"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["disks"] = ""
        while line:
            linux["disks"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------physical volumes--------------------------------------
        f = subprocess.Popen(["pvs"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["pvs"] = ""
        while line:
            linux["pvs"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------volume groups--------------------------------------
        f = subprocess.Popen(["vgs"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["vgs"] = ""

        while line:
            linux["vgs"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------logical volumes-------------------------------
        f = subprocess.Popen(["lvs"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["lvs"] = ""
        while line:
            linux["lvs"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------crontab-------------------------------
        f = subprocess.Popen(["cat /etc/crontab"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["crontab"] = ""
        while line:
            linux["crontab"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------kernelmodule----------------------------
        f = subprocess.Popen(["cat /proc/sys/kernel/tainted"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["kernelmodule"] = ""
        while line:
            linux["kernelmodule"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------etc/hosts----------------------------
        f = subprocess.Popen(["cat /etc/hosts"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["hosts"] = ""
        while line:
            linux["hosts"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------hostname----------------------------
        f = subprocess.Popen(["hostname"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()

        while line:
            linux["hostname"] = line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------hostname----------------------------
        f = subprocess.Popen(["hostname -f"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()

        while line:
            linux["fullhostname"] = line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------lspci----------------------------
        f = subprocess.Popen(["lspci"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["lspci"] = ""
        while line:
            linux["lspci"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()
        # lspci is empty on ppc. A replacement os lscfg
        f = subprocess.Popen(["lscfg -v"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)
        line = f.stdout.readline()
        while line:
            linux["lspci"] += line

            line = f.stdout.readline()
        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()
        #-----------------------limits----------------------------
        f = subprocess.Popen(["cat /etc/security/limits.conf"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["limits"] = ""
        while line:
            linux["limits"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------ifcfg----------------------------
        f = subprocess.Popen(["ifconfig"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["ifconfig"] = ""
        while line:
            linux["ifconfig"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------intel specifics----------------------------
        if self.ARCHITECTURE == "x86":
           f = subprocess.Popen(["fio-status"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

           line = f.stdout.readline()
           linux["fio-status"] = ""
           while line:
               linux["fio-status"] += line

               line = f.stdout.readline()


           line = f.stderr.readline()
           while line:
               log += line

               line = f.stderr.readline()

        #-----------------------Power specifics----------------------------
        if  self.ARCHITECTURE == "ppc64":
            #-----------------------lparstat----------------------------
            f = subprocess.Popen(["/usr/sbin/lparstat -i"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)
            line = f.stdout.readline()
            linux["lparstat"] = ""
            while line:
                 linux["lparstat"] += line

                 line = f.stdout.readline()

            line = f.stderr.readline()
            while line:
                 log += line

                 line = f.stderr.readline()
            #-----------------------frequency----------------------------
            f = subprocess.Popen(["/usr/sbin/ppc64_cpu --frequency"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)
            line = f.stdout.readline()
            linux["ppc64_cpu--frequency"] = ""
            while line:
                 linux["ppc64_cpu--frequency"] += line

                 line = f.stdout.readline()

            line = f.stderr.readline()
            while line:
                 log += line

                 line = f.stderr.readline()
            #-----------------------lscpu--------------------------------
            f = subprocess.Popen(["/usr/bin/lscpu"],stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,shell=True)
            line = f.stdout.readline()
            linux["lscpu"] = ""
            while line:
                 linux["lscpu"] += line
                 line = f.stdout.readline()
            line = f.stderr.readline()

            while line:
                 log += line
                 line = f.stderr.readline()

        #-----------------------multipath----------------------------
        f = subprocess.Popen(["multipath -ll"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["multipath"] = ""
        while line:
            linux["multipath"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------route----------------------------
        f = subprocess.Popen(["route"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["route"] = ""
        while line:
            linux["route"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------swapon----------------------------
        f = subprocess.Popen(["swapon -s"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["swapon"] = ""
        while line:
            linux["swapon"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------java----------------------------
        f = subprocess.Popen(["java -version"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["java"] = ""
        while line:
            linux["java"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()


        #-----------------------clocksource----------------------------
        f = subprocess.Popen(["cat /sys/devices/system/clocksource/clocksource0/current_clocksource"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["clocksource"] = ""
        while line:
            linux["clocksource"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------transparent Hugepages----------------------------
        if self.ARCHITECTURE == "x86":
           f = subprocess.Popen(["cat /sys/kernel/mm/transparent_hugepage/enabled"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

           line = f.stdout.readline()
           linux["hugepages"] = ""
           while line:
               linux["hugepages"] += line

               line = f.stdout.readline()


           line = f.stderr.readline()
           while line:
               log += line

               line = f.stderr.readline()

           #-----------------------transparent Hugepages defrag----------------------------
           f = subprocess.Popen(["cat /sys/kernel/mm/transparent_hugepage/defrag"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

           line = f.stdout.readline()
           linux["hugepagesdefrag"] = ""
           while line:
               linux["hugepagesdefrag"] += line

               line = f.stdout.readline()


           line = f.stderr.readline()
           while line:
               log += line

               line = f.stderr.readline()

        #-----------------------governor----------------------------
        f = subprocess.Popen(["cpufreq-info | grep 'The governor'"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["governor"] = ""
        while line:
            linux["governor"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------numa----------------------------
        f = subprocess.Popen(["numactl --hardware"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["numa"] = ""
        while line:
            linux["numa"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------cpu----------------------------
        f = subprocess.Popen(["cat /proc/cpuinfo"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["cpuinfo"] = ""
        while line:
            linux["cpuinfo"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        #-----------------------meminfo----------------------------
        f = subprocess.Popen(["cat /proc/meminfo"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

        line = f.stdout.readline()
        linux["meminfo"] = ""
        while line:
            linux["meminfo"] += line

            line = f.stdout.readline()


        line = f.stderr.readline()
        while line:
            log += line

            line = f.stderr.readline()

        self.__info = linux
        return True


    @staticmethod
    def consolidateResults(config, results):

        import os
        chainvalkey = []
        for client, values in results["results"].iteritems():
            results = values
            if results["ARCHITECTURE"] == "x86":
                chainvalkey = ["validateDistribution","validateLinuxKernelVersion","validateRuntime","validateCPU","validateHTT","validateMemory","validateMemoryDistribution","validateHypervisor","validateCoreMemoryRatio","validateApplianceSystemType","validateCPUgovernor","validateTHP","validateClocksource"]
            else:
                chainvalkey = ["validateDistribution","validateLinuxKernelVersion","validateRuntime","validateCPU","validateHypervisor","validateHTT","validateMemory","validateCoreMemoryRatio","validateMemoryDistribution", "validateClocksource"]

            print "=" * 80
            print "EVALUATED SYSTEM SETUP ON %s : " %  (results["hostname"].rstrip())
            print "=" * 80
            for key in results["report"]:

                if key in chainvalkey:
                    print "%-28s:" % key,
                    if results["report"][key]["status"] == "SUCESS":
                        print '\033[1;32m{0:^80}\033[0m'.format("SUCCESS")
                    if results["report"][key]["status"] == "FAILED":
                        if results["exceptions"][key]["type"] == "HIGH":
                            print '\033[1;31m{0:^79}\033[0m'.format("FAILED")
                            print "\tseverity: %s" % results["exceptions"][key]["type"]
                            print "\treason  : %s\n" % results["exceptions"][key]["reason"]

                        else:
                            print '\033[1;33m{0:^80}\033[0m'.format("WARNING")
                            print "\tseverity: %s" % results["exceptions"][key]["type"]
                            print "\treason  : %s\n" % results["exceptions"][key]["reason"]

                    if results["report"][key]["status"] == "NOTAPPLICABLE":
                        print '\033[1;34m{0:^80}\033[0m'.format("SKIPPED")


                    print "-" * 80



            #print self.config["reportdir"]
            cwd = config["remote_base_dir"]
            #print cwd
            os.system("mkdir {pwd}/{dir}/LINUX/{hostname}".format(dir=config["reportdir"],pwd=cwd,hostname=results["hostname"].rstrip()))
            if results["hostname"]:
                for key in results:

                    try:
                        if key in ["report", "exceptions"]:
                            pass
                        else:

                            #print self.config["remote_base_dir"]
                            out = open("{pwd}/{rdir}/LINUX/{hostname}/{filekey}".format(pwd=cwd,rdir=config["reportdir"],hostname=results["hostname"].rstrip(), filekey=key),"w")
                            out.write(results[key].encode('utf8')) 
                            out.close()
                    except Exception,e:
                        print "failed to formatResults "
                        print e
                        return False


        return True
