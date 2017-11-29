import pickle
import json
import ast
import re
import random
class userRegistration:
    """    """

    def __init__(self,path):
        self.userData = {}
        self.path = path
        self.userDataList = []

    def new_User_Registration(self):
        print(self.path)
        datadic = {}

        userid = input("Enter User ID :")
        uname =input("Enter user Name :")
        password = input("Enter password min 8 character :")
        address = input("Enter your Address :")
        phone = input("Enter your phone number :")
        email = input("Enter your Email ID :")
        accountno = self.accountNumber()
        min_balance = int(input("Enter min Balance amount should be 1000 and above"))
        if min_balance < 1000:
            print("Minimum Balance should be greater than 1000")
        elif userid in self.getValue(): # logic missing
            print("User already exist")
        else:
            datadic["name"]=uname
            datadic["password"]=password
            datadic["address"]=address
            datadic["phone"]=phone
            datadic["email"]=email
            datadic["accountno"]= accountno
            datadic["balance"] = min_balance

            #self.userDataList.append(datadic)
            self.userData[userid] = datadic


        # Append data in the existing Userdata file
        try :
            with open (self.path, "a" ) as test_db:
                test_db.write(str(self.userData))
                test_db.write('\n')
        except IOError:
            print("Unable to upload the data")
    def accountNumber(self):
        
        acc_no = (x for x in range(1000,9999))
        return acc_no.__next__()
    
    def getValue(self):
        with open(self.path, "r") as read_db:
            for line in read_db:
                line = ast.literal_eval (line)
        return line






















                            # with open(self.path,'ab') as userFile:
                            #     userFile.write(self.userData)
                            #     #pickle.dump(self.userData,userFile)
                            #     #f.write(data)

                            # return self.userData




                            # with open(self.path) as json_file:
        #     self.userData = json.load(json_file)
        #     return self.userData
            # for line in data:
            #     print( data[line] )
            #     print( type( data[line] ) )

        # with open(self.path,'rb') as userFile:
        #     for line in userFile.readline():
        #         self.userData = line


               # self.userData = pickle.load(line)
            #self.userData=f.read()
        # print(self.userData)


# if __name__ == "__main__":
#
#     a = userRegistration()
#
#     value = a.new_User_Registration()
#     print(value)

 # def new_User_Registration(self):
 #
 #        self.userData = {"thimma@gmail.com": {'Name': 'Thimmarayan', 'password': 'Lakrthkuv@1'}}
 #        uname = input("Enter username :")
 #        count = 1
 #        while uname in self.userData and count < 3:
 #            uname = input("Enter another valid username")
 #            count +=1
 #            continue
 #
 #        if uname not in self.userData:
 #            return self.userData
 #
 #        else:
 #            return self.userData
 #
