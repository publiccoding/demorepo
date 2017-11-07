import re



resource ="C:\\Users\\kristhim\\Desktop\\thimma 01302017\\programming\\python\\csur modules\\computeNodeResourceFile"

try:
    with open(resource) as f:
        res = f.read().splitlines()
except IOError as err:
    errors = True
    #print("Unable to open the "+ resource + "for reading.\n" + str(err))


firmwareList = []
firmwareDict = {}
componentUpdateDict = {'Firmware' : {}, 'Drivers' : {}, 'Software' : {}}
nicCardModels = []
updateDriverList = []
started = False
# for data in res:
#     #Remove spaces if any are present.
#     data = data.replace(' ', '')
#     if not re.match('Firmware.*', data) and not started:
#         continue
#
#     elif re.match('Firmware.*', data):
#         started = True
#         continue
#     elif re.match(r'\s*$', data):
#         break
#     else:
#         firmwareList = data.split('|')
#         #print(firmwareList)
#         firmwareDict[firmwareList[0]] = [firmwareList[1], firmwareList[2]]
#
# count = 0
# for key, value in firmwareDict.items():
#     #print("Key :" + str(key) + "value :" + str(value))
#     #print("\n")
#     count = count + 1
# #print(count)
#
# #print(firmwareList)
# #print(firmwareDict)

#-----------------------------------------------------------------------------
# started = False
# driversFound = False
# updateDriverList = []
# mlnxCount = 0
# csurDriverList = []
#
# for data in res:
#     data = data.replace(' ','')
#     #print(data)
#     if not 'Drivers' in data and not driversFound:
#         continue
#     elif 'Drivers' in data:
#         driversFound = True
#         continue
#     elif not (('SLES11.4' in data) and ('DL580Gen9' in data )) and not started:
#         continue
#     elif (('SLES11.4' in data ) and ('DL580Gen9' in data)):
#         started = True
#         continue
#     elif re.match(r'\s*$', data):
#         break
#     else:
#         csurDriverList = data.split('|')
#         #print(csurDriverList)
#         csurDriver = csurDriverList[0]
#         #print(csurDriver)
#         csurDriverVersion = csurDriverList[1]
#         #print(csurDriverVersion)
#         #print(csurDriverList[2])


#--------------------------------------------------------------------------------

started = False
softwareFound = False
updateSoftwareList = []
#csurSoftwareList = []

for data in res:
    data = data.replace(' ','')
    #print(data)
    if not 'Software' in data and not softwareFound:
        continue
    elif 'Software' in data:
        softwareFound = True
        continue
    elif not (('SLES11.4' in data) and ('DL580Gen9' in data )) and not started:
        continue
    elif (('SLES11.4' in data ) and ('DL580Gen9' in data)):
        started = True
        continue
    elif re.match(r'\s*$', data):
        break
    else:
        csurSoftwareList = data.split('|')
        csurSoftware = csurSoftwareList[0]
        csurSoftwareEpoch = csurSoftwareList[1]
        csurSoftwareVersion = csurSoftwareList[2]
        csurSoftwareRpm = csurSoftwareList[3]
        print(csurSoftwareRpm)

#-----------------------------------------------------------------------------------------------
componentHeader = 'Component'
componentUnderLine = '---------'
csurVersionHeader = 'CSUR Version'
csurVersionUnderLine = '------------'
currentVersionHeader = 'Current Version'
currentVersionUnderLine = '---------------'
statusHeader = 'Status'
statusUnderLine = '------'
# print('{0:40}'.format('Firmware Versions:') + '\n')
# print('{0:40} {1:25} {2:25} {3}'.format(componentHeader, csurVersionHeader, currentVersionHeader, statusHeader))
# print('{0:25}'.format(componentHeader,csurVersionHeader))

# command ="Smart Array P431 in Slot 2    (sn: PCZED0ARH8L03C) \n" \
#          "Smart Array P830i in Slot 0   (sn: 0014380292CE340)"
#
# #print(command)
#
# controllerList = re.findall('P\d{3}i*\s+in\s+Slot\s+\d{1}',command)
#
# for control in controllerList:
#     print(control)
#     controlModel = control.split()[0]
#     controllerSlot = control.split()[-1]
#     #print(controlModel+" "+controllerSlot)
#     csurControllerFirmwareVersion = firmwareDict[controlModel][0]
#     csurControllerFirmwareRpm = firmwareDict[controlModel][1]
#     #print(csurControllerFirmwareVersion+"  "+csurControllerFirmwareRpm)
#     #print(controllerSlot)
#     #print(controlModel[0]+"and the slot value is "+controlModel[3])
#
#     componentUpdateDict['Firmware'][controlModel] = firmwareDict[controlModel][1]
#     print(componentUpdateDict['Firmware'][controlModel])
#     csurEnclosureFirmwareVersion27 = firmwareDict['D2700'][1]
#     csurEnclosureFirmwareVersion37 = firmwareDict['D3700'][1]
#     print(csurEnclosureFirmwareVersion27)
#     print(csurEnclosureFirmwareVersion37)
#
