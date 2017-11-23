#!/usr/bin/python

import binascii
import subprocess
import optparse


def init():

	referenceDict = {'eth3': 'e8:39:35:bf:f5:b7', 'eth2': 'e8:39:35:bf:f5:b6'}

	for var in referenceDict:
		command = "ip addr list " + var + "|grep " + referenceDict[var]
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		try:
			if result.returncode  != 0:
				raise NotImplementedError()
		except NotImplementedError:
			print "NotImplementedError Bye"
			exit(1)

	usage = 'usage: %prog [-f CSUR_FILENAME]'

        parser = optparse.OptionParser(usage=usage)

        parser.add_option('-f', action='store', help='This option is mandatory and requires its argument to be the Gap Analysis data file.', metavar='FILENAME')

        (options, args) = parser.parse_args()

        if not options.f:
                parser.print_help()
                exit(1)
        else:
                dataFile = options.f

	return dataFile
#End init()


def transformDataFile(dataFile):
	gapAnalysisResultsFile = "gapAnalysisResults.txt"

	try:
		fh = open(dataFile)
		binaryData = fh.read()
	except IOError:
		print "Unable to open " + dataFile + " for reading.\n"
		exit(1)

        gapAnalysisData = binascii.unhexlify(binaryData.strip())

        lowerAlphaDict = {'z': 'a', 'q': 'h', 'm': 'e', 'j': 't', 'x': 'c'}
        upperAlphaDict = {'P': 'A', 'W': 'H', 'B': 'E', 'Q': 'T', 'J': 'C'}
        numDict = {'4': '7', '5': '2', '3': '9', '8': '4', '6': '0'}

        for charKey in lowerAlphaDict:
                gapAnalysisData.replace(charKey, lowerAlphaDict[charKey])

        for charKey in upperAlphaDict:
                gapAnalysisData.replace(charKey, upperAlphaDict[charKey])

        for charKey in numDict:
                gapAnalysisData.replace(charKey, numDict[charKey])

	try:
		fh = open(gapAnalysisResultsFile, 'w')
		fh.write(gapAnalysisData)
		fh.close()
	except IOError:
                print "Unable to open " + gapAnalysisResultsFile + " for writing.\n"
                exit(1)
#End writeGapAnalysisData(data)


dataFile = init()

transformDataFile(dataFile)
