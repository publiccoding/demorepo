import json
import module.sendEmail
from  module import userRegistration
from  module import sendEmail
from module import bankingOperation
def main():

    """ This module is used for login user else direct to New user registration"""

path = r"C:\Users\kristhim\Desktop\thimma 01302017\programming\Practice\demorepo\MyWork\BankingApplication\module\UserData.txt"
def userRegister():
    data = input( "Do you want to Register (y|n)" )
    if data == "y":
        userRegistration.userRegistration(path).new_User_Registration()
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
                print ( "Logged in successfully" )
                print("Enter appropriate Numbers for the below selection")
                print("1. Change password :")
                print("2. Do you want to deposit amount :")
                print("3. Do you want to Withdraw the amount :")
                print("4. Do you want to check the balance :")
                user_input= input()
                if user_input == "1":
                    if bankingOperation.bankingOperation.passwordChange(username):
                        print("Password changed successfully")
                    else:
                        print("Password not changed")
                if user_input == "2":
                    depamount = input("Enter the amount to deposite")
                    if bankingOperation.bankingOperation.depositAmount(username,depamount):
                        print("Amount Deposited successfully")
                    else:
                        print("Unable to deposite Amount")
                if user_input == "3":
                    withdraw = input("Enter the amount need to withdraw")
                    if bankingOperation.bankingOperation.withdrawAmount(username,withdraw):
                        balanceAmt=bankingOperation.bankingOperation.balanceCheck(username)
                        print("amount withdrawed.. !!1 availabel amount is"+balanceAmt)
                    else:
                        print("Unable to withdraw Amount check for balance ")
                if user_input == "4":
                    balance=bankingOperation.bankingOperation.balanceCheck(username)
                    print("You have "+balance+" In your account")
            else:
                forget_pwd =input("Forget password (yes/no)")
                if forget_pwd == 'yes':
                    email_id = input(" Enter your email id to send password ")
                    for email in userdata.values():
                        if email_id == email['email']:
                            # Enter sending user password to there email id code
                            sendEmail.sendEmailOpration.emailPassword(email_id)

                elif forget_pwd == 'no':
                    print("Exiting the applicaton")
                    exit()

username = input( "Enter username " )
try:
    userdata = userRegistration.userRegistration(path).getValue()
    print(userdata)
    userLogin(userdata)

except:
    userRegister()

if __name__ == "__main__":
    main()


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
    # else:
    #     userRegister()
    #
    #     if username in line.keys ():
    #         pwd = input ( "Enter Password" )
    #         for d in line.values ():
    #             if d['pwd'] == pwd:
    #                 print ( "Your Logged in successfully" )
