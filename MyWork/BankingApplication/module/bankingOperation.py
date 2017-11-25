from module import userRegistration
class bankingOperation:
    def __init__(self):
        self.userdata = userRegistration.userRegistration.getValue()
        self.data_key = self.userdata.values()
        self.data_value = self.userdata.values ()

    def withdrawAmount(self,username,withdraw):

        if username in self.data_key():
            for bal in self.data_value:
                availAmount = bal["balance"]
                if availAmount >= ( int(withdraw) + 1000):
                    balance = availAmount - availAmount
                    self.data_value["balance"] = balance
                    return True
                else:
                    return False

    def depositAmount(self, username, depamount):
        if username in self.data_key ():
            for bal in self.data_value:
                availAmount = bal["balance"]
                balance = availAmount + depamount
                self.data_value["balance"] = balance
                return True
        else:
            return False

    def balanceCheck(self,username):
        if username in self.data_key ():
            for bal in self.data_value:
                availAmount = bal["balance"]
                return availAmount

    def passwordChange(self,username):

        if username in self.data_key:
            user_pwd = input ( " Enter Old password :" )
            new_pwd = input("Enter New Password")
            confirm_pwd = input("Confirm New Password")
            if new_pwd == confirm_pwd:
                for pwd in self.data_value:
                    if pwd['pwd'] == user_pwd:
                        self.data_value["pwd"] = confirm_pwd
                        return True
            else:
                print("New Password and Confirm Password not same")
                return False

