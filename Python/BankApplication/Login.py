
#This is login first login page created using python
from collections import OrderedDict


from module.userRegistration import userRegistration


def main():

    """ This module is used for login user else direct to New user registration"""

    username = input( "Enter username " )
    userdata = userRegistration.getUserData()
    print(userdata)
    # if username in userdata:
    #     pwd = userdata[username]["password"]
    #     userpwd = input( "Enter your password" )
    #     count = 1
    #     while userpwd.strip() != pwd and count < 3:
    #         userpwd = input( "Enter your password" )
    #         count += 1
    #         continue
    #     else:
    #         print( "Please try again" )
    #         exit()
    # else:
    #     data=input("Do you want to Register (y|n)")
    #     if data == "y":
    #         userRegistration.newUserRegistration()
    #     elif data == "n":
    #         print("Thanks for visiting ")
    #         exit()
    #     else:
    #         print("select correct option (y|n)")
    #         exit()


if __name__ == "__main__":
    main()




