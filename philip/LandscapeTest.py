
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
        f = os.popen("uname -r")
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
        #determine architecture
            
        #self.__info["CPU"] = self.getCPUInfo()
        #self.__info["HDB"] = self.getHDBInfo()

        self.gatherInfo()
        #self.getCPUInfo()
        #self.getMEMInfo()
        #self.getLINUXInfo()
        #self.getSYSTEMInfo()
        self.getNETInfo()
        self.chainValidation()

        pass

    def chainValidation(self):

        self.validateDistribution()
        self.validateLinuxKernelVersion()
        self.validateRuntime()
        self.validateCPU()
        self.validateHTT()
        self.validateMemory()
        self.validateCPUgovernor()
        #self.validateMaxFileHandler()
        #/self.validateRPMlist()                # Function is not implemented/

        if self.ARCHITECTURE == "x86":
        	self.validateMemoryDistribution()
                self.validateBondEffectivity()
		self.validateHypervisor()        
		self.validateCoreMemoryRatio()  
		self.validateApplianceSystemType()
		self.validateTHP()	
		self.validateClocksource()
        
        #print self.report
        #print self.exceptions

        pass


    def validateDistribution(self):
        linuxInformationContainer = self.getLINUXInfo()
        tmp_exception = {}
        tmp_report = {}

        # print linuxInformationContainer

        try:

            if "SUSE Linux Enterprise Server 11" in linuxInformationContainer["distribution_name"]: 
                #ppc branch
		if self.ARCHITECTURE == "ppc64":
               	   if linuxInformationContainer["distribution_patchlevel"] == "3":
                       	
                      tmp_report["status"] = "SUCESS"
	              tmp_report["host"] = self.hostname
	              self.report["validateDistribution"] = tmp_report
	
        	      return True
                   else:
                      tmp_exception["type"] = "HIGH"
                      tmp_exception["reason"] = "Distribution Servicepack %s is not supported. Please see SAP Note 2055470 for more details." % linuxInformationContainer["distribution_patchlevel"]
	              self.exceptions["validateDistribution"] = tmp_exception

        	      tmp_report["status"] = "FAILED"
                      tmp_report["host"] = self.hostname
                      self.report["validateDistribution"] = tmp_report	
                    		
                #intel branch    						                
	        if self.ARCHITECTURE == "x86":  	
                   if linuxInformationContainer["distribution_patchlevel"] in ["1","2","3"]:

                       tmp_report["status"] = "SUCESS"
                       tmp_report["host"] = self.hostname
                       self.report["validateDistribution"] = tmp_report

                       return True
                   else:
                       tmp_exception["type"] = "HIGH"
                       tmp_exception["reason"] = "Distribution Servicepack %s is not supported." % linuxInformationContainer["distribution_patchlevel"]
                       self.exceptions["validateDistribution"] = tmp_exception

                       tmp_report["status"] = "FAILED"
                       tmp_report["host"] = self.hostname
                       self.report["validateDistribution"] = tmp_report

            elif linuxInformationContainer["distribution_name"] == "Red Hat Enterprise Linux Server release 6.5 (Santiago)":
                
                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateDistribution"] = tmp_report

            else: 
                tmp_exception["type"] = "HIGH"
                tmp_exception["reason"] = "Distribution %s is not supported." % linuxInformationContainer["distribution_name"]
                self.exceptions["validateDistribution"] = tmp_exception

                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateDistribution"] = tmp_report

                return False
        except Exception,e:
       	    tmp_exception["type"] = "HIGH"
            tmp_exception["reason"] = "Distribution is not supported."
            self.exceptions["validateDistribution"] = tmp_exception

            tmp_report["status"] = "FAILED"
            tmp_report["host"] = self.hostname
            self.report["validateDistribution"] = tmp_report

            return False


        pass

    def validateRuntime(self):
        linuxInformationContainer = self.getLINUXInfo()
        tmp_exception = {}
        tmp_report = {}
        libgcc_sles = ["libstdc++6-4.7.2_20130108-0.17.2","libgcc_s1-4.7.2_20130108-0.17.2"]
        libgcc_sles_ppc = ["libmpc2, 0.8.2, 1.7.1","libgcc_s1, 4.7.2, 0.17.2","libstdc++6, 4.7.2, 0.17.2","multipath-tools, 0, 0", "glibc, 2.11.3, 17.46.2"] #Format: Name, min. Version, min. Release 
        libgcc_rhel = ["compat-sap-c++-4.7.2-10.el6_5.x86_64"]
