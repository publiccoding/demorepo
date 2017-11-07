
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fmt = logging.Formatter('%(asctime)s:[%(levelname)s]:%(name)s:%(message)s')
file_handler = logging.FileHandler('example.log')
file_handler.setFormatter(fmt)
logger.addHandler(file_handler)
logging.basicConfig(format=fmt, filename='example.log',level=logging.INFO)


# class Emp:
#
#     raise_amt = 1.04
#
#     def __init__(self,first,last,pay):
#         # self.m=20
#         # self._m=25
#         # self.__m=30
#         self.first=first
#         self.last = last
#        # self.email= first + '.' + last + '@email.com'
#         self.pay = pay
#         #logger.info(" Constructer for log class initiated {}".format(self.m))
#     @property
#     def email(self):
#         return '{}.{}@email.com'.format(self.first,self.last)
#     @property
#     def fullname(self):
#         return '{} {}'.format(self.first,self.last)
#     @fullname.setter
#     def fullname(self,name):
#         first , last = name.split(' ')
#         self.first = first
#         self.last = last
#
#     def apply_raise(self):
#         self.pay = int(self.pay * self.raise_amt)
#
#     def __str__(self):
#         #logger.warning("value is assinged  {}".format(self._m))
#         logger.error("this value is not printed")
#         return "Tested Dunder class"
#
#     def __len__(self):
#         return len(self.fullname())
#
#     def simple(self):
#         print("test method")
#
#
# class Dev(Emp):
#
#     raise_amt = 1.10
#
#     def __init__(self, first, last, pay, prog_lang):
#         super().__init__(first,last,pay)
#         self.prog_lang = prog_lang
#
#     def __len__(self):
#         return len(self.fullname())
#
#
# class Manager(Emp):
#     def __init__(self, first, last, pay, emp=None):
#         super().__init__(first,last,pay)
#
#         if emp is None:
#             self.emp = []
#         else:
#             self.emp = emp
#
#     def add_emp(self,e):
#
#         if e not in self.emp:
#             self.emp.append(e)
#
#     def remove_emp(self,e):
#         if e in self.emp:
#             self.emp.remove(e)
#
#     def print_emp(self):
#
#         for i in self.emp:
#             print('--->', i.fullname())
#
#
#     def __repr__(self):
#
#         return "Employee('{}','{}','{}')".format(self.first,self.last,self.pay)
#
#     def __str__(self):
#         return '{} - {}'.format(self.fullname(),self.email)
#
#
#     def __add__(self, other):
#         return self.pay + other.pay
#
#     def __len__(self):
#         return len(self.fullname())
#
#
# dev1 = Dev("thimma","Rayan", 50000, "java")
# dev2 = Dev("Lakshmi","Amma",40000,"python")
#
# emp1 = Emp("krishnappa","Gowda",60000)
# mgr1 = Manager("Kumar", "krishnappa", 90000, [dev1])
# mgr2 = Manager("Lakshmimamma", "Krishnappa", 90000, [dev1])
#
# emp1.fullname = 'Thimmarayan Krishnappa'
#
# print(emp1.first)
# print(emp1.last)
# print(emp1.fullname)
# print(emp1.email)
#
# print(mgr1 + mgr2)
# print(len(emp1))
# print(1+2)
# print(int.__add__(1,2))
# print(emp1.email)
# print(mgr)
# print(repr(mgr))
# print(str(mgr))
# print(mgr.__repr__())
# print(mgr.__str__())
#
# print(dev1.email)
# print(dev1.pay)
# dev1.apply_raise()
# print(dev1.pay)
# print(dev1.prog_lang)
#
#
# print(mgr.email)
# mgr.add_emp(dev2)
# mgr.print_emp()
# mgr.remove_emp(dev2)
#
# print("=============================")
#
# mgr.print_emp()
# print ( issubclass(Dev,Emp))
#
# print(dir(dev1))
# print(help(mgr))
#
