import json
import urllib.request
import csv
import requests
import urllib.parse


''' In this example i am going to work on json data
 in python script how to store python object into json format and display content'''

# In json every key must be string.

# q = []
#
# q.append({"fname":"Thimmarayan","lname":"Krishnappa"})

#
# print(json.dumps(q, indent=4))

# in this example how to store json data in file using python utility

# fout = open(r"C:\Users\kristhim\Desktop\thimma 01302017\programming\Practice\demorepo\Json\test1.json",'w')
# json.dump(q,fout,indent=4)
# fout.close()

# In this example i am goind to retrive json data  using python utility

# fin = open("C:\\Users\\kristhim\\PycharmProjects\\Programming\\Json\\test1.json", 'r')
# jsonobj = json.load(fin)
# print(type(jsonobj))
# fin.close()

#print(jsonobj)

# url ="//earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_month.geojson"
# response = urllib.request.urlopen(url)
# content = response.read()
# data = json.load(content.decode("utf8"))
# print(data)
#
# file = "C:\\Users\\kristhim\\PycharmProjects\\Programming\\Json\\data.json"
# sourceFile = open(file, 'rU')
# json_data = json.load(sourceFile)
# print(json_data["executionTime"])
#
# # outputFile = open("convert.csv","w")
# # outputWriter = csv.writer(outputFile)
#
# for station in json_data["stationBeanList"]:
#     row_array = []
#     row_array.append(json_data["executionTime"])
#     for attribute in station:
#         row_array.append(station[attribute])
#     print(row_array)
#
#     #outputWriter.writerow(row_array)
#
# sourceFile.close()
# #outputFile.close()
#
# api="http://maps.googleapis.com/maps/api/geocode/json?"
#
#
# while True:
#     address = input("Enter the address: ")
#     if address == 'quit' or address == 'q':
#         break
#
#     url = api + urllib.parse.urlencode({'address':address})
#     print(url)
#     json_data = requests.get(url).json()
#     json_status = json_data['status']
#     print('API Status'+ json_status)
#
#
#     if json_status == 'OK':
#         for each in json_data['results'][0]['address_components']:
#             print(each['long_name'])
#             # fmt_address = json_data['results'][0]['formatted_address']
#             # print()
#             # print(fmt_address)

fin = open(r"C:\Users\kristhim\Desktop\thimma 01302017\programming\Practice\demorepo\Json\test2.json", 'r')
jsonobj = json.load(fin)
print (type(jsonobj))


#print(jsonobj["problems"][0])

for each in jsonobj["problems"]:
    for value in each["Diabetes"]:
        for item in value["medications"]:
            for type in item["medicationsClasses"]:
                for menu in type["className"]:
                    print(menu["associatedDrug#2"][0]["name"])
                    #print(type)

# for each in jsonobj["items"]["item"]:
#     for value in each["batters"]["batter"]:
#         print(value['type'])
#         #print(value)
#     for value in each["topping"]:
#         print(value)
#

# for each in jsonobj:
#     print("ID : "+each["id"])
#     print("Type: "+each["type"])
#     print("Name: "+each["name"])
#     print("PPU: "+str(each["ppu"]))
#     for item in each["batters"]["batter"]:
#         print(item["type"])
#     for item in each["topping"]:
#         print(item["type"])

#print(jsonobj)
#print("\n\n")
#value = []

print()

# for each in jsonobj[0]:
#     print(each)


# for i in jsonobj["batters"]["batter"]:
#     print("value is "+i["id"]+" and Type is "+i["type"])
#
# for i in jsonobj["topping"]:
#     print(i["id"])

#print(jsonobj["batters"]["batter"][1])

#print(jsonobj["data"]["current_condition"])
# for each in jsonobj["data"]["current_condition"][0]:
#     print(each["winddir16Point"])

# for children in jsonobj["children"]:
#     print("loop1")
#     print(type(children))
#     print(children)
#     for grandchildren in children["children"]:
#         print("loop2")
#         print(type(grandchildren))
#         print(grandchildren)
#         for greatgrand in grandchildren["children"]:
#             print("loop3")
#             print(type(greatgrand))
#             print(greatgrand)
#             print(greatgrand["Ids"])
#             print()
#             print(greatgrand["id"])
#             print()
#             print(greatgrand["name"])
#             print()
#             if greatgrand["name"] == "BoxDet":
#                 print("BoxDet" + " ".join(greatgrand["Ids"]))
#


fin.close()


#
# for k, v in jsonobj.items():
#     if "name" in k:
#         value.append(v)
#         for i in v:
#             print(i)


# if "children" in v:
#     for i in v:
#         if "children" in i:
#             for j in i:
#                 print(j)













































