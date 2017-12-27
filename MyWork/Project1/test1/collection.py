


# In this session we are going to work on Collection in python 


# 1. Named Tuples


import collections

# Student = collections.namedtuple('Student',['Name','age','rollno'])
# student = Student('Varun',27,100)

# print(student.Name)
# print(student._fields)
# student=student._replace(Name="thimmarayan")
# print(student)

# Ordered Dictionary -> it will maintain same order as insertion if you insert unorded dict into it it will give the unordered data

dict1 = {"name":"thimma","age":27,"wieght":60}
dict2 = {"age":27,"name":"thimma","wieght":60}

# print(dict1==dict2)

# ordect_dict1 = collections.OrderedDict()
# ordect_dict1["name"]="thimma"
# ordect_dict1["age"]=27
# ordect_dict1["wieght"]=60

# ordect_dict2 = collections.OrderedDict()

# ordect_dict2["age"]=27
# ordect_dict2["name"]="thimma"
# ordect_dict2["wieght"]=60

# print(ordect_dict1==ordect_dict2)

# print(dict1)
# print(ordect_dict2)

# Default Dictionary 

# Example 1
# df_dict = collections.defaultdict(lambda: "Default value")
# df_dict['name']='thimma'
# df_dict['age']=27
# print(df_dict['hight'])


#Example 2
# a=('yellow','blue','red','green','yellow','blue','green')
# b=(2,3,5,3,8,1,5)
# d = [(x) for x in zip(a,b)]
# #print(d)
# df_dict = collections.defaultdict(list)

# for k,v in d:
#     df_dict[k].append(v)

# print(df_dict.items())

#Example 3

# s='missisiosdo'

# d=collections.defaultdict(int)

# for i in s:
#     d[i] +=1

# print(d.items())


# Itertools combination and combination releastion

# from itertools import combinations

# print(list(combinations(range(3),2)))
# print(list(combinations('abc',2)))
# print(list(combinations('abcd',3)))

# from itertools import combinations_with_replacement

# print(list(combinations_with_replacement(range(3),2)))
# print(list(combinations_with_replacement('abc',2)))
# print(list(combinations_with_replacement('abcd',3)))

# deque 

from collections import deque

d = deque()

# d.append(1)
# d.append(2)
# d.append(3)
# print(d)
# d.appendleft(4)
# d.appendleft(5)
# d.appendleft(6)
# print(d)
# d.clear()
# print(d)

# d.append(1)
# d.append(3)
# d.append(1)
# d.append(4)
# d.append(2)
# d.append(1)
# d.append(2)

# print(d.count(1)) # outputs no of occurence of particular element

# d.append(1)
# d.append(2)
# d.append(3)
# d.extend('abc')
# d.append('abc')
# d.extend([1,2,3])
# d.append([1,2,3])
# print(d)


# d.append(1)
# d.append(2)
# d.append(3)
# d.extendleft('abc')
# d.append('abc')
# d.extendleft([1,2,3])
# d.append([1,2,3])
# print(d)

# d.append(1)
# d.append(2)
# d.append(3)
# d.append(4)
# d.append(5)
# d.append(6)

# print(d)
# print(d.pop())
# print(d.popleft())

# d.append(1)
# d.append(3)
# d.append(1)
# d.append(4)
# d.append(2)
# d.append(1)
# d.append(2)

# print(d)

# d.remove(1)
# print(d)
# d.remove(4)
# print(d)
# d.remove(1)
# print(d)

# from collections import Counter

# c = Counter('Allahabad')

# print(c)
# print(list(c.elements()))
# print(c.most_common(3))

# c = Counter([1,2,3,2,3,1,4,5,2,6,1,7])

# print(c)

li = ['l','w','c','m']
print([x.upper() for x in li])

