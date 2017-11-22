import pickle
import json

class userRegistration:
    """    """

    def __init__(self,path):
        self.userData = {}
        self.path = path
        self.userDataList = []


    def new_User_Registration(self):

        datadic = {}

        userid = input("Enter User ID should be your email ID :")
        uname =input("Enter user Name :")
        password = input("Enter password min 8 character :")
        address = input("Enter your Address :")
        phone = input("Enter your phone number :")

        datadic["password"]=password
        datadic["name"]=uname
        datadic["password"]=password
        datadic["address"]=address
        datadic["phone"]=phone


        self.userDataList.append(datadic)
        self.userData[userid] = self.userDataList


        # Append data in the existing Userdata file
        with open(self.path,'a') as userFile:
            json.dump(self.userData,userFile)
        # with open(self.path,'ab') as userFile:
        #     userFile.write(self.userData)
        #     #pickle.dump(self.userData,userFile)
        #     #f.write(data)

        #return self.userData

    def getValue(self):

        with open(self.path) as json_file:
            self.userData = json.load(json_file)
            return self.userData
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
