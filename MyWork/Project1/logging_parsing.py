import optparse
import os
import sys
import re
import logging


def init(applicationResourceFile,loggerName):


    usage = 'usage: %prog [[-a] [-k] [-o] -d] [-h]'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-a', action='store_true', default=False,
                      help='This option will result in the application of both OS and Kernel security patches.')
    parser.add_option('-d', action='store_true', default=False,
                  help='This option is used when problems are encountered and additional debug information is needed.')
    parser.add_option('-k', action='store_true', default=False,
                  help='This option will result in the application of Kernel security patches.')
    parser.add_option('-o', action='store_true', default=False,
                  help='This option will result in the application of OS security patches.')
    parser.add_option( '-p', action='store_true', default=False,
                       help='This option is used to perform the post update tasks.' )
    parser.add_option( '-v', action='store_true', default=False,
                       help="This option is used to display the application's version." )
    (options, args) = parser.parse_args()
    applicationName = os.path.basename( sys.argv[0] )
    applicationVersion = 'v1.8-6'
    if options.v:
        print(applicationName + ' ' + applicationVersion)
        exit( 0 )
    if options.a and options.k or options.a and options.o or options.k and options.o or options.a and options.p or options.o and options.p or options.k and options.p:
        parser.error( 'Options -a, -k, -o and -p are mutually exclusive.' )
    if not options.a and not options.k and not options.o and not options.p:
        parser.error( "Try '" + applicationName + " -h' to get command specific help." )
    if options.p:
        print('Phase 1: Initializing for the post system update.')
    else:
        print('Phase 1: Initializing for the system update.')
    patchResourceDict = {}
    patchResourceDict['options'] = options

    try:
        with open(applicationResourceFile) as f:
            for line in f:
                line = line.strip()
                line = re.sub('[\'"]','', line)
                if len(line) == 0  or re.match('^\\s*#', line) or re.match('^\\s+$',line):
                    continue
                else:
                    key, val = line.split('=')
                    key = key.strip()
                    patchResourceDict[key] = val.strip()


    except IOError as err:
        print("Unable to access the application's resource file " + applicationResourceFile + '.\n' + str(err) + '\n')
        exit(1)

    try:
        logBaseDir = re.sub('\\s+', '', patchResourceDict['logBaseDir']).rstrip('/')
        patchApplicationLog = re.sub('\\s+', '', patchResourceDict['patchApplicationLog'])
        patchApplicationLog = logBaseDir + '/' + patchApplicationLog
        print(patchApplicationLog)

    except KeyError as err:
        print('The resource key (' + str(err) + ') was not present in the resource file; exiting program execution.' + '\n')
        exit(1)

    if not options.p:
        try:
            logList = os.listdir( logBaseDir )
            for log in logList:
                print(log)
                os.remove( logBaseDir + '/' + log )


        except OSError as err:
            print('Unable to remove old logs in ' + logBaseDir + '; exiting program execution.\n' + str(err) + '\n')
    handler = logging.FileHandler(patchApplicationLog)
    logger = logging.getLogger(loggerName)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s',datefmt='%m/%b/%Y %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)

    # IF -p option is called below option will work.
    if options.p:
        return patchResourceDict
    logger.info( applicationName + ' ' + applicationVersion )

    # Below option will work only if -a option is called
    try:
        if len( patchResourceDict['rpmsToRemove'] ) != 0:
            print("We need to remove some of the RPM files")
            patchResourceDict['removeRPMs'] = True
        else:
            patchResourceDict['removeRPMs'] = False
        if len( patchResourceDict['rpmsToAdd'] ) != 0:
            patchResourceDict['addRPMs'] = True
            print( "We need to ADD some of the RPM files" )
        else:
            patchResourceDict['addRPMs'] = False
    except KeyError as err:
        logger.error( 'The resource key (' + str( err ) + ') was not present in the resource file.' )
        print('A resource key was not present in the resource file, check the log file for errors; exiting program execution.' + '\n' )
        exit( 1 )


# def callPatchdir(patchResourceDict):
#     print(patchResourceDict)

def main():

    applicationResourceFile = r"C:\Users\kristhim\Desktop\patchResourceFile"
    loggerName = 'patchLogger'
    patchResourceDict = init(applicationResourceFile, loggerName)

    if patchResourceDict:
        print("Patch resource is called in main program after -P option")
        for key in patchResourceDict:
            print( "Key ->" + str( key ) + " Value ->" + str( patchResourceDict[key] ) )
    # statusValue = callPatchdir(patchResourceDict.copy())
    # print(statusValue)
main()





