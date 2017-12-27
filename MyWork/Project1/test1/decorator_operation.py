
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
print(decorator.email)
print(decorator.fullname)
#del decorator.del_user
print(decorator.fullname)

# Decorator operation 

# def dec_argument(name):

#     def dec_function(original_func):

#         def wrapper_func(*args,**kwargs):
#             print(name,": Before orginal fuction from wrapper method",original_func.__name__)
#             result = original_func(*args,**kwargs)
#             print(name,": After orginal function from wrapper method ",original_func.__name__)
#             return result
#         return wrapper_func
#     return dec_function

# @dec_argument("TESTING")
# def add_function(a,b):
#     return a + b 


# Decorator class example 
# class dec_class(object):

#     def __init__(self, original_func):
#         self.original_func = original_func

#     def __call__(self,*args , **kwargs):

#         print("Decorator class called ", self.original_func.__name__)
#         result = self.original_func(*args, **kwargs)
#         return result

# @dec_class
# def display_function(name, age):
#     print("Display method called with value ({},{})".format(name,age))

# print(display_function.__name__)
# print(display_function("Hawk",25))


from functools import wraps

# def my_logger(original_func):
#     import logging
#     logging.basicConfig(filename='{}.log'.format(original_func.__name__),level=logging.INFO)
    
#     @wraps(original_func)
#     def wrapper(*args, **kwargs):
#         logging.info('Ran with args {} and kwargs {}'.format(args, kwargs))
#         result = original_func(*args, **kwargs)
#         return result
#     return wrapper

# def my_timer(original_func):
#     import time
#     t1 = time.time()
    
#     @wraps(original_func)
#     def wrapper(*args, **kwargs):
#         result = original_func(*args, **kwargs)
#         t2 = time.time() - t1 
#         print("Time taken to run ", t2)
#         return result
#     return wrapper

# import time 

# @my_timer
# @my_logger
# def display_function(name, age):
#     time.sleep(1)
#     """ Original function will display the output """
#     print("{} method called with value ({},{})".format(display_function.__name__,name,age))

# display_function("hawk",29)

