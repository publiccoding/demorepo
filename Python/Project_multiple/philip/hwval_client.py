
import SocketServer
import threading
import getopt
import sys
import os
import json
import traceback
import socket
from threading import Lock

HOSTNAME = socket.gethostname()

master_host = None
master_port = None

server = None

THIS_FILE = os.path.join(os.getcwd(), __file__)

TESTS = {}
TESTS_WRITE_LOCK = Lock()

TOKEN = ""

class ThreadedTCPRequestHandler(SocketServer.StreamRequestHandler):

    def handle(self):
        data = self.rfile.readline().strip()
        data = data+self.rfile.readline().strip()
        if data:
            data = json.loads(data)
            if data['action'] == "KILL":
                server.shutdown()

            elif data['action'] == "CONFIGURE_TEST":
                #print "CONFIGURE_TEST"
                status = True
                reference = data["reference"]
                package = data["package"]
                clazz = data["class"]
                config = data["config"]

                for key, value in config.iteritems():
                    if isinstance(value, basestring) and value.find("CTX:UNIQUE") > -1:
                        value = value.replace("CTX:UNIQUE", TOKEN)
                        config[key] = value

                with TESTS_WRITE_LOCK:
                    TESTS[reference] = {}
                    TESTS[reference]["test_class"] = None
                    TESTS[reference]["interrupted"] = False
                try:
                    test_class = None
                    exec("import %s" % package)
                    exec("test_class = %s.%s()" % (package, clazz))
                    with TESTS_WRITE_LOCK:
                        TESTS[reference]["test_class"] = test_class
                        test_class.configure(config)
                except Exception as e:

                    printException(e)
                    status = False
                #self.wfile.write(json.dumps({"action":"CONFIGURED_TEST", "reference":reference, "status":status}))
                message_to_master({"action":"CONFIGURED_TEST", "reference":reference, "status":status,"port":port2})

            elif data['action'] == "PREPARE_TEST":
                #print "PREPARE_TEST"
                status = True
                reference = data["reference"]
                try:
                    test_class = TESTS[reference]["test_class"]
                    test_class.setUp()
                except Exception as e:
                    printException(e)
                    status = False
                message_to_master({"action":"PREPARED_TEST", "reference":reference, "status":status,"port":port2})
                #self.wfile.write(json.dumps({"action":"FINISHED_TEST", "reference":reference, "status":status}))

            elif data['action'] == "RUN_TEST":
                #print "RUN_TEST"
                status = True
                reference = data["reference"]

                try:
                    test_class = TESTS[reference]["test_class"]
                    test_class.runTest()
                except Exception as e:
                    #printException(e)
                    status = False
                message_to_master({"action":"FINISHED_TEST", "reference":reference, "status":status,"port":port2})
                #self.wfile.write(json.dumps({"action":"FINISHED_TEST", "reference":reference, "status":status}))

            elif data['action'] == "RUN_METHOD":
                #print "RUN_METHOD"
                status = True
                reference = data["reference"]
                method_reference = data["method_reference"]

                #print method
                try:
                    test_class = TESTS[reference]["test_class"]
                    method = data["method"]
                    exec("test_class.%s()" % method)
                except Exception as e:
                    #printException(e)
                    status = False
                message_to_master({"action":"FINISHED_METHOD", "reference":reference, "method_reference":method_reference, "status":status,"port":port2})
                #self.wfile.write(json.dumps({"action":"FINISHED_METHOD", "reference":reference, "method_reference":method_reference, "status":status}))

            elif data['action'] == "GET_RESULTS":
                #print "GET_RESULTS"
                status = True
                reference = data["reference"]

                try:
                    test_class = TESTS[reference]["test_class"]
                    result = test_class.getResult()
                except Exception as e:
                    printException(e)
                    status = False
                    result = {}
                message_to_master({"action":"FINISHED_RESULTS", "reference":reference, "result":result, "status":status,"port":port2})
                #self.wfile.write(json.dumps({"action":"FINISHED_RESULTS", "reference":reference, "result":result, "status":status}))

            elif data['action'] == "INTERRUPT_TEST":
                #print "INTERRUPT_TEST"
                #status = True
                reference = data["reference"]
                with TESTS_WRITE_LOCK:
                    TESTS[reference]["interrupted"] = True
                try:
                    test_class = TESTS[reference]["test_class"]
                    test_class.interrupt()
                except Exception as e:
                    printException(e)
                    #status = False
            elif data['action'] == "CLEANUP_TEST":
                #print "CLEANUP_TEST"
                status = True
                reference = data["reference"]
                try:
                    test_class = TESTS[reference]["test_class"]
                    test_class.tearDown()
                    del test_class
                except Exception as e:
                    printException(e)
                    status = False
                message_to_master({"action":"CLEANEDUP_TEST", "reference":reference, "status":status,"port":port2})
                #self.wfile.write(json.dumps({"action":"CLEANEDUP_TEST", "reference":reference, "status":status}))
                #print "finish"




class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):

    pass

def message_to_master(message):


    message["token"] = TOKEN
    message_string = json.dumps(message,ensure_ascii=False)
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    sock.connect((master_host,master_port))
    #sock.setblocking(0)
    sock.sendall(message_string)
    sock.close()
    sock = None
    #server.socket.sendto(message_string, (master_host, master_port))



def printException(e):
    print 40 * "-"
    print "Exception occured on client %s:" % HOSTNAME
    traceback.print_exc(file=sys.stdout)
    print 40 * "-"

class AbstractCheck():
    def __init__(self):
        self.interrupted = False

    def configure(self, args):
        raise NotImplementedError

    @staticmethod
    def getClientSpecificConfig(clients, config):
        return None

    #def setUpMaster(self):
    #    raise NotImplementedError

    def setUp(self):
        raise NotImplementedError

    #def runTest(self):
    #    raise NotImplementedError

    def interrupt(self):
        self.interrupted = True

    def getResult(self):
        raise NotImplementedError

    def tearDown(self):
        raise NotImplementedError

    #def tearDownMaster(self):
    #    raise NotImplementedError


if __name__ == "__main__":


    try:
        opts, args = getopt.getopt(sys.argv[1:], "m:t:", ["master=", "token="])
    except getopt.GetoptError, err:
        print str(err)

    for o, a in opts:
        if o in ("-m", "--master"):
            master_host, master_port = a.split(":")
            master_port = int(master_port)
        if o in ("-t", "--token"):
            TOKEN = a

    if master_host is None or master_port is None:
        print "Set master host:port! (option --master / -m)"
        sys.exit()

    if TOKEN is None:
        print "Set token! (option --token / -t)"
        sys.exit()

    server = ThreadedTCPServer(("0.0.0.0", 0), ThreadedTCPRequestHandler)
    ip, port2 = server.server_address
    server.allow_reuse_address = True




    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    #server_thread.setDaemon(True)
    # Exit the server thread when the main thread terminates
    server_thread.start()


    #server.socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    #server_thread.socket.connect((master_host,master_port))
    #server_thread.socket.setblocking(0)
    #print "Server loop running"
    #print master_host, master_port



    message_to_master({"action":"ALIVE","port":port2})
    #server.shutdown()
