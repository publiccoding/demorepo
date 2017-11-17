
class userRegistration:
    """    """

    def __init__(self):
        self.userData = {}


    def new_User_Registration(self):

        self.userData = {"thimma@gmail.com": {'Name': 'Thimmarayan', 'password': 'Lakrthkuv@1'}}
        uname = input("Enter username :")
        count = 1
        while uname in self.userData and count < 3:
            uname = input("Enter another valid username")
            count +=1
            continue

        if uname not in self.userData:
            return self.userData

        else:
            return self.userData

    def getValue(self):
        return self.userData

a = userRegistration()

value = a.new_User_Registration()
print(value)


