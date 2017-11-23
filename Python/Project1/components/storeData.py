#!/usr/bin/python


import subprocess


def saveData():
	systemLoginDataList = ['10.41.0.4|TT?bTTTT|root', '10.41.0.33|x3$%W1212l|root', '10.41.0.9|HP1nv3nt|admin']

	systemLoginData = ' '.join(systemLoginDataList)

	cmd = "/tmp/csurTest/transform3 'x45lw#j6.W' read '/tmp/csurTest/dataFile'"
	#cmd = "/tmp/csurTest/transform3 'x45lw#j6.W' write '/tmp/csurTest/dataFile' '" + systemLoginData + "'"

	result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	result = out.strip('# \n')
	print("The results are: " + result)

	resultList = result.split(' ')

	resultDict = {}

	for result in resultList:
		tmpList = result.split('|', 1)
		resultDict[tmpList[0]] = tmpList[1].rsplit('|', 1)

	print(resultDict)

saveData()
