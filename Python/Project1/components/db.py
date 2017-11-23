import mysql.connector

conn=mysql.connector.connect(user='root',password='tiger',host='localhost',database='test')
mycursor=conn.cursor()
mycursor.execute("show tables")
print(mycursor.fetchall())
mycursor.execute("show variables like '%version%'")
print(mycursor.fetchall())



##>>> import json
##>>> json_data = '{"first_name":"Thimma","last_name":"Rayan"}'
##>>> obj = json.loads(json_data)
##>>> print(obj)
##{'last_name': 'Rayan', 'first_name': 'Thimma'}
##>>> type(obj)
##<class 'dict'>
##>>> print(obj["last_name"])
##Rayan
##>>> js_d = '{"colors":["red","blue","white"]}'
##>>> obj = json.loads(js_d)
##>>> print(obj)
##{'colors': ['red', 'blue', 'white']}
##>>> print(obj[colors])
##Traceback (most recent call last):
##  File "<stdin>", line 1, in <module>
##NameError: name 'colors' is not defined
##>>> print(obj["colors"])
##['red', 'blue', 'white']
##>>>

##>>> for color in obj["colors"]:
##...     print(color)
##...
##red
##blue
##white
##>>>
##
##>>> for color in obj["colors"]:
##...     print(color)
##...
##red
##blue
##white
##>>>
##
##python to json 
##
##>>> py_dic = {"phil":"flyers","Tamp":"light"}
##>>> json_data = json.dumps(py_dic)
##>>> print(json_data)
##{"phil": "flyers", "Tamp": "light"}
##>>> print(type(json_data))
##<class 'str'>
##
##json file in python 
##
##import json 
##with open('test.json') as data:
##	json_data = json.load(data)
##	
##print(json_data["glossary"]["title"])
##
##
##
##>>> import json
##>>> data = {"phil":"Flyers", "Tampa":"light"}
##>>> with open('test.json','w') as f:
##...     json.dump(data,f)
##...
##>>> with open('test.json') as f:
##...     json_data = json.load(f)
##...
##>>> print(json_data)
##{'phil': 'Flyers', 'Tampa': 'light'}
