import json 
from module.userRegistration import userRegistration

def main():

    """ This module is used for login user else direct to New user registration"""

path = r"C:\Users\kristhim\Desktop\thimma 01302017\programming\Practice\demorepo\Python\BankApplication\module\UserData.txt"

def userRegister():
    data = input( "Do you want to Register (y|n)" )
    if data == "y":
        userRegistration( path ).new_User_Registration()
        print("User registered successfully")
        exit()
    elif data == "n":
        print( "Thanks for visiting " )
        exit()
    else:
        print( "select correct option (y|n)" )
        exit()

def userLogin(userdata):
    if username in userdata.keys():
        user_pwd = input("Enter password :")
        for pwd in userdata.values():
            if pwd['pwd'] == user_pwd:

    # if username in userdata:
    #     pwd = userdata[username][0]["password"]
    #     userpwd = input( "Enter your password" )
    #     count = 1
    #     while userpwd.strip() != pwd and count < 3:
    #         userpwd = input( "Enter your password" )
    #         count += 1
    #         continue
    #     else:
    #         print( " You are successfully logged in" )
    #         exit()
    else:
        userRegister()

        if username in line.keys ():
            pwd = input ( "Enter Password" )
            for d in line.values ():
                if d['pwd'] == pwd:
                    print ( "Your Logged in successfully" )

username = input( "Enter username " )
try:
    userdata = userRegistration(path).getValue()
    print(userdata)
    userLogin(userdata)

except JSONDecodeError:
    userRegister()
    # print( userdata )
    # print( type( userdata ) )

if __name__ == "__main__":
    main()




