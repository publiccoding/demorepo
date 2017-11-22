
from module import test2



class UserDetail:


    def showUser(self):
        print("under showuser")
        conn=test2.startDB()
        print(type(conn))
        print( "after  showuser" )
        data1=input("Enter the user Name you want to search")
        found=input("Enter the value to be searched")
        datastring=conn.execute("SELECT id,name from bank_userData where name=?",(data1,))

        if found in datastring.__next__():
            print("found Data")
        #print(type(datastring.__next__()))
        #print(str(datastring.__next__()))
        # for row in datastring:
        #     print( "ID = ", row[0] )
        #     print( "NAME = ", row[1] )
        #     print( "ADDRESS = ", row[2] )
        #     print( "PHONE = ", row[3], "\n" )
        print( "Operation done successfully" )

        test2.connClose()

d = UserDetail()
d.showUser()


#
# import pickle
#
# path =r"C:\Users\kristhim\Desktop\thimma 01302017\programming\Practice\demorepo\Python\BankApplication\module\UserData.txt"
#
# import json
#
# # data = {}
# # data['rayan@gmail.com'] = []
# # data['rayan@gmail.com'].append({
# #     'name': 'Scott',
# #     'website': 'stackabuse.com',
# #     'from': 'Nebraska'
# # })
# #
# # data['thimma@gmail.com'] = []
# # data['thimma@gmail.com'].append({
# #     'name': 'Larry',
# #     'website': 'google.com',
# #     'from': 'Michigan'
# # })
# # data['krish@gmail.com'] = []
# # data['krish@gmail.com'].append({
# #     'name': 'Tim',
# #     'website': 'apple.com',
# #     'from': 'Alabama'
# # })
# #
# # with open(path, 'w') as outfile:
# #     json.dump(data, outfile)
#
#
#         datadic = {}
#
#         userid = input("Enter User ID should be your email ID :")
#         uname =input("Enter user Name :")
#         password = input("Enter password min 8 character :")
#         address = input("Enter your Address :")
#         phone = input("Enter your phone number :")
#
#         datadic["password"]=password
#         datadic["name"]=uname
#         datadic["password"]=password
#         datadic["address"]=address
#         datadic["phone"]=phone
#
#
#         self.userDataList.append(datadic)
#         self.userData[userid] = self.userDataList
#
#
#
# with open(path) as json_file:
#     data = json.load(json_file)
#     for line in data:
#         print(data[line])
#         print(type(data[line]))
#     #print(data)
#
#
#
#
