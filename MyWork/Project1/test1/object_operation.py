
my_list = [1,2,3,5,4,7,6,8]
my_abc = ['a','b','c','d','e','f','g','h']

# list comprehension 

# my_update_list = []
# def multiple(x):
#     "Multiple list value by same and return"
#     return x*x

# for x in my_list:
#     print(multiple(x))

#print(multiple(my_list))

# print([x*x for x in my_list])

# list comprehension with 

# def lambda_func(x):
#     if x % 2 == 0:
#         return x

# # for x in my_list:
# #     print(lambda_func(x))

# mylist = list(map(lambda_func,my_list))
# print(mylist)

#tup_1 = (1,2,3,4,5,6)

# my_tup = filter(lambda x:x%2==0,tup_1)
# print(list(my_tup))

#print((x+x for x in tup_1 ))


# print([x for x in my_list if x % 2 == 0])

# Set Comprehnsion
# set_com = {1,2,3,4,5}

# my_set = {x*2 for x in set_com}
# print(my_set)

# my_val = [x for x in zip(my_list,my_abc)]
# print([(x,y) for x, y in zip(my_list, my_abc)])
# print(my_val)

# def dict_func(my_list,my_abc):

#     dict_com = {}
#     for i in range(len(my_list)):
#         dict_com[my_list[i]] = my_abc[i]    
#     return dict_com

# print(dict_func(my_list,my_abc))
# print({x:y for x,y in zip(my_list, my_abc)})

# def gen_func(num):
#     for x in num:
#         yield x*x

# gen_list = (gen_func(my_list))
# #print(type(gen_list))
# print(gen_list)
# for val in gen_list:
#     print(val)

# gen_obj = (x*x for x in my_list)
# for x in gen_obj:
#     print(x)

# List slicing
# my_list = [1,2,3,4,5,6,7,8]
# #          0 1 2 3 4 5 6 7
# my_abc = ['a','b','c','d','e','f','g','h']
# abc = "abcdef"

# print(my_list[::])
# print(abc[::-1])



# Sorting List 


# my_list.sort() # orginal list will be modified 
# mylist = sorted(my_list) # It will create new list with sorted data 
# print(mylist)

# # sorting String

# string1="efafcksdl"
# #print(string1)
# #string1.sort()
# print(string1)
# print(string1.zfill(10))
# str1 = sorted(string1)
# print(str1)

# # Sorting Tuple

# tup_1 = (1,2,5,2,9)
# tup_2 = sorted(tup_1)
# print(tup_2)

# # Sorting Dictionary value 

# dic_v = {"name":"thimma","age":29,"salaray":95000}
# dic_sort = sorted(dic_v)
# print(dic_sort)

# #Sorting Objects

# class Employee:

#     def __init__(self, first, age , salary):
#         self.first = first 
#         self.age = age 
#         self.salary = salary
    
#     def __repr__(self):
#         return "({},{},{})".format(self.first,self.age,self.salary)


# e1 = Employee("thimma",29,95000)
# e2 = Employee("kumar",26,100000)
# e3 = Employee("lakshmi",42,150000)

# def empsort(name):
#     return name.age

# from operator import attrgetter
# employee = [e1,e2,e3]
# #emp_sort = sorted(employee, key=lambda e:e.age)
# emp_sort = sorted(employee, key=attrgetter("age"))
# print(emp_sort)

# # emplist = attrgetter(employee, "age")
# # print(emplist)

