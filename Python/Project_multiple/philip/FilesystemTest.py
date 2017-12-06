
from hwval_client import AbstractCheck
VERBOSITY = 0
OMIT = None
DEBUG = False


class DataVolumeIO(AbstractCheck):
    def configure(self, config={}):
        self.config = {}
        self.config.update(config)
        self.__info = {}
        self.results = {}
        self.hostname = None


        self.testconfig = {"short":{"4K":"1G",
                                    "16K":"5G",
                                    "64K":"5G",
                                    "1M":"5G",
                                    "16M":"5G",
                                    "64M":"5G"},
                            "long":{"4K":"5G",
                                    "16K":"16G",
                                    "64K":"16G",
                                    "1M":"16G",
                                    "16M":"16G",
                                    "64M":"16G"},
                            "verylong":{"4K":"10G",
                                        "16K":"32G",
                                        "64K":"32G",
                                        "1M":"32G",
                                        "16M":"32G",
                                        "64M":"32G"}}

        if not self.config["mount"]:
            print "Mount path missing"
            return False

        if not self.config["duration"]:
            self.config["duration"]="short"
            print "Duration missing, fall back to short duration Profile"
            return False

        if not self.testconfig[self.config["duration"]]:
            print "Wrong Duration value"
            return False



    def setUpMaster(self):
        pass

    def setUp(self):
        pass

    def runTest(self):
        import os
        user=""
        f = os.popen("whoami")

        for line in f.readlines():
            user=line

        f.close()

        if not self.runFstest():
           return False

    def getResult(self):
        return self.__info

    def tearDown(self):
        pass

    def prepareData(self):
        pass

    def tearDownMaster(self):
        pass

    def runFstest(self):

        #Import needed libraries

        import subprocess
        import sys, os
        from subprocess import Popen, PIPE, STDOUT


        f = subprocess.Popen(["hostname"],stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        line = f.stdout.readline()

        while line:

            self.results["hostname"] =line.rstrip("\n")
            line = f.stdout.readline()

        if self.results["hostname"] in self.config["mount"]:

            cwd = self.config["remote_base_dir"]
            environ = os.environ.copy()
            environ['LD_LIBRARY_PATH'] = "{pwd}lib".format(pwd=cwd)

            for blockSize in self.testconfig[self.config["duration"]]:

                mountpath = self.config["mount"][self.results["hostname"]][0]
                totalSize = self.testconfig[self.config["duration"]][blockSize]

                if not os.path.isdir(mountpath):
                    print "mountpath does not exist"
                    #raise Exception("mountpath does not exist")
                    return False

                fstestPath= "{pwd}lib/fstest recommend --verbose --random --total {total} --block {block} --path {path}".format(pwd=cwd,total=totalSize,block=blockSize,path=mountpath)

                environ = os.environ.copy()
                environ['LD_LIBRARY_PATH'] = "{pwd}lib".format(pwd=cwd)


                f = subprocess.Popen([fstestPath],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,env=environ,shell=True)


                line = f.stdout.readline()
                self.results[blockSize] = ""
                while line:

                    if "Max." in line:

                        self.results[blockSize] += "Data {block} : ".format(block=blockSize)+line

                    if "Path" in line:

                        self.results[blockSize] += "".format(block=blockSize)+line

                    if "IO order" in line:

                        self.results[blockSize] += "".format(block=blockSize)+line


                    if "Latency    sync." in line:

                        self.results[blockSize] += "Data Latency {block} : ".format(block=blockSize)+line

                    line = f.stdout.readline()


                line = f.stderr.readline()
                while line:

                    # removing newline character since line already have one
                    print "stderr "+line.rstrip("\n")

                    line = f.stderr.readline()

                f.wait()


        self.__info = self.results
        return True



    @staticmethod
    def formatResults(config, results):
        pass


    @staticmethod
    def consolidateResults(config, results):
        import os
        for client, values in results["results"].iteritems():
            try:

                if values["hostname"] in config["mount"]:
                    results = values
                    cwd = config["remote_base_dir"]

                    contention = len(config["mount"])
                    if values["hostname"]:
                        try:
                            #print self.config["remote_base_dir"]
                            out = open("{pwd}/{rdir}/DISK/{content}_contention_data_{hostname}".format(pwd=cwd,rdir=config["reportdir"],content=contention,hostname=values["hostname"]),"w")
                            for key in results:
                                if key != "hostname":
                                    out.write(results[key])
                                    out.write("\n")
                            out.close()
                        except Exception,e:
                            print "failed to formatResults"
                            raise Exception("failed to formatResults")
                            return False
            except Exception,e:
                return False

        return True

class BackupIO(AbstractCheck):
    def configure(self, config={}):
        self.config = {}
        self.config.update(config)
        self.__info = {}
        self.results = {}
        self.hostname = None
        self.testconfig = {"short":{"64M":"5G"},
                            "long":{"64M":"16G"},
                            "verylong":{"64M":"32G"}}


        if not self.config["mount"]:
            print "Mount path missing"
            return False

        if not self.config["duration"]:
            print "Duration missing"
            return False

        if not self.testconfig[self.config["duration"]]:
            print "Wrong Duration value"
            return False


    def setUpMaster(self):
        pass

    def setUp(self):
        pass

    def runTest(self):

        import os
        user=""
        f = os.popen("whoami")

        for line in f.readlines():
            user=line

        f.close()

        if "root" in user:
            if not self.runFstest():
                return False
        else:
            return False

    def getResult(self):
        return self.__info

    def tearDown(self):
        pass

    def prepareData(self):
        pass

    def tearDownMaster(self):
        pass

    def runFstest(self):

        #Import needed libraries

        import subprocess
        import sys, os
        from subprocess import Popen, PIPE, STDOUT


        f = subprocess.Popen(["hostname"],stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        line = f.stdout.readline()

        while line:

            self.results["hostname"] =line.rstrip("\n")

            line = f.stdout.readline()



        if self.results["hostname"] in self.config["mount"]:

            cwd = self.config["remote_base_dir"]
            environ = os.environ.copy()
            environ['LD_LIBRARY_PATH'] = "{pwd}lib".format(pwd=cwd)

            for blockSize in self.testconfig[self.config["duration"]]:

                mountpath = self.config["mount"][self.results["hostname"]][0]
                totalSize = self.testconfig[self.config["duration"]][blockSize]

                if not os.path.isdir(mountpath):
                    #raise Exception("mountpath does not exist")
                    print "ERROR: mountpath does not exist on %s" % self.results["hostname"]
                    return False


                fstestPath= "{pwd}lib/fstest recommend --verbose --sequential --total {total} --block {block} --path {path}".format(pwd=cwd,total=totalSize,block=blockSize,path=mountpath)

                environ = os.environ.copy()
                environ['LD_LIBRARY_PATH'] = "{pwd}lib".format(pwd=cwd)


                f = subprocess.Popen([fstestPath],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,env=environ,shell=True)


                line = f.stdout.readline()
                self.results[blockSize] = ""
                while line:
                    if "Max." in line:

                        self.results[blockSize] += "Backup {block} : ".format(block=blockSize)+line

                    if "Path" in line:

                        self.results[blockSize] += "".format(block=blockSize)+line

                    if "IO order" in line:

                        self.results[blockSize] += "".format(block=blockSize)+line

                    if "Latency    sync." in line:

                        self.results[blockSize] += "Backup Latency {block} : ".format(block=blockSize)+line

                    line = f.stdout.readline()


                line = f.stderr.readline()
                while line:

                    # removing newline character since line already have one
                    print "stderr "+line.rstrip("\n")

                    line = f.stderr.readline()

                f.wait()



        self.__info = self.results
        return True




    @staticmethod
    def formatResults(config, results):
        pass


    @staticmethod
    def consolidateResults(config, results):

        import os
        for client, values in results["results"].iteritems():
            try:


                if values["hostname"] in config["mount"]:
                    results = values
                    cwd = config["remote_base_dir"]

                    contention = len(config["mount"])
                    if values["hostname"]:
                        try:
                            #print self.config["remote_base_dir"]
                            out = open("{pwd}/{rdir}/DISK/{content}_contention_backup_{hostname}".format(pwd=cwd,rdir=config["reportdir"],content=contention,hostname=values["hostname"]),"w")
                            for key in results:
                                if key != "hostname":
                                    out.write(results[key])
                                    out.write("\n")
                            out.close()
                        except Exception,e:
                            print "--------------------------------------"
                            print e
                            print "failed to formatResults"
                            raise Exception("failed to formatResults")

                            return False
            except Exception,e:
                return False


        return True


class LogVolumeIO(AbstractCheck):
    def configure(self, config={}):
        self.config = {}
        self.config.update(config)
        self.__info = {}
        self.results = {}
        self.hostname = None

        self.testconfig = {"short":{"4K":"1G",
                                   "16K":"5G",
                                   "1M":"5G"},
                            "long":{"4K":"5G",
                                   "16K":"16G",
                                   "1M":"16G"},
                            "verylong":{"4K":"10G",
                                   "16K":"32G",
                                   "1M":"32G"}}


        if not self.config["mount"]:
            print "Mount path missing"
            return False

        if not self.config["duration"]:
            print "Duration missing"
            return False

        if not self.testconfig[self.config["duration"]]:
            print "Wrong Duration value"
            return False



    def setUpMaster(self):
        pass

    def setUp(self):
        pass

    def runTest(self):
        import os
        user=""
        f = os.popen("whoami")

        for line in f.readlines():
            user=line

        f.close()

        if "root" in user:
            if not self.runFstest():
                return False
        else:
            return False

    def getResult(self):
        return self.__info

    def tearDown(self):
        pass

    def prepareData(self):
        pass

    def tearDownMaster(self):
        pass

    def runFstest(self):

        #Import needed libraries

        import subprocess
        import sys, os
        from subprocess import Popen, PIPE, STDOUT


        f = subprocess.Popen(["hostname"],stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        line = f.stdout.readline()

        while line:

            self.results["hostname"] =line.rstrip("\n")

            line = f.stdout.readline()


        if self.results["hostname"] in self.config["mount"]:

            cwd = self.config["remote_base_dir"]
            environ = os.environ.copy()
            environ['LD_LIBRARY_PATH'] = "{pwd}lib".format(pwd=cwd)

            for blockSize in self.testconfig[self.config["duration"]]:

                mountpath = self.config["mount"][self.results["hostname"]][0]
                totalSize = self.testconfig[self.config["duration"]][blockSize]

                if not os.path.isdir(mountpath):
                    print "ERROR: mountpath does not exist on %s" % self.results["hostname"]
                    raise Exception("mountpath does not exist")
                    return False


                fstestPath= "{pwd}lib/fstest recommend --verbose --sequential --total {total} --block {block} --path {path}".format(pwd=cwd,total=totalSize,block=blockSize,path=mountpath)

                environ = os.environ.copy()
                environ['LD_LIBRARY_PATH'] = "{pwd}lib".format(pwd=cwd)


                f = subprocess.Popen([fstestPath],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,env=environ,shell=True)


                line = f.stdout.readline()
                self.results[blockSize] = ""
                while line:
                    if "Max." in line:

                        self.results[blockSize] += "Log {block} : ".format(block=blockSize)+line

                    if "Latency    sync." in line:

                        self.results[blockSize] += "Log Latency {block} : ".format(block=blockSize)+line

                    if "Path" in line:

                        self.results[blockSize] += "".format(block=blockSize)+line

                    if "IO order" in line:

                        self.results[blockSize] += "".format(block=blockSize)+line

                    line = f.stdout.readline()


                line = f.stderr.readline()
                while line:

                    # removing newline character since line already have one
                    print "stderr "+line.rstrip("\n")

                    line = f.stderr.readline()

                f.wait()


        self.__info = self.results
        return True



    @staticmethod
    def formatResults(config, results):
        pass


    @staticmethod
    def consolidateResults(config, results):
        import os

        for client, values in results["results"].iteritems():
            try:
                if values["hostname"] in config["mount"]:
                    results = values
                    cwd = config["remote_base_dir"]

                    contention = len(config["mount"])
                    if values["hostname"]:
                        try:
                            #print self.config["remote_base_dir"]
                            out = open("{pwd}/{rdir}/DISK/{content}_contention_log_{hostname}".format(pwd=cwd,rdir=config["reportdir"],content=contention,hostname=values["hostname"]),"w")
                            for key in results:
                                if key != "hostname":
                                    out.write(results[key])
                                    out.write("\n")
                            out.close()
                        except Exception,e:
                            print "failed to formatResults"
                            raise Exception("failed to formatResults")
                            return False

            except Exception,e:
                            return False
        return True

class MixedStressIO(AbstractCheck):
    def configure(self, config={}):
        self.config = {}
        self.config.update(config)
        self.__info = {}
        self.results = {}
        self.hostname = None

        self.testconfig = {"short":{"4K":"1G",
                                   "16K":"5G",
                                   "1M":"5G"},
                            "long":{"4K":"5G",
                                   "16K":"16G",
                                   "1M":"16G"},
                            "verylong":{"4K":"10G",
                                   "16K":"32G",
                                   "1M":"32G"}}


        if not self.config["mount"]:
            print "Mount path missing"
            return False

        if not self.config["duration"]:
            print "Duration missing"
            return False

        if not self.testconfig[self.config["duration"]]:
            print "Wrong Duration value"
            return False



    def setUpMaster(self):
        pass

    def setUp(self):
        pass

    def runTest(self):
        import os
        user=""
        f = os.popen("whoami")

        for line in f.readlines():
            user=line

        f.close()

        if "root" in user:
            if not self.runFstest():
                return False
        else:
            return False

    def getResult(self):
        return self.__info

    def tearDown(self):
        pass

    def prepareData(self):
        pass

    def tearDownMaster(self):
        pass

    def runFstest(self):

        #Import needed libraries

        import subprocess
        import sys, os
        from subprocess import Popen, PIPE, STDOUT


        f = subprocess.Popen(["hostname"],stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        line = f.stdout.readline()

        while line:

            self.results["hostname"] =line.rstrip("\n")

            line = f.stdout.readline()


        if self.results["hostname"] in self.config["mount"]:

            cwd = self.config["remote_base_dir"]

            for blockSize in self.testconfig[self.config["duration"]]:

                mountpath1 = self.config["mount"][self.results["hostname"]][0]
                mountpath2 = self.config["mount"][self.results["hostname"]][1]
                totalSize = self.testconfig[self.config["duration"]][blockSize]

                if not os.path.isdir(mountpath1):
                    print "first mountpath does not exist"
                    #raise Exception("first mountpath does not exist")
                    return False

                if not os.path.isdir(mountpath2):
                    print "second mountpath does not exist"
                    #raise Exception("second mountpath does not exist")
                    return False


                fstestPath1= "{pwd}lib/fstest recommend --verbose --random --total {total} --block {block} --path {path}".format(pwd=cwd,total=totalSize,block=blockSize,path=mountpath1)
                fstestPath2= "{pwd}lib/fstest recommend --verbose --sequential --total {total} --block {block} --path {path}".format(pwd=cwd,total=totalSize,block=blockSize,path=mountpath2)

                environ = os.environ.copy()
                environ['LD_LIBRARY_PATH'] = "{pwd}lib".format(pwd=cwd)


                f1 = subprocess.Popen([fstestPath1],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,env=environ,shell=True)
                f2 = subprocess.Popen([fstestPath2],stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=0,env=environ,shell=True)


                line = f1.stdout.readline()

                self.results["Data %s" % blockSize] = ""

                while line:

                    if "Max." in line:

                        self.results["Data %s" % blockSize] += "Data {block} : ".format(block=blockSize)+line

                    if "Latency    sync." in line:

                        self.results["Data %s" % blockSize] += "Data Latency {block} : ".format(block=blockSize)+line

                    if "Path" in line:

                        self.results["Data %s" % blockSize] += "".format(block=blockSize)+line

                    if "IO order" in line:

                        self.results["Data %s" % blockSize] += "".format(block=blockSize)+line

                    line = f1.stdout.readline()





                line = f1.stderr.readline()
                while line:

                    # removing newline character since line already have one
                    print "stderr "+line.rstrip("\n")

                    line = f1.stderr.readline()

                #####################################################################
		self.results["Log %s" % blockSize] = ""
                line2 = f2.stdout.readline()
                while line2:
                    if "Max." in line2:

                        self.results["Log %s" % blockSize] += "Log {block} : ".format(block=blockSize)+line2

                    if "Latency    sync." in line2:

                        self.results["Log %s" % blockSize] += "Log Latency {block} : ".format(block=blockSize)+line2

                    if "Path" in line2:

                        self.results["Log %s" % blockSize] += "".format(block=blockSize)+line2

                    if "IO order" in line2:

                        self.results["Log %s" % blockSize] += "".format(block=blockSize)+line2

                    line2 = f2.stdout.readline()


                line2 = f2.stderr.readline()
                while line2:

                    # removing newline character since line already have one
                    print "stderr "+line2.rstrip("\n")

                    line2 = f2.stderr.readline()


        self.__info = self.results
        return True


    @staticmethod
    def formatResults(config, results):
        pass


    @staticmethod
    def consolidateResults(config, results):

        import os
        for client, values in results["results"].iteritems():
            try:


                if values["hostname"] in config["mount"]:

                    results = values
                    cwd = config["remote_base_dir"]

                    contention = len(config["mount"])
                    if values["hostname"]:
                        try:
                            #print self.config["remote_base_dir"]
                            out = open("{pwd}/{rdir}/DISK/{content}_contention_mixed_{hostname}".format(pwd=cwd,rdir=config["reportdir"],content=contention,hostname=values["hostname"]),"w")
                            for key in results:
                                if key != "hostname":
                                    out.write(results[key])
                                    out.write("\n")
                            out.close()
                        except Exception,e:
                            print "failed to formatResults"
                            raise Exception("failed to formatResults")

                            return False
            except Exception,e:
                return False


        return True



