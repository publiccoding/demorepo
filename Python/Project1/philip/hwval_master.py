import SocketServer
import threading
import hwval_client
import os
import time
import subprocess
import json
from threading import Thread, Lock
import sys
from random import choice
import string
import socket
import copy
import signal

### THIS IS NO CONFIGURATION PART ###

VERBOSE = False

HOSTNAME = socket.gethostbyaddr(socket.gethostname())[0]
LOCAL_USER = os.environ['USER']

# host : user
BLADES = {"localhost":None}

# (host,id):(user, port, token)
CLIENTS = {}
CONCLIENTS = {}

USE_HDB = False
SID = None
NUMBER = None
REMOTE_BASE_DIR = os.getcwd()+"/"
REPORT_ID = "test"
NFS = False
NO_SSH = False

KEY_FILE = os.environ["HOME"] + "/.ssh/id_rsa"
IDENTITY_FILE = os.environ["HOME"] + "/.ssh/identity.pub"

CLIENT_SCRIPT_NAME = hwval_client.THIS_FILE

local_ip = None
local_port = None

TESTS = {}
TESTS_WRITE_LOCK = Lock()
EXPORTLINE=None

server = None

sock = None

class ThreadedTCPRequestHandler(SocketServer.StreamRequestHandler):

    def handle(self):


        data = self.rfile.readline().strip()
        if data:
            #data = self.request[0].strip()
            #print("%s wrote: %s" % (self.client_address[0], data))
	    data = data.decode('utf8','ignore').encode('utf8')
            data = json.loads(data)


            token = data["token"]

            host = ""
            id = -1
            for blade, specs in CLIENTS.items():
                _blade, _id = blade
                user, _port, _token = specs
                if _token == token:
                    host = _blade
                    id = _id
                    break



            port = None
            if (host, id) in CLIENTS.keys():
                #print ("host: %s action: %s" % (host,data.get("action","")))

                reference = data.get("reference", "")
                action = data.get("action", "")
                status = data.get("status", False)
                port = data.get("port",False)


                with TESTS_WRITE_LOCK:

                    if action == "ALIVE":
                        user, port, token = CLIENTS[(host, id)]
                        #port = self.client_address[1]
                        port = data.get("port")
                        #print port
                        CLIENTS[(host, id)] = (user, port , token)

                        #CONCLIENTS[(host, id)] = self.wfile
                        if VERBOSE: print "Host %s is alive on port %s" % (host, port)
                    elif action == "CONFIGURED_TEST":
                        TESTS[reference]["configured"][(host, port)] = status
                    elif action == "PREPARED_TEST":
                        TESTS[reference]["prepared"][(host, port)] = status
                    elif action == "FINISHED_TEST":
                        TESTS[reference]["finished"][(host, port)] = status
                    elif action == "FINISHED_METHOD":
                        method_reference = data.get("method_reference", "")
                        if not method_reference in TESTS[reference].keys():
                            TESTS[reference][method_reference] = {}
                        TESTS[reference][method_reference][(host, port)] = status
                    elif action == "FINISHED_RESULTS":
                        results = data["result"]
                        TESTS[reference]["results"][(host, port)] = results
                        TESTS[reference]["gotresults"][(host, port)] = status
                    elif action == "CLEANEDUP_TEST":
                        TESTS[reference]["cleanedup"][(host, port)] = status
                    else:
                        raise Exception("Unknown action: %s" % action)


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