#print linuxInformationContainer["rpm"]
        try:

            if self.report["validateDistribution"]["status"] == "SUCESS" and "SUSE Linux Enterprise Server 11" in  linuxInformationContainer["distribution_name"]:
   	 	#ppc branch
		if self.ARCHITECTURE == "ppc64":
			for item in libgcc_sles_ppc:
                            itemname, itemversion, itemrelease = map(str.strip, item.split(",",3))
			    for rpmitem in linuxInformationContainer["rpm-ppc"]:
                              rpmname, rpmversion, rpmrelease = map(str.strip, rpmitem.split(",",3))
                              exists = 0
                              hasLevel = 0
	                      if itemname == rpmname:
                                     exists = 1
                                     #remove PTF Number
                                     itemversion = itemversion.split("_",1)[0]
                                     itemrelease = itemrelease.split("_",1)[0]
                                     rpmversion = rpmversion.split("_",1)[0]
                                     rpmrelease = rpmrelease.split("_",1)[0]
                                     #convert to integer
                                     itemrelease = int(itemrelease.replace('.',''))
                                     rpmrelease = int(rpmrelease.replace('.',''))
                                     itemverstion = int(itemversion.replace('.',''))
                                     rpmversion = int(rpmversion.replace('.',''))
                                     if (itemrelease > rpmrelease) and (itemversion > rpmversion):
				        break #release number is too small
                                     else:
                                        hasLevel = 1  
                                        break                                     
                            if exists == 0:                            
                       	         tmp_exception["type"] = "HIGH"
                                 tmp_exception["reason"] = "Runtime environment in this Distribution is not ready for HANA. Could not find %s. Please see SAP Note 2055470 for more details." % item
                                 self.exceptions["validateRuntime"] = tmp_exception
	
                                 tmp_report["status"] = "FAILED"
                                 tmp_report["host"] = self.hostname
                                 self.report["validateRuntime"] = tmp_report
                                 return False				
                            elif hasLevel == 0: 
                                 tmp_exception["type"] = "HIGH"
                                 tmp_exception["reason"] = "Runtime environment in this Distribution is not ready for HANA. The package %s is not at the minimum required level.  Please see SAP Note 2055470 for more details." % item
                                 self.exceptions["validateRuntime"] = tmp_exception

                                 tmp_report["status"] = "FAILED"
                                 tmp_report["host"] = self.hostname
                                 self.report["validateRuntime"] = tmp_report
                                 return False
                            else:
                                 continue
		#intel branch
                if self.ARCHITECTURE == "x86": 
                	for item in libgcc_sles:
	                    if item in linuxInformationContainer["rpm"]:
                        	continue
	
                    	    else:
                        	tmp_exception["type"] = "HIGH"
                        	tmp_exception["reason"] = "Runtime environment in this Distribution is not ready for HANA DSPS07 Revisions and HANA SPS08. Please see SAP Note 2001528 for more details"
                        	self.exceptions["validateRuntime"] = tmp_exception
	
                        	tmp_report["status"] = "FAILED"
                        	tmp_report["host"] = self.hostname
                        	self.report["validateRuntime"] = tmp_report
                        	return False


            elif self.report["validateDistribution"]["status"] == "SUCESS" and linuxInformationContainer["distribution_name"] == "Red Hat Enterprise Linux Server release 6.5 (Santiago)":

                for item in libgcc_rhel:
                    if item in linuxInformationContainer["rpm"]:
                        continue
     
                    else:
                        tmp_exception["type"] = "HIGH"
                        tmp_exception["reason"] = "Runtime environment in this Distribution is not ready for HANA DSPS07 Revisions and HANA SPS08. Please see SAP Note 2001528 for more details."
                        self.exceptions["validateRuntime"] = tmp_exception

                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateRuntime"] = tmp_report
                        return False


            tmp_report["status"] = "SUCESS"
            tmp_report["host"] = self.hostname
            self.report["validateRuntime"] = tmp_report


            return True
                
        except Exception,e:
                tmp_exception["type"] = "HIGH"
                tmp_exception["reason"] = "Problem in identifying Runtime Environment in OS Distribution."
                self.exceptions["validateRuntime"] = tmp_exception

                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateRuntime"] = tmp_report

                return False


        pass

    def validateLinuxKernelVersion(self):
        linuxInformationContainer = self.getLINUXInfo()
        tmp_exception = {}
        tmp_report = {}

        #print linuxInformationContainer

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

                        return True
                    else:
                        tmp_exception["type"] = "MEDIUM"
                        tmp_exception["reason"] = "Kernelversion %s is too low and might have bugs related to XFS" %  value
                        self.exceptions["validateLinuxKernelVersion"] = tmp_exception

                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateLinuxKernelVersion"] = tmp_report
                        return False

                elif linuxInformationContainer["distribution_patchlevel"] == "2":

                    value, _ = map(str.strip, linuxInformationContainer["kernelrelease"].split("-",1))
                    kernelversion, majorversion, minorrevison = map(str.strip, value.split(".",2))

                    if (int(kernelversion) >= 3) and (int(majorversion) >= 0) and (int(minorrevison) >= 101):

                        tmp_report["status"] = "SUCESS"
                        tmp_report["host"] = self.hostname
                        self.report["validateLinuxKernelVersion"] = tmp_report

                        return True
                    else:
                        tmp_exception["type"] = "MEDIUM"
                        tmp_exception["reason"] = "Kernelversion %s is too low and has some bugs that might affect the installation. For More details: SAP Note 1824819" % value
                        self.exceptions["validateLinuxKernelVersion"] = tmp_exception

                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateLinuxKernelVersion"] = tmp_report
                        return False
                elif linuxInformationContainer["distribution_patchlevel"] == "3":

                    value, _ = map(str.strip, linuxInformationContainer["kernelrelease"].split("-",1))
                    kernelversion, majorversion, minorrevison = map(str.strip, value.split(".",2))
	#Verify: I expect to have a minor of 101 to fix xfs bug also in SP03. 
        #        Is this same for Intel SUSE?
                    if (int(kernelversion) >= 3) and (int(majorversion) >= 0) and (int(minorrevison) >= 101):

                        tmp_report["status"] = "SUCESS"
                        tmp_report["host"] = self.hostname
                        self.report["validateLinuxKernelVersion"] = tmp_report

                        return True
                    else:
                        tmp_exception["type"] = "MEDIUM"
                        tmp_exception["reason"] = "Kernelversion %s is too low and has some bugs that might affect the installation. For More details: SAP Note 1954788"  % value
                        self.exceptions["validateLinuxKernelVersion"] = tmp_exception

                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateLinuxKernelVersion"] = tmp_report
                        return False

            else:
                tmp_report["status"] = "NOTAPPLICABLE"
                tmp_report["host"] = self.hostname
                self.report["validateLinuxKernelVersion"] = tmp_report

                return False
                
        except Exception,e:
                tmp_exception["type"] = "HIGH"
                tmp_exception["reason"] = "Problem in identifying Distribution and Linuxkernel relations"
                self.exceptions["validateLinuxKernelVersion"] = tmp_exception

                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateLinuxKernelVersion"] = tmp_report

                return False


        pass


    def validateCPU(self):
        CPUInformationContainer = self.getCPUInfo()
        tmp_exception = {}
        tmp_report = {}

        if CPUInformationContainer["cpu_name"] in ["Intel(R) Xeon(R) CPU E7- 8870  @ 2.40GHz","Intel(R) Xeon(R) CPU E7- 4870  @ 2.40GHz","Intel(R) Xeon(R) CPU E7- 2870  @ 2.40GHz",
                                                    "Intel(R) Xeon(R) CPU E7-8880 v2 @ 2.50GHz","Intel(R) Xeon(R) CPU E7-4880 v2 @ 2.50GHz","Intel(R) Xeon(R) CPU E7-2880 v2 @ 2.50GHz"
                                                    "Intel(R) Xeon(R) CPU E7-8890 v2 @ 2.80GHz","Intel(R) Xeon(R) CPU E7-4890 v2 @ 2.80GHz","Intel(R) Xeon(R) CPU E7-2890 v2 @ 2.80GHz"]:
            tmp_report["status"] = "SUCESS"
            tmp_report["host"] = self.hostname
            self.report["validateCPU"] = tmp_report

            return True
        #ppc    
        elif ("power7+" in CPUInformationContainer["cpu_name"]) or (int(CPUInformationContainer["cpu_vers"]) > 7):
            tmp_report["status"] = "SUCESS"
            tmp_report["host"] = self.hostname
            self.report["validateCPU"] = tmp_report

            return True    
       
        else:
            tmp_exception["type"] = "HIGH"
            tmp_exception["reason"] = "CPU Model %s is not Supported" % (CPUInformationContainer["cpu_name"])
            self.exceptions["validateCPU"] = tmp_exception
            tmp_report["status"] = "FAILED"
            tmp_report["host"] = self.hostname
            self.report["validateCPU"] = tmp_report
            return False


        pass

    def validateHTT(self):
        CPUInformationContainer = self.getCPUInfo()
        tmp_exception = {}
        tmp_report = {}
	if self.ARCHITECTURE == "x86":
        	if  CPUInformationContainer["logical"] == 2*CPUInformationContainer["physical"] and " ht " in CPUInformationContainer["flags"]:

        	 	tmp_report["status"] = "SUCESS"
        	    	tmp_report["host"] = self.hostname
            		self.report["validateHTT"] = tmp_report

	            	return True
        	else:
        	    	tmp_exception["type"] = "HIGH"
           	 	tmp_exception["reason"] = "Hyperthreading is not enabled"
           	 	self.exceptions["validateHTT"] = tmp_exception
            		tmp_report["status"] = "FAILED"
	            	tmp_report["host"] = self.hostname
	            	self.report["validateHTT"] = tmp_report
        	    	return False
        if self.ARCHITECTURE == "ppc64": 
                warning_txt = []
        	if  "Dedicated" not in CPUInformationContainer["lpar_type"]:
                   warning_txt.append('Shared Pool LPARs are not allowed for HANA on POWER systems. Only dedicated or dedicated donating partitions are supported.')
                if  ( CPUInformationContainer["smt"] < 4 ) :
                    warning_txt.append('This LPAR runs on less than four SMTs. Use lscpu to verify CPU settings. The command ppc64_cpu --smt=x can be used to dynamically increase SMT settings.')
                if CPUInformationContainer["power_mode"] != "off" :
        	     warning_txt.append('This partition is using AEM (IBM Active Energy Manager). This can decrease or increase performance characteristics of this partition dynamically during operations.')   	            
                if (len(warning_txt) == 0) :
                        tmp_report["status"] = "SUCESS"
            		tmp_report["host"] = self.hostname
	            	self.report["validateHTT"] = tmp_report

        	    	return True
        	else:
                        return_string = ''.join(warning_txt)
            		tmp_exception["type"] = "WARNING"
           	 	tmp_exception["reason"] = return_string
           	 	self.exceptions["validateHTT"] = tmp_exception
        	    	tmp_report["status"] = "FAILED"
	            	tmp_report["host"] = self.hostname
            		self.report["validateHTT"] = tmp_report
            	
        	    	return False
	
        pass


    def validateMemory(self):
        import re, os
        MEMInformationContainer = self.getMEMInfo()
        tmp_exception = {}
        tmp_report = {}
        AllowedMemoryConfiguration = [24576,49152,65536,131072,196608,262144,327680,393216,524288,1048576,2097152,4194304]
        TotalMemory = 0



	if self.ARCHITECTURE == "x86":
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

	           	return False

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
        
        	    	return False

        	if TotalMemory in AllowedMemoryConfiguration:
	        	tmp_report["status"] = "SUCESS"
           		tmp_report["host"] = self.hostname
	           	self.report["validateMemory"] = tmp_report
        	else:
    	        	tmp_exception["type"] = "HIGH"
	           	tmp_exception["reason"] = "TotalMemory Size is not an allowed memory configuration"
	            	self.exceptions["validateMemory"] = tmp_exception
	           	tmp_report["status"] = "FAILED"
        	    	tmp_report["host"] = self.hostname
	           	self.report["validateMemory"] = tmp_report
        
            		return False
        if self.ARCHITECTURE == "ppc64": #ppc branch
 			#	mem["ams"]
			#	mem["ame"] 
        	TotalMemory =  re.sub("[^0-9]", "",MEMInformationContainer["MemTotal"])
		if (int(TotalMemory) < 128000000) :     #value is in kb
                        tmp_exception["type"] = "HIGH"
                        tmp_exception["reason"] = "Less than 128 GB are configured to this HANA machine. 128 GB is the entry sizing for production systems. For None-Production the memory allocation might be sufficient."
                        self.exceptions["validateMemory"] = tmp_exception
                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateMemory"] = tmp_report
                        return False	
		if (MEMInformationContainer["ams"] == "disabled") and (MEMInformationContainer["ame"] == "disabled") :
        		tmp_report["status"] = "SUCESS"
           		tmp_report["host"] = self.hostname
	            	self.report["validateMemory"] = tmp_report
           	else:
   	        	tmp_exception["type"] = "HIGH"
			tmp_exception["reason"] = "Memory vitualization (AME or AMS) is not supported for HANA Systems on Power."
	        	self.exceptions["validateMemory"] = tmp_exception
	           	tmp_report["status"] = "FAILED"
	           	tmp_report["host"] = self.hostname
       		    	self.report["validateMemory"] = tmp_report
    
           		return False           
        pass




    def validateMemoryDistribution(self):
        MEMInformationContainer = self.getMEMInfo()
        tmp_exception = {}
        tmp_report = {}
        AllowedMemoryConfiguration = [24576,49152,65536,131072,196608,262144,327680,393216,524288,1048576,2097152,4194304]
        TotalMemory = 0

        for i in MEMInformationContainer["dimmSize"]:
            TotalMemory += int(i)

        if self.report["validateMemory"]["status"] == "SUCESS":

            if len(list(set(MEMInformationContainer["nodeSize"]))) == 1:

                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                return True
            elif len(list(set(MEMInformationContainer["nodeSize"]))) == 2:
                if int(MEMInformationContainer["nodeSize"][0]) < int(MEMInformationContainer["nodeSize"][1]) and int(MEMInformationContainer["nodeSize"][0]) > int(MEMInformationContainer["nodeSize"][1]) - int(MEMInformationContainer["dimmSize"][0]):
                    tmp_report["status"] = "SUCESS"
                    tmp_report["host"] = self.hostname
                    self.report["validateMemoryDistribution"] = tmp_report
                    return True
                else:

                    tmp_exception["type"] = "MEDIUM"
                    tmp_exception["reason"] = "Memory distribution is not fully balanced.. This may impact memory performance"
                    self.exceptions["validateMemoryDistribution"] = tmp_exception
                    tmp_report["status"] = "FAILED"
                    tmp_report["host"] = self.hostname
                    self.report["validateMemoryDistribution"] = tmp_report

            else:
                tmp_exception["type"] = "MEDIUM"
                tmp_exception["reason"] = "Memory distribution is not fully balanced.. This may impact memory performance"
                self.exceptions["validateMemoryDistribution"] = tmp_exception
                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateMemoryDistribution"] = tmp_report

                return False


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
                return False

            if TotalMemory in AllowedMemoryConfiguration:
                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateMemoryDistribution"] = tmp_report
            else:
                tmp_exception["type"] = "HIGH"
                tmp_exception["reason"] = "TotalMemory Size is not an allowed memory configuration"
                self.exceptions["validateMemoryDistribution"] = tmp_exception
                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateMemoryDistribution"] = tmp_report
                return False

        else:
            tmp_report["status"] = "NOTAPPLICABLE"
            tmp_report["host"] = self.hostname
            self.report["validateMemoryDistribution"] = tmp_report
            return False

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


        f = subprocess.Popen(["{cwd}scanhypervisor".format(cwd=self.config["remote_base_dir"])],stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        line = f.stdout.readline()

        while line:
            if "Vendor ID" in line:
                _, vendorid = map(str.strip, line.split(":", 1))

            if "Hypervisor" in line:
                _, hypervisor = map(str.strip, line.split(":", 1))


            line = f.stdout.readline()

        if "hypervisor" in CPUInformationContainer["flags"] or hypervisor is not None:
            if vendorid is not None and vendorid in ["XEN","VMwareVMware"]:

                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateHypervisor"] = tmp_report
                return True
            else:
                tmp_exception["type"] = "HIGH"
                tmp_exception["reason"] = "Hypervisor '%s' is not supported" % (vendorid)
                self.exceptions["validateHypervisor"] = tmp_exception
                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateHypervisor"] = tmp_report
                return False
        else:
            tmp_report["status"] = "NOTAPPLICABLE"
            tmp_report["host"] = self.hostname
            self.report["validateHypervisor"] = tmp_report
            return True

        pass


    def validateCoreMemoryRatio(self):
        MEMInformationContainer = self.getMEMInfo()
        CPUInformationContainer = self.getCPUInfo()
        tmp_exception = {}
        tmp_report = {}
        AllowedCPUMemoryConfiguration = {"20":[24576,49152,65536,131072],
                                         "40":[24576,49152,65536,131072,196608,262144],
                                         "80":[24576,49152,65536,131072,196608,262144,196608,262144,327680,393216,524288],
                                         "120":[24576,49152,65536,131072,196608,262144,196608,262144,327680,393216,524288,1048576],
                                         "160":[24576,49152,65536,131072,196608,262144,196608,262144,327680,393216,524288,1048576,2097152,4194304],
                                         "240":[24576,49152,65536,131072,196608,262144,196608,262144,327680,393216,524288,1048576,2097152,4194304]}
        TotalMemory = 0




        for i in MEMInformationContainer["dimmSize"]:
            TotalMemory += int(i)


        if self.report["validateMemory"]["status"]=="SUCESS" and self.report["validateCPU"]["status"] =="SUCESS":

            if TotalMemory in AllowedCPUMemoryConfiguration[str(CPUInformationContainer["logical"])]:

                tmp_report["status"] = "SUCESS"
                tmp_report["host"] = self.hostname
                self.report["validateCoreMemoryRatio"] = tmp_report
            else:
                tmp_exception["type"] = "HIGH"
                tmp_exception["reason"] = "The system has a non valid core-memory ratio"
                self.exceptions["validateCoreMemoryRatio"] = tmp_exception
                tmp_report["status"] = "FAILED"
                tmp_report["host"] = self.hostname
                self.report["validateCoreMemoryRatio"] = tmp_report
        else:
            tmp_report["status"] = "NOTAPPLICABLE"
            tmp_report["host"] = self.hostname
            self.report["validateCoreMemoryRatio"] = tmp_report
            return False


        pass

    def validateApplianceSystemType(self):
        SystemInfromationContainer = self.getSYSTEMInfo()
        SupportedSystem = ['Express5800/A1080a [NE3100-xxxx]','Express5800/A1040a [NE3100-xxxx]','BladeSymphony E57A2','System x3950 X5 -[7143H2G]-',
                            'System x3950 X5 -[7147H2G]-', 'System x3950 X5 -[7145H2G]-','System x3950 X5 -[7148H2G]-','ProLiant ML350p Gen8',
                            'Compute Blade 2000 X57A2', 'Compute Blade E57A2','Lenovo WQ R680 G7','PRIMERGY RX600 S5', 'PRIMERGY RX900 S1', '738325Z]-',
                            'PRIMERGY RX900 S2','PRIMERGY RX600 S6','PRIMERGY RX300 S6','PRIMERGY RX350 S7', 'PRIMERGY TX300 S6','PRIMERGY TX300 S7',
                            'ProLiant DL980 G7','ProLiant DL580 G7','ProLiant BL680c G7','UCSC-BASE-M2-C460','C260-BASE-2646','B440-BASE-M2','R460-4640810',
                            'PowerEdge R910', '-[7145]-','System x3690 X5','System x3850 X5','System x3850 X5 / x3950 X5', 'VMware Virtual Platform','System x3950 X5', "PRIMEQUEST 2800B"]
        tmp_exception = {}
        tmp_report = {}

        if SystemInfromationContainer["product_name"] in SupportedSystem:

            tmp_report["status"] = "SUCESS"
            tmp_report["host"] = self.hostname
            self.report["validateApplianceSystemType"] = tmp_report
        else:
            tmp_exception["type"] = "HIGH"
            tmp_exception["reason"] = "'%s' is not a certified HANA Server. Due to new Validations this information can be outdated please look into the SAP HANA PAM for more details" % (SystemInfromationContainer["product_name"])
            self.exceptions["validateApplianceSystemType"] = tmp_exception
            tmp_report["status"] = "FAILED"
            tmp_report["host"] = self.hostname
            self.report["validateApplianceSystemType"] = tmp_report


        pass

    def validateCPUgovernor(self):
        CPUInformationContainer = self.getCPUInfo()
        frequency = []
        frequency2 = []
        tmp_exception = {}
        tmp_report = {}
        if self.ARCHITECTURE =="x86" :
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



           #print frequency
           if len(set(frequency)) != 1:

               tmp_exception["type"] = "HIGH"
               tmp_exception["reason"] = "CPU power governor allows switching C-states, or CPUs are not running with nominal frequency"
               self.exceptions["validateCPUgovernor"] = tmp_exception
               tmp_report["status"] = "FAILED"
               tmp_report["host"] = self.hostname
               self.report["validateCPUgovernor"] = tmp_report



           elif set(frequency) == CPUInformationContainer["frequency"] or set(frequency2) == set(frequency):
               tmp_report["status"] = "SUCESS"
               tmp_report["host"] = self.hostname
               self.report["validateCPUgovernor"] = tmp_report

           else:
               tmp_exception["type"] = "HIGH"
               tmp_exception["reason"] = "CPU power governor allows switching C-states, or CPUs are not running with nominal frequency"
               self.exceptions["validateCPUgovernor"] = tmp_exception
               tmp_report["status"] = "FAILED"
               tmp_report["host"] = self.hostname
               self.report["validateCPUgovernor"] = tmp_report
        elif self.ARCHITECTURE =="ppc64" :
               #power has always right governors as this is static as of today.
               tmp_report["status"] = "SUCESS"
               tmp_report["host"] = self.hostname
               self.report["validateCPUgovernor"] = tmp_report
        pass


    def validateBondEffectivity(self):
        NETInformationContainer = self.getNETInfo()
        bond= {}
        tmp_exception = {}
        tmp_report = {}
        bus = []
        hit = False
        #print NETInformationContainer
        for key in NETInformationContainer:

            if "bond" in key:
                hit = True
                break
            else:
                hit = False

        if hit == False:

            tmp_report["status"] = "NOTAPPLICABLE"
            tmp_report["host"] = self.hostname
            self.report["validateBondEffectivity"] = tmp_report
            return False


        for key in NETInformationContainer:

            if "bond" in key:
                bus = []
                for slave in NETInformationContainer[key]["slaves"]:
                    businfo = NETInformationContainer[slave]["bus-info"]
                    dev, func = map(str.strip, businfo.split(".",1))
                    bus.append(dev)


                bond[key] = bus
            for key in bond:


                if len(set(bond[key])) ==1:

                    tmp_exception["type"] = "MEDIUM"
                    tmp_exception["reason"] = "Slave interfaces on bond dev %s are on the same physical device.\n This configuration may reduce the effectivity of HA during PCI card failure.  " % (key)
                    self.exceptions["validateBondEffectivity"] = tmp_exception
                    tmp_report["status"] = "FAILED"
                    tmp_report["host"] = self.hostname
                    self.report["validateBondEffectivity"] = tmp_report
                    return False
                else:
                    tmp_report["status"] = "SUCESS"
                    tmp_report["host"] = self.hostname
                    self.report["validateBondEffectivity"] = tmp_report

        pass

    def validateClocksource(self):
        LINUXInformationContainer = self.getLINUXInfo()
        tmp_exception = {}
        tmp_report = {}


	if "tsc" in LINUXInformationContainer["clock"]:
	    tmp_report["status"] = "SUCESS"
            tmp_report["host"] = self.hostname
            self.report["validateClocksource"] = tmp_report
	    return True
	else:
	    tmp_exception["type"] = "MEDIUM"
            tmp_exception["reason"] = "The clocksource %s can have a significant performance impact. " % (LINUXInformationContainer["clock"])
            self.exceptions["validateClocksource"] = tmp_exception
            tmp_report["status"] = "FAILED"
            tmp_report["host"] = self.hostname
            self.report["validateClocksource"] = tmp_report
            return False



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

                        return True
                    else:
                        if "[never]" in LINUXInformationContainer["thp"]:
                            tmp_report["status"] = "SUCESS"
                            tmp_report["host"] = self.hostname
                            self.report["validateTHP"] = tmp_report

                        else:
                            tmp_exception["type"] = "HIGH"
                            tmp_exception["reason"] = "Transparent hugepages is enabled, this can lead to a system stall during memory defragmentation operation. For More details: SAP Note 1954788 "
                            self.exceptions["validateTHP"] = tmp_exception
                            tmp_report["status"] = "FAILED"
                            tmp_report["host"] = self.hostname
                            self.report["validateTHP"] = tmp_report
                            return False

        elif "SUSE Linux Enterprise Server 11" in LINUXInformationContainer["distribution_name"] and LINUXInformationContainer["distribution_patchlevel"] == "2":

                    value, _ = map(str.strip, LINUXInformationContainer["kernelrelease"].split("-",1))
                    kernelversion, majorversion, minorrevison = map(str.strip, value.split(".",2))

                    if (int(kernelversion) >= 3) and (int(majorversion) >= 0) and (int(minorrevison) >= 999):

                        tmp_report["status"] = "SUCESS"
                        tmp_report["host"] = self.hostname
                        self.report["validateTHP"] = tmp_report

                        return True
                    else:
                        if "[never]" in LINUXInformationContainer["thp"]:
                            tmp_report["status"] = "SUCESS"
                            tmp_report["host"] = self.hostname
                            self.report["validateTHP"] = tmp_report

                            return True

                        else:
                            tmp_exception["type"] = "HIGH"
                            tmp_exception["reason"] = "Transparent hugepages is enabled, this can lead to a system stall during memory defragmentation operation. For More details: SAP Note 1824819"
                            self.exceptions["validateTHP"] = tmp_exception
                            tmp_report["status"] = "FAILED"
                            tmp_report["host"] = self.hostname
                            self.report["validateTHP"] = tmp_report
                            return False

        elif LINUXInformationContainer["distribution_name"] == "Red Hat Enterprise Linux Server release 6.5 (Santiago)":

                    if "[never]" in LINUXInformationContainer["thp"]:
                        tmp_report["status"] = "SUCESS"
                        tmp_report["host"] = self.hostname
                        self.report["validateTHP"] = tmp_report

                        return True
                    else:
                        tmp_exception["type"] = "HIGH"
                        tmp_exception["reason"] = "Transparent hugepages is enabled, this can lead to a system stall during memory defragmentation operation. For More details: SAP Note 1824819"
                        self.exceptions["validateTHP"] = tmp_exception
                        tmp_report["status"] = "FAILED"
                        tmp_report["host"] = self.hostname
                        self.report["validateTHP"] = tmp_report
                        
                        return False

        pass





    def getResult(self):


        self.__info["report"] = self.report
        self.__info["exceptions"] = self.exceptions

        return self.__info


    def tearDown(self):
        pass


    def tearDownMaster(self):
        pass


    def getMEMInfo(self):

	if self.mem is None:
    		import os

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

			
		if self.ARCHITECTURE == "ppc64":
			#check for AME/AMS
			f = os.popen("lparstat -i")
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
		if self.ARCHITECTURE == "x86":
			cpus = []
           		logical = []
        		frequency = []
    	    		physical = {}
	        	last_cpu = 0
    	    		with open("/proc/cpuinfo") as file:
	      			lines = file.readlines()
		
	            		for line in lines:
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
           			#print cpu
	
           		self.cpu = cpu
           		return cpu
	            	
		if self.ARCHITECTURE == "ppc64":
                        cpu_vers = ""
                        lpar_type = ""
                        cpus = ""
                        smt = ""
                        power_mode = "off"
                        f = os.popen("LD_SHOW_AUXV=1 /bin/true")
                        for line in f:
                              key, value = map(str.strip, line.split(":", 2))     
                              if key == "AT_BASE_PLATFORM" :
	        			cpu_name = value   #e.g. power7+ 
	         			cpu_vers = re.sub("[^0-9]", "",cpu_name)  #e.g. 7, 8, ..
                        f.close()      
                        f = os.popen("lparstat -i") 
			for line in f:
	   			key, value = map(str.strip, line.split(":", 2))
                                if key == "Type" :
	      				lpar_type = value   #e.g. dedicated
      				if key == "Entitled Capacity" :
	      				cpus = value   #e.g. number of dedicated CPUs
                                if key == "Power Saving Mode" :
                                        power_mode = value
			f.close()
                        f = os.popen("lscpu")
                        for line in f:
                                key, value = map(str.strip, line.split(":", 2))
                                if key == "Thread(s) per core" :
                                        smt = int(value)   # 1, 2, 4 8
                        f.close()
										
                        cpu["cpu_name"] = cpu_name
			cpu["cpu_vers"] = cpu_vers
			cpu["lpar_type"] = lpar_type
			cpu["cpus"] = cpus	
		        cpu["smt"] = smt
		        cpu["power_mode"] = power_mode		
            		self.cpu = cpu
	            	return cpu
            	
   		else:
			print "ERROR in exception handling def gatherCPUInfo()"
        	#error handling for invalid architecture
            
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
        f = subprocess.Popen(["uname -r"],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,shell=True)

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

        #-----------------------fio-status----------------------------
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
                chainvalkey = ["validateDistribution","validateLinuxKernelVersion","validateRuntime","validateCPU","validateHTT","validateMemory","validateMemoryDistribution","validateHypervisor","validateCoreMemoryRatio","validateApplianceSystemType","validateCPUgovernor","validateBondEffectivity","validateTHP","validateClocksource"]
            else:
                chainvalkey = ["validateDistribution","validateLinuxKernelVersion","validateRuntime","validateCPU","validateHTT","validateMemory","validateCPUgovernor"]


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
                            out.write(results[key])
                            out.close()
                    except Exception,e:
                        print "failed to formatResults "
                        print e
                        return False


        return True




