class Employee:

    no_of_emp = 0
    raise_amt = 1.04
    def __init__(self,first,last,pay):
        self.first = first
        self.last = last
        self.pay = pay
        self.email = first+"."+last+"@company.com"
        Employee.no_of_emp +=1

    def fullname(self):
        return '{} {}'.format(self.first,self.last)

    def apply_raise(self):
        self.pay = int(self.pay * self.raise_amt)

    #@classmethod
    def set_raise_amt(cls,amount):
        cls.raise_amt=amount

    @classmethod
    def str_fmt_method(cls,emp_str):
        first,last,pay = emp_str.split("-")
        return cls(first,last,pay)

    @staticmethod
    def is_workday(day):
        if day.weekday() == 5 or day.weekday == 6:
            return False
        return True

class Developer (Employee ):

    raise_amt = 1.10

    def __init__(self,first,last,pay, prog_lang):

        super().__init__(first,last,pay)
        self.prog_lang = prog_lang

# class Manager(Employee):

#     def __init__(self,first,last,pay,employee=None):
#         Employee.__init__(self,first,last,pay)
#         if employee is None:
#             self.employee = []
#         else:
#             self.employee=employee

#     def addEmp(self,emp):
#         if emp not in self.employee:
#             self.employee.append(emp)
#     def removeEmp(self,emp):
#         if emp in self.employee:
#             self.employee.remove(emp)

#     def printEmp(self):
#         for emp in self.employee:
#             print("===>",emp.fullname())

# dev1 = Developer ( 'thimma', 'krishna', 90000, "python" )
# mgr1 = Manager('Arun',"kumar",200000)


# print(mgr1.email)
# print(dev1.prog_lang)
# mgr1.addEmp(dev1)
# print(mgr1.printEmp())
# mgr1.removeEmp(dev1)
# print(mgr1.printEmp())
Developer.is_workday()
# emp1 = Employee('thimma','krishnappa',95000)
# emp2 = Employee('test','user',100000)
# emp1.set_raise_amt(1.06)
# emp_string1='thimmarayan-krishnappa-90000'
emp_string1='test-user-95000'
Employee.str_fmt_method(emp_string1)
print(Employee.fullname,Employee.first)
# print(new_emp1.email)
# print(new_emp1.pay)
#Employee.raise_amt=1.05
# print(emp1.raise_amt)
# print(emp2.raise_amt)
# print(emp1.apply_raise())
# print(emp2.apply_raise())
# print(emp1.first)
# print(emp1.last)
# print(emp1.fullname())
# print(Employee.fullname(emp1))
# print(emp1.email)
# print('{}.{}@company.com'.format(emp1.first,emp1.last))
# print(emp1.email)
# print(emp2.email)
