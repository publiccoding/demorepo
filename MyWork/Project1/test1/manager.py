
class Decorator_test:

    """  class test   """
 
    no_of_emp = 0
    raise_amt = 1.04
    def __init__(self,first,last,pay):
        self.first = first
        self.last = last
        self.pay = pay
        #self.email = first+"."+last+"@company.com"
        Decorator_test.no_of_emp +=1

    @property
    def email(self):
        return '{}.{}@gmail.com'.format(self.first,self.last)

    @property
    def fullname(self):
        return '{} {}'.format(self.first,self.last)

    @fullname.setter
    def split_name(self,name):
        first, last = name.split(' ')
        self.first = first
        self.last = last 

    @fullname.deleter
    def del_user(self):
        print("Deleter module called")
        self.first = None
        self.last = None

         
decorator = Decorator_test("test","user",90000)
print(decorator.email)
decorator.first = "test1"
decorator.split_name = "test2 user2"
#print(decorator.first)
#print(decorator.email)
print(decorator.fullname)
del decorator.del_user
print(decorator.fullname)