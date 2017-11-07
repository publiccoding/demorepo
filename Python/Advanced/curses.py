
import re
# csur_data = {"thimmarayan" : { "fname":"krishnappa" ,"mname": "Lakshmamma"}, "kumar":{"fname":"krishnappa" ,"mname": "Lakshmamma"}}
# csur_list = {"thimmarayan" : ["krishnappa" ,"Lakshmamma"], "kumar":["krishnappa" ,"Lakshmamma"]}
# print(csur_list["kumar"][0])

# #def getFirmwareDict():
# started = False
# firmwareList = []
# firmwareDict = {}
# f = open("C:\\Users\\kristhim\\Desktop\\thimma 01302017\\programming\\python\\csur modules\\computeNodeResourceFile", "r")
# computeNodeResource = f.read()
# #print(computeNodeResource)
# for data in computeNodeResource:
#     #print(data)
#     data = data.replace(' ','')
#     print(data)
#     if not re.match('Firmware.*', data) and not started:
#         continue
#     elif re.match('Firmware.*', data):
#         started = True
#         continue
#     elif re.match(r'\s*$', data):
#         #print(data)
#         break
#     else:
#         firmwareList = data.split('|')
#         print(firmwareList)
#         firmwareDict[firmwareList[0]] = [firmwareList[1], firmwareList[2]]
#         print(firmwareDict)


started = False
firmwareList = []
firmwareDict = {}

with open("C:\\Users\\kristhim\\Desktop\\thimma 01302017\\programming\\python\\csur modules\\computeNodeResourceFile") as f:
    content = f.readlines()
    content = [x.strip() for x in content]
    #print(content)

    for data in content:
        data = data.replace(' ','')
        #print(data)
        if not re.match('Firmware.*', data) and not started:
            continue
        elif re.match('Firmware.*', data):
            started = True
            continue
        elif re.match(r'\s*$', data):
            break
        else:
            firmwareList = data.split('|')
            #print(firmwareList)
            firmwareDict[firmwareList[0]] = [firmwareList[1], firmwareList[2]]
#print(firmwareDict)

count = 0
for key, value in firmwareDict.items():
    print ("Key :"+str(key)+"value :"+str(value))
    #print("\n")
    count = count +1
print(count)







