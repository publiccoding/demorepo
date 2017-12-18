# 1. Local and global variable 
# 2. JSON OPERATION
# 3. FILE OPERATION 

# x = 'x global'
# def variable_scope():
#     global x 
#     x = 'x local'
#     print(x)

# variable_scope()
# print(x)

# for i in [1,2,3,4,5,6]:
#     print(i)


# people_string = '''
# {
#     "people":[
#         {
#             "name":"johne",
#             "phone":"6242323902304324",
#             "emails":["johnsim@gmail.com","john@gmail.com"],
#             "real":73423.89,
#             "intvalue":598343

#         },  
#         {
#             "name":"badler",
#             "phone":"6242323902304324",
#             "emails":["badler@gmail.com","bad@gmail.com"],
#             "license":true,
#             "data": null
#         }
#     ]
# }
# '''

# JSON DUMPS and LOADS to convert String 
# import json 

# data = json.loads(people_string)
# print(data)
# for item in data["people"]:
#     del item["phone"]
# new_data = json.dumps(data, indent=2)
# print(new_data)

# import json 

# with open("test.json",'r') as f:
#     json_data = json.load(f)

# #print(json_data)

# for data in json_data["people"]:
#     del data["phone"]
# #print(json_data)

# with open("test1.json",'w') as fp:
#     json.dump(json_data,fp, indent=2)

# Using url open to download file 

# import json 
# from urllib.request import urlopen

# with urlopen("https://docs.python.org/3.6/library/json.html?highlight=json#module-json") as file:
#     source = file.read()

# with open("urltest.json",'w') as fp:
#     fp.write(str(source))



# f = open('data.txt', 'r')
# print(f.name)
# print(f.mode)
# f.close

# with open('data.txt','r') as file:
#     data = file.readlines().split()
    

# print(data)