def mount_nfs():

    global BLADES
    global REMOTE_BASE_DIR
    global EXPORTLINE
    global server
    global NFS

    if not NFS:
        return True

    #Get working directory
    pwd=os.getcwd()
    EXPORTLINE=pwd+"    "


    print "Preparing blades for test execution..."
    #umount directory and prepare line for /etc/exports
    for host, user in BLADES.iteritems():
        user_prefix=""

        if (user == None or user == LOCAL_USER) and (host == "localhost" or host in HOSTNAME):
            if VERBOSE: print "Skipping mount for %s" % host
            return True
        if user is not None:
            user_prefix = "%s@" % user

        umountcmd=["ssh "+user_prefix+host+" -C umount -f '"+REMOTE_BASE_DIR+"'"]
        try:
            ret=subprocess.Popen(umountcmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell="/bin/bash").wait()
        except:
            print "it's ok, directory not mounted."
            pass
        EXPORTLINE=EXPORTLINE+" "+host+"(rw,no_root_squash)"

    EXPORTLINE=EXPORTLINE+"\n"

    #Write EXPORTLINE to /etc/exports
    with open("/etc/exports", "a") as exportsfile:
       exportsfile.write(EXPORTLINE)
       exportsfile.close()

    try:
        exportfscmd=["exportfs -fa"]
        ret1=subprocess.Popen(exportfscmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell="/bin/bash").wait()

    except:
        print "exportfs failed"
        sys.exit()

    #Create mountpoint on blades and mount NFS
    for host, user in BLADES.iteritems():
        user_prefix=""
        if user is not None:
            user_prefix = "%s@" % user

        mkdircmd=["ssh "+user_prefix+host+" -C mkdir '"+REMOTE_BASE_DIR+"'"]
        #print mkdircmd


        try:
            ret=subprocess.Popen(mkdircmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell="/bin/bash").wait()

        except:
            print "mkdir failed, maybe it already exists, so it's ok in most cases I think."
            sys.exit()


        mountcmd=["ssh "+user_prefix+host+" -C mount '-t nfs -vvv -o mountproto=tcp,sync "+HOSTNAME+":"+pwd+" "+REMOTE_BASE_DIR+"'"]
        #print mountcmd

        try:
            ret2=subprocess.Popen(mountcmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell="/bin/bash").wait()

        except:
            print "Mount failed"
            sys.exit()

    return True

def unmount_nfs():
    global EXPORTLINE
    global NFS

    if not NFS:
        return True
    print "Cleaning up blades..."
    #Unmount NFS on hosts
    for host, user in BLADES.iteritems():
        user_prefix=""

        if (user == None or user == LOCAL_USER) and (host == "localhost" or host in HOSTNAME):
            if VERBOSE: print "Skipping unmount for %s" % host
            return True

        if user is not None:
            user_prefix = "%s@" % user

        umountcmd=["ssh "+user_prefix+host+" -C umount -f '"+REMOTE_BASE_DIR+"'"]
        try:
            ret=subprocess.Popen(umountcmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell="/bin/bash").wait()
        except:
            print "WARNING: directory couldn't be unmounted, test may have failed."

    #Cleanup /etc/exports
    lines=list()
    with open("/etc/exports", "r") as exportsfileread:
        lines=exportsfileread.readlines()
        lines.remove(EXPORTLINE)
    with open("/etc/exports","w") as exportsfilewrite:
        for line in lines:
            exportsfilewrite.write(line)
    try:
        exportfscmd=["exportfs -ra"]
        ret1=subprocess.Popen(exportfscmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell="/bin/bash").wait()
    except:
        print "exportfs failed"
        pass

    #rmdir of mountpoint
    for host, user in BLADES.iteritems():
        user_prefix=""
        if user is not None:
            user_prefix = "%s@" % user

        rmdircmd=["ssh "+user_prefix+host+" -C rmdir '"+REMOTE_BASE_DIR+"'"]
        try:
            ret=subprocess.Popen(rmdircmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell="/bin/bash").wait()
        except:
            pass

