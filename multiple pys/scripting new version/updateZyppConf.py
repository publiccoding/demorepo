#!/usr/bin/python

import spUtils
import subprocess
import logging
import tempfile


'''
This function is used to update /etc/zypp/zypp.conf so that two kernels will be maintained. The 
new kernel and the previous kernel. 
The function returns True on success and False on a failure, at which time the log
should be consulted.
'''
def updateZyppConf(logFile):

	result = True

	logger = logging.getLogger("securityPatchLogger")
	logger.info('Updating /etc/zypp/zypp.conf.')

	script = '''
		zyppConf='/etc/zypp/zypp.conf'

		cp $zyppConf "${zyppConf}.ORIG"

		if [[ $? != 0 ]]; then
			exit 1
		fi

		line=''

		#Update the multiversion variable differently based on whether or not it is commented out already.
		if [[ ! `egrep "^\s*multiversion\s*=\s*" ${zyppConf}` ]]; then
			sed -i '0,/^\s*#\+\s*multiversion\s*=\s*.*$/s//multiversion = provides:multiversion(kernel)/' $zyppConf
		else
			sed -i '0,/^\s*multiversion\s*=\s*.*$/s//multiversion = provides:multiversion(kernel)/' $zyppConf
		fi

		if [[ $? != 0 ]]; then
			exit 1
		fi

		#Update the multiversion.kernels variable differently based on whether or not it is commented out already.
		if [[ ! `egrep "^\s*multiversion.kernels\s*=\s*" ${zyppConf}` ]]; then
			sed -i '0,/^\s*#\+\s*multiversion.kernels\s*=\s*.*$/s//multiversion.kernels = latest,latest-1,running/' $zyppConf
		else
			sed -i '0,/^\s*multiversion.kernels\s*=\s*.*$/s//multiversion.kernels = latest,latest-1,running/' $zyppConf
		fi

		if [[ $? != 0 ]]; then
			exit 1
		else
			exit 0
		fi
	'''	

        try:
                fh = open(logFile, 'a')

                with tempfile.NamedTemporaryFile() as updateZyppConfScript:
                        updateZyppConfScript.write(script)
                        updateZyppConfScript.flush()
                	returnCode = subprocess.call(['/bin/bash', updateZyppConfScript.name], stdout=fh)

		if returnCode != 0:
			result = False

                fh.close()
        except OSError as e:
                logger.error('Errors were encountered while writing to ' + logFile + ':Error' + repr(e))
		result = False
        except Exception as e:
                logger.error('Errors were encountered while writing to ' + logFile + ':Error' + repr(e))
		result = False
        finally:
                try:
                        logFile.close()
                except:
                        pass

	logger.info('Done updating /etc/zypp/zypp.conf.')
	return result
#End def updateZyppConf(logFile):


#This section is for running the module standalone for debugging purposes.
if __name__ == '__main__':

	#Setup logging.
	logger = logging.getLogger()
	logFile = '/tmp/updateZyppConf.log'
	zyppConfScriptLogFile = '/tmp/updateZyppConfScript.log'
	zyppConf = '/etc/zypp/zypp.conf'

        try:
                open(logFile, 'w').close()
        except IOError:
                print spUtils.RED + "Unable to access " + logFile + " for writing." + spUtils.RESETCOLORS
                exit(1)

        handler = logging.FileHandler(logFile)

	logger.setLevel(logging.INFO)
	handler.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

	if updateZyppConf(zyppConfScriptLogFile):
                print spUtils.GREEN + "Successfully updated " + zyppConf + spUtils.RESETCOLORS
	else:
                print spUtils.RED + "Unable to update " + zyppConf + "; check log files " + zyppConfScriptLogFile + " and " + logFile + " for errors." + spUtils.RESETCOLORS
