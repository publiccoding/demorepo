
# #List operations
#
# fruits = ['orange', 'apple', 'pear', 'banana', 'kiwi', 'apple', 'banana']
# print(fruits.count('apple'))
# print(fruits.index('banana',4))
# print(fruits.append('thimma'))
# print(fruits)
# print(fruits.reverse())
# print(fruits)
# print(fruits.remove('apple'))
# print(fruits)
# print(fruits.sort())
# print(fruits)
# print(fruits.pop())
# print(fruits)


# #List Comprehensions


## Normal method of calling creating list
# squares = []
# for x in range(10):
#     squares.append(x**2)
#
# print(squares)

# # Lambda method for creating list value


# squares = list(map(lambda x:x**2,range(5)))
# print(squares)
#
# # List Comprehension method for creating value
# squares = list(x**2 for x in range(5))
# print(squares)
#
# # List comprehension using multiple for loop
#
# squares = list((x,y) for x in range(5) for y in range(6) if x!=y)
# print(squares)

## Matrix List comprehension values

# matrix =[
#     [1,2,3],
#     [4,5,6],
#     [7,8,9]
# ]
#
# trans = []
#
# for i in range(3):
#     trans.append([row[i] for row in matrix])
# print(trans)

# # Tuples in python
#
# t = 12345, 54321, 'hello!'
# u= t + (1,2,3,4,5)
# print(u)
#
#
# #Dictionary in python is key value pair called based on indes
#
# knights = {'gallahad': 'the pure', 'robin': 'the brave'}
#
# for k, v in knights.items():
#     print(k +"==>"+v)
# for k in knights.keys():
#     print(k)
# for k in knights.values():
#     print(k)
#


# # Enumaration method provide the output with index and value format
#
#
# for i, v in enumerate(['tic', 'tac', 'toe']):
#     print("Index value {} and actual value is {}".format(i,v))
#     print("Index {1} and actual value {0}".format(i,v))

# for i in reversed(range(1,10,2)):
#     print(i)
#
# Using Zip method in python

# a=[1,2,3,4,5]
# b=[6,7,8,9,0]
#
# for i in zip(a,b):
#     print(i)
#
#
# # Using map fucntion in Python
# # Map function takes function and iteratable as input
#
#
# value = list(map(max, zip(a,b))) # Lambada function also used with this function
# print(value)


