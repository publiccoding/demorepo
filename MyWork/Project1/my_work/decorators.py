
class Student:

    scholarship = 5000
    def __init__(self, fname , lname, category, grade):
        self.fname = fname 
        self.lname = lname
        self.category = category
        self.grade = grade 
    
    @classmethod
    def scholarship_amt(cls,amount):
        cls.scholarship = amount
        

    @classmethod
    def student_data(cls, student_name):
        fname, lname, category, grade= student_name.split(' ')
        return cls(fname,lname, category,grade)
        

    @property
    def fullname(self):
        return f'{self.fname}  {self.lname}'

    @property
    def email_id(self):
        return f'{self.fname}.{self.lname}@gmail.com'    
    
    @staticmethod
    def holiday(day):
        if day.weekday() == 5 or day.weekday() == 6:
            return "Its Holiday"
        
    def __repr__(self):
        return f'{self.fullname}'

    def __str__(self):
        return f'{self.email_id}'

    def __add__(self, other):
        return self.category + other.category

    def __len__(self):
        return len(self.fullname)

# class Sport_quota(Student):

#     def __init__(self, fname, lname,category,grade,sport):
#         super().__init__(fname, lname,category,grade)
#         self.sport = sport

    
# class Principal(Student):

#     def __init__(self,fname,lname,category,grade,students=None):
#         super().__init__(fname,lname,category,grade)
#         if students is None:
#             self.students = []
#         else:
#             self.students = students
        
#     def dec_func(name):
#         def mydecorator(func):
#             def wrapper(*args):
#                 print("Your going to modify student record")
#                 result= func(*args)
#                 print("Student record altered check for change in ",name)
#                 return result
#             return wrapper
#         return mydecorator


#     @dec_func("print_student")
#     def add_student(self,student):
#         if student not in self.students:
#             self.students.append(student)

#     @dec_func("print_student")
#     def del_student(self,student):
#         if student in self.students:
#             self.students.remove(student)
    
#     @property    
#     def print_student(self):
        
#         for student in self.students:     
#             print(' --->',student.fullname)
            
# #------------------------ Class decrator Example ------------------------
# class Dec_class(object):

#     def __init__(self, original):
#         self.original = original
#     def __call__(self,*args):
#         print("Decorator class calling.....!")
#         result = self.original(*args)
#         print("Decorator class called.")
#         return result

# @Dec_class
# def dec_func(name):
#     print("inside the dec func for class",name)

# dec_func('thimmarayan called inside the dec_func')
student = Student('thimmarayan','krishnappa', 8,'A')
student1 = Student('kumar','krishnappa', 7,'A')
print("repr methond called",repr(student))
print(str(student))
print(student + student1)
print(len(student1))

# new_student = Student.student_data('lakshmi krishnappa 10 A')
# student.scholarship=6000
# sport = Sport_quota('dav','kris', 8,'A','football')
# print(sport.fullname,sport.email_id,sport.sport)
# print(new_student.category, new_student.email_id)
# Student.scholarship_amt('10000')
# print(Student.scholarship)
# print(student.scholarship)
# print(student1.scholarship)
# import datetime
# print(Student.holiday(datetime.date(2017,12,23)))

# princi = Principal('thimma', 'krishna',15,'master')
# print(princi.fullname,princi.email_id)
# princi.add_student(student)
# princi.add_student(sport)
# princi.print_student
# princi.del_student(student)
# princi.print_student

# ----------------------------Clousers-------------------------------------

# class Average():
#     def __init__(self):
#         self.series = []

#     def __call__(self,val):
#         self.series.append(val)
#         result =sum(self.series)
#         return result/len(self.series)
# avg = Average()

# def closur_func():
#     series = []
#     def average(val):
#         series.append(val)
#         return sum(series)/len(series)
#     return average

# avg = closur_func()

# def closur_func():
#     count = 0
#     sum = 0
#     def average(val):
#         nonlocal count , sum
#         sum += val
#         count +=1
#         return sum / count
#     return average
        
# avg = closur_func()
# print(avg(10))
# print(avg(15))
# print(avg(20))
# print(avg(30))

# print(avg.__code__.co_freevars)
# print(avg.__closure__)
# print(avg.__closure__[0].cell_contents)
# print(avg.__code__.co_varnames)
#avg.__code__