def check_ssh():
    global BLADES, NO_SSH
    if NO_SSH:
	return True
    failed_hosts = []
    for host, user in BLADES.iteritems():
        user_prefix = ""

        if (user == None or user == LOCAL_USER) and (host == "localhost" or host in HOSTNAME):
            if VERBOSE: print "Skipping check for %s" % host
            continue


        if user is not None:
            user_prefix = "%s@" % user

        ret = subprocess.Popen(["ssh -o BatchMode=yes " + user_prefix + host + " sleep 0.1"], shell="/bin/bash", stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait()
        #print ret
        if ret > 0 and (host, user_prefix) not in failed_hosts:
            failed_hosts.append((host, user_prefix))

    if len(failed_hosts):
        for host, user_prefix in failed_hosts:
            print "Please prepare host %s%s for passwordless ssh connection." % (user_prefix, host)
            return False

    return True

def set_min_clients_per_host(num_clients):
    global BLADES, CLIENTS, USE_HDB, SID

    for blade_host, blade_user in BLADES.items():
        # count current clients
        count = 0
        max_id = 0
        for host, id in CLIENTS.keys():
            if blade_host == host:
                count += 1
                max_id = max(max_id, id)

        while count < num_clients:
            max_id += 1
            token = ''.join([choice(string.letters) for _c in range(5)])

            if ( max_id == 2 ):
                if(USE_HDB==True):
                    CLIENTS[(blade_host, max_id)] = (SID.lower()+"adm", None, token)
                else:
                    CLIENTS[(blade_host, max_id)] = (blade_user, None, token)

            if( max_id != 2 ):
                CLIENTS[(blade_host, max_id)] = (blade_user, None, token) # CLIENTS = {(hostname,id):(user,port,token)} !!
            count += 1

def start_missing_clients():
    global CLIENTS

    clients_to_start = {}

    for key, value in CLIENTS.items():
        (host, id), (user, port, token) = key, value
        if port is None:
            clients_to_start[(host, id)] = (user, port, token)

    return start_clients(clients_to_start, USE_HDB, SID, NUMBER, REMOTE_BASE_DIR)


def start_clients(hosts, use_hdb, sid, number, remote_base_dir):

    #print '>>>>>>>>>>>>>>', ','.join([ sid, number, remote_base_dir])

    ssh_clients_count = 0

    for host, specs in hosts.items():
        host, id = host
        user, _port, token = specs

        cmd = []


        if user is not None:
            if use_hdb and ("adm" in user):
                try:
                    if sid is not None and number is not None:
                        prefix = ""
                        cmd.append("/usr/sap/"+str(sid)+"/HDB%s/HDBSettings.sh" % str(number))
                        #
                        #cmd.append(os.path.join(dir, ))
                        #print ">>>><<",cmd

                    else:
                        #dir = os.environ["DIR_INSTANCE"]
                        print "Missing SID or NUMBER"
                except Exception, e:
                    print e
                    return False

        #cmd = [hdb_env, "/usr/bin/env", "python", CLIENT_SCRIPT_NAME, "-m", local_ip + ":" + str(local_port)]
        #cmd.append("/usr/bin/env")
        #cmd.append("export PYTHONPATH=$PYTHONPATH:/var/hwvaltestset/")
        #cmd.append("python")
	cmd.append(remote_base_dir+"lib/Python/bin/python")
        #print ">>>>>>>>>>>>",cmd
        #print remote_base_dir
        if remote_base_dir is not None:
            cmd.append(os.path.join(remote_base_dir, "hwval_client.py"))
        else:
            cmd.append(CLIENT_SCRIPT_NAME)
        cmd.append("-m")
        cmd.append(HOSTNAME + ":" + str(local_port))
        cmd.append("-t")
        cmd.append(token)

        if not ((user == None or user == LOCAL_USER) and (host == "localhost" or host in HOSTNAME) or (NO_SSH)):
            user_prefix = ""
            if user is not None:
                user_prefix = "%s@" % user

            ssh_ext = ["ssh", user_prefix + host]
            ssh_ext.extend(cmd)
            cmd = ssh_ext
            #print ">>>>>",cmd

            ssh_clients_count += 1

            if ssh_clients_count % 10 == 0:
                time.sleep(1)
        #print ">>>>>>>>>>>> "
        #print " ".join(cmd)+"\n"

        subprocess.Popen(cmd)
        time.sleep(1)
        #proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        #ClientWriter(proc.stdout, "%s" % host).start()
    return True

def wait_clients_up_and_running(timeout):

    global CLIENTS

    up_and_running = False

    current = 0

    while not up_and_running:
        if current > timeout:
            break
        up_and_running = True
        time.sleep(1)
        current += 1
        for _host, specs in CLIENTS.items():
            _user, port, _token = specs
            up_and_running = up_and_running and port is not None

    return up_and_running

def get_clients_per_host(num_clients):
    clients = {}

    current_count = {}

    for key, value in CLIENTS.items():
        (host, id), (user, port, token) = key, value
        count = current_count.get(host, 0)
        if count < num_clients:
            count += 1
            current_count[host] = count
            clients[(host, id)] = (user, port, token)

    return clients

class ClientWriter(Thread):
    def __init__(self, out, prefix):
        super(ClientWriter, self).__init__()
        self.out = out
        self.prefix = prefix


    def run(self):
        while True:
            line = self.out.readline()
            if not line:
                break
            sys.stdout.write("Client %20s: %s" % (self.prefix, line))

def message_to_clients(message, clients, clientSpecific=None):


    for host, specs in CLIENTS.items():
        _host, id = host
        _user, port, _token = specs
        message_for_client = copy.deepcopy(message)
        if clientSpecific is not None:
            clientData = clientSpecific.get((_host, id), None)
            if clientData is not None:
                __merge_dictionary(message_for_client, clientData)
        if port:
            sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            sock.connect((_host,port))
            #print "host:  %s port: %s" % (_host,_port)
            sock.setblocking(0)
            sock.sendall(json.dumps(message_for_client) + "\n")
            sock.close()
            sock = None


def __merge_dictionary(dst, src):
    stack = [(dst, src)]
    while stack:
        current_dst, current_src = stack.pop()
        for key in current_src:
            if key not in current_dst:
                current_dst[key] = current_src[key]
            else:
                if isinstance(current_src[key], dict) and isinstance(current_dst[key], dict) :
                    stack.append((current_dst[key], current_src[key]))
                else:
                    current_dst[key] = current_src[key]
    return dst

def wait_clients(reference, what, clients, timeout=0):
    time_already_waited = 0
    finished = clients == {}
    while not finished:
        time.sleep(0.2)
        time_already_waited += 0.2
        if timeout > 0 and time_already_waited >= timeout:
            break

        # potential bug, if array is not written properly
        finished = len(clients.keys()) == len(TESTS[reference].get(what, []))

        #finished = True
        #for blade, specs in clients.items():
        #    finished = finished and (blade, specs[1]) in TESTS[reference][what]

    return finished

def get_clients_that_passed(clients, test_id, what=[]):
    result = {}

    for host, specs in clients.items():
        host, id = host
        _user, port, _token = specs
        passed = True
        for phase in what:
            passed = passed and client_passed_phase(test_id, host, port, phase)
        if passed:
            result[(host, id)] = specs
    return result

def client_passed_phase(test_id, client, port, what):
    for key, status in TESTS[test_id][what].items():
        if (client , port) == key:
            return status
    return False

def signal_handler(signal, frame):
        print '\nAborting.....!'
        try:
            message_to_clients({"action":"KILL"}, CLIENTS)
            # wait for clients to stop
            server.shutdown()
            unmount_nfs()
            sys.exit()
        except Exception,e:
            print "hier"

def run_test(profile=None, verbose=False):

    global server, BLADES, CLIENTS, local_ip, local_port, TESTS, USE_HDB, SID, NUMBER, REMOTE_BASE_DIR, VERBOSE, NFS, HOSTNAME, NO_SSH

    VERBOSE = verbose

    signal.signal(signal.SIGINT, signal_handler)

    if profile is None:
        raise Exception("Please specify a profile when using as method!")

    config = profile

    CLIENTS = {}
    BLADES = {"localhost":None}
    NO_SSH = profile.get("no_ssh", NO_SSH)
    HOSTNAME = profile.get("master_host", HOSTNAME)
    SocketServer.ThreadingTCPServer.allow_reuse_address = True
    server = ThreadedTCPServer(("0.0.0.0", 0),ThreadedTCPRequestHandler)
    server.allow_reuse_address = True
    local_ip, local_port = server.server_address

    if "blades" in config.keys():
        BLADES = {}

        for blade in config["blades"]:
            hostname, user = blade, None
            if "@" in hostname:
                user, hostname = hostname.split("@")

            BLADES[hostname] = user

    USE_HDB = config.get("use_hdb", USE_HDB)
    SID = config.get("sid", SID)
    NFS = config.get("nfs", NFS)
    NUMBER = config.get("number", NUMBER)
    REMOTE_BASE_DIR = config.get("remote_base_dir", REMOTE_BASE_DIR)
    REPORT_PREFIX = config.get("report_id", REPORT_ID)

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)


    # Exit the server thread when the main thread terminates
    server_thread.start()

    if VERBOSE: print "Server loop running answering on %s:%i" % (local_ip, local_port)

    if VERBOSE: print "Checking SSH configuration for blades"
    if not check_ssh():
        server.shutdown()
        sys.exit()
    mount_nfs()

    if USE_HDB==True:
        set_min_clients_per_host(2)
    else:
        set_min_clients_per_host(1)


    if VERBOSE: print "Starting up clients"

    if not start_missing_clients():
        print "Aborting. Clients did not came up!"
        sys.exit()

    if wait_clients_up_and_running(timeout=60):
        total_test_counter = 0


        """
        Create report dir
        """
        dirtime = time.time()
        strdirtime = time.strftime("%m_%d_%Y-%H:%M:%S", time.localtime(dirtime))
        reportdir = "report_%s_%s" % (REPORT_PREFIX,strdirtime)
        subdir = ["LINUX","DISK","NET"]
        cwd = os.getcwd()

        try:
            os.system("mkdir {cwd}/{dir}".format(dir=reportdir,cwd=cwd))
            for elements in subdir:
                os.system("mkdir {cwd}/{dir}/{sdir}".format(cwd=cwd, dir=reportdir,sdir=elements))

        except Exception,e:
            print "Failed in Creating Reportdir"
            message_to_clients({"action":"KILL"}, CLIENTS)
            # wait for clients to stop
            server.shutdown()
            unmount_nfs()
            sys.exit()

        for test in config.get("tests", {}):
            total_test_counter += 1
            print "Running test %i/%i ..." % (total_test_counter, len(config.get("tests", {})))
            ### PROCESSING test config for input from other tests
            _test_config = test.get("config", {})

            test_config = {}
            test_config["sid"] = config.get("sid",SID)
            test_config["server"] = config.get("blades",BLADES)
            test_config["number"] = config.get("number", NUMBER)
            test_config["remote_base_dir"] = REMOTE_BASE_DIR

            for key, value in test.iteritems():

                if (type(value) == tuple or type(value) == list) and len(value) == 2:

                    ref, fallback = value

                    if isinstance(ref, basestring) and ref.startswith("REF:"):
                        test_id = int(ref[4:ref.find(":", 4)])
                        ref_name = ref[ref.find(":", 4) + 1:]
                        try:
                            value = TESTS[test_id]["output"][ref_name]
                        except KeyError:
                            value = fallback

                test[key] = value

            # TODO: remove the double code ^ v

            for key, value in _test_config.iteritems():

                if (type(value) == tuple or type(value) == list) and len(value) == 2:

                    ref, fallback = value

                    if isinstance(ref, basestring) and ref.startswith("REF:"):
                        test_id = int(ref[4:ref.find(":", 4)])
                        ref_name = ref[ref.find(":", 4) + 1:]
                        try:
                            value = TESTS[test_id]["output"][ref_name]
                        except KeyError:
                            value = fallback

                test_config[key] = value


            try:
                package_name = test["package"]
                class_name = test["class"]
                id = test["id"]
            except KeyError, e:
                print "Please specify a %s within your test configuration!" % e
                continue

            with TESTS_WRITE_LOCK:
                TESTS[id] = {"configured":{}, "prepared":{}, "finished":{}, "cleanedup":{}, "gotresults":{}, "results":{}}

            try:
                test_class = None
                exec("import %s" % package_name)
                exec("test_class = %s.%s" % (package_name, class_name))
            except Exception, e:
                print "Error loading test class %s.%s: %s" % (package_name, class_name, e)
                continue

            if(USE_HDB==True):
                num_clients_per_host = test.get("clients_per_host", 2)
            else:
                num_clients_per_host = test.get("clients_per_host", 1)



            ### STARTING ADDITIONAL CLIENTS
            set_min_clients_per_host(num_clients_per_host)
            start_missing_clients()

            if not wait_clients_up_and_running(timeout=60):
                print "Clients could not be spawned, skipping test."
                continue
            # TODO ROOT ADM Switcher
            ### get clients for this test
            clients = get_clients_per_host(num_clients_per_host)




            test_config["reportdir"] = reportdir

            ### CONFIGURE
            clientSpecific = None
            if VERBOSE: print "Configuring blades for test %s.%s" % (package_name, class_name)
            exec("clientSpecific = test_class.getClientSpecificConfig(clients,test_config)")
            message_to_clients({"action":"CONFIGURE_TEST",
                               "reference":id,
                               "package":package_name,
                               "class":class_name,
                               "config":test_config}, clients, clientSpecific)
            wait_clients(id, "configured", clients)
            if VERBOSE: print "All clients configured"

            ### PREPARE
            if VERBOSE: print "Preparing test %s.%s on clients" % (package_name, class_name)
            message_to_clients({"action":"PREPARE_TEST", "reference":id}, get_clients_that_passed(clients, id, ["configured"]))
            wait_clients(id, "prepared", get_clients_that_passed(clients, id, ["configured"]))
            if VERBOSE: print "All clients prepared"

            additionalSteps = []

            test_methods = test.get("test_methods", [])

            if test_methods == []:  ### legacy behaviour

                test_methods = ["runTest:%i" % test.get("test_timeout", 9)]


            call_queue = []

            i = 1

            for element in test_methods:
                if isinstance(element, basestring):
                    name = element
                    timeout = 0
                    if ":" in element:
                        name, timeout = element.split(":")
                        timeout = int(timeout)
                    call_queue.append((name, i, timeout, []))
                    i += 1
                else: # is array
                    deps_so_far = []
                    for dep_method in element:
                        name = dep_method
                        timeout = 0
                        if ":" in dep_method:
                            name, timeout = dep_method.split(":")
                            timeout = int(timeout)

                        call_queue.append((name, i, timeout, copy.deepcopy(deps_so_far)))
                        deps_so_far.append("%s_%i" % (name, i))
                        i += 1

            for method, method_id, timeout, dependencies in call_queue:
                #print "master %s " % method
                if VERBOSE: print "Starting test %s.%s.%s on clients with timeout %is" % (package_name, class_name, method, timeout)
                message_to_clients({"action":"RUN_METHOD", "reference":id, "method_reference":"%s_%s" % (method, method_id), "method":method}, get_clients_that_passed(clients, id, ["prepared"] + dependencies))
                processes_finished = wait_clients(id, "%s_%s" % (method, method_id), get_clients_that_passed(clients, id, ["prepared"] + dependencies), timeout=timeout)
                if not processes_finished:
                    if VERBOSE: print "Clients not yet finished with test %s.%s after timeout ... interrupting" % (package_name, class_name)
                    message_to_clients({"action":"INTERRUPT_TEST", "reference":id}, get_clients_that_passed(clients, id, ["prepared"] + dependencies))
                    wait_clients(id, "%s_%s" % (method, method_id), get_clients_that_passed(clients, id, ["prepared"] + dependencies))
                if VERBOSE: print "All clients finished test %s.%s.%s" % (package_name, class_name, method)
                additionalSteps.append("%s_%s" % (method, method_id))

            ### CLEANUP
            if VERBOSE: print "Cleaning up test %s.%s on clients" % (package_name, class_name)
            message_to_clients({"action":"CLEANUP_TEST", "reference":id}, clients)
            wait_clients(id, "cleanedup", clients)
            if VERBOSE: print "All clients finished cleanup"

            ### GET RESULTS
            if VERBOSE: print "Getting results for test %s.%s on clients" % (package_name, class_name)
            message_to_clients({"action":"GET_RESULTS", "reference":id}, get_clients_that_passed(clients, id, ["prepared"] + dependencies))
            wait_clients(id, "gotresults", clients)
            if VERBOSE: print "All clients finished"


            ### EXTRA METHODS
            results = TESTS[id]
            for method in test.get("result_methods", ["consolidateResults"]):
                try:
                    exec("results = test_class.%s(test_config,results)" % method)
                except Exception, e:
                    print "Error performing result method %s: %s" % (method, e)

            print "Test Process Summary:"
            print "---------------------"

            steps = ["configured", "prepared"] + additionalSteps + ["gotresults", "cleanedup"]

            print "%-26s" % "Host",
            for step in steps:
                theStep = step
                if "_" in step:
                    theStep = theStep[:theStep.rfind("_")]
                print '{0:^15}'.format(theStep),
            print

            for host, specs in clients.items():
                host, _id = host
                user, port, _token = specs

                print "%-26s" % (host + ":" + str(port)),

                for what in steps:
                    try:
                        status = TESTS[id][what][(host, port)]
                        print '{0:^15}'.format({True:"OK", False:"FAIL"}[status]),
                    except KeyError:
                        print '{0:^15}'.format("SKIPPED"),
                print

            print

    else:
        print "Timeout reached. Aborting!"

    if VERBOSE: print "Stopping clients"

    message_to_clients({"action":"KILL"}, CLIENTS)

    unmount_nfs()

    server.shutdown()
