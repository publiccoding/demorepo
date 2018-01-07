# data = {

# 'bob':890,
# 'alice':235,
# 'jack':890

# }

# print(data['alice'])

# xvalue = {x:x*x for x in range(6)}
# print(xvalue)
# data['thimma']=900
# data['kumar']=800

# print(data)
# import collections

# key1 = collections.OrderedDict(one=1,two=2)
# print(key1)
# key1['four']=4

# print(key1)

# dog = collections.defaultdict(list)
# dog['dog'].append('Jill')
# dog['dog'].append('jack')

# print(dog['dog'])

# chain = collections.ChainMap(data,xvalue)
# print(chain)
# print(chain[5])
# print(chain['jack'])


# import types
# writable ={'one':1,'two':2}
# readonly =types.MappingProxyType(writable) 

# print(readonly)
# writable['three']=3
# print(readonly)
# print(writable)
# readonly['three']=3
# #readonly['five']=5


#list 

# arr = ['one','two','three']
# print(arr,arr[0])
# arr[1] ='Hello'
# del arr[1]
# print(arr,arr[0])

#tuple

# arr = ('one','two','three')
# print(arr,arr[0])
# arr[1]='hellow'


#array.array

# import array 

# arr = array.array('f',(1.0,1.5,2.0,2.5))
# print(arr, arr[1])
# arr[1]=23.0
# print(arr, arr[1])
# del arr[1]
# print(arr,arr[1])
# arr.append(42.0)
# print(arr,arr[1])
# arr[1]=42
# print(arr,arr[1])
# arr[1]='Hello'
# print(arr,arr[1])

#String type 

# arr = 'abcd'
# print(arr[1])
# print('-'.join(list(arr)))

#bytes array type  supports (0-256) integer bytes immutable byte type
# arr = bytes((0,1,5,3,4))
# print(arr[1])
# #print(bytes((0,300)))
# arr[1]=23
# del arr[1]

#byte array mutable array type 

# arr = bytearray((2.4,5.6,9.0))
# print(arr,arr[1])
# arr[1]=45
# del arr[1]
# arr.append(43)
# print(arr,arr[-1])
# arr[1]='Hellow'

# carl = {'color':'red',
#         'milage':3456,
#         'automatic':True
#         }

# carl2 = {'color':'blue',
#         'milage':8456,
#         'automatic':False
#         }

# carl['color']="green"
# carl['windshield']='broken'
# print(carl)
# print(carl2)


# class Car:
#     def __init__(self, color , milage, automatic):
#         self.color = color 
#         self.milage = milage
#         self.automatic = automatic

#     def __repr__(self):
#         return f'{self.color} {self.milage} {self.automatic}\n'

# car = Car("red",3456,True)
# car1 = Car("blue",6768,False)
# print(car, car1)
# print(car.milage)
# car1.milage = 35
# print(car1.milage)


# from typing import NamedTuple

# class Car(NamedTuple):
#     color: str 
#     milage: float
#     automatic: bool 

# car1 = Car('Red',3456.09, True)

# print(car1)
# print(car1.milage)

# # car1.milage = 56
# # car1.windshield ='broken'

# car2 =Car('Red','NOT FLOAT',99)
# print(car2)


# from struct import Struct

# mystruct = Struct('i?f')
# data = mystruct.pack(23,False,42.0)
# print(data)

# print(mystruct.unpack(data))

# from types import SimpleNamespace

# car1 = SimpleNamespace(color = 'red',
#                         milage=4588,
#                         automatic=True)

# print(car1.milage)
# del car1.automatic
# car1.windshield='broken'
# print(car1)

# vowels = {'a','e','i','o','u'}
# print('e' in vowels)
# vowels.add('x')
# print(vowels)

# set1 = {x*x for x in range(10)}
# print(set1)

#Immutable sets ( frozenset)

# vowels = frozenset({'a','e','i','o','u'})

# print(vowels)
# vowels.add('y')


#Stack (LIFO) Operation 

# List example

# l = [1,2,3,4]
# print(l)
# l.append(4)
# print(l)
# print(l.pop())

from collections import deque

# l = [1,2,3,4]
# a = deque(l)
# a.append(5)

# print(a)

# print(a.pop())

# import queue

# l = queue.LifoQueue()
# l.put(1)
# l.put(2)
# l.put(3)

# print(l.get())
# print(l.get())


# FIFO ( Queue ) Operation 

# l = []

# l.insert(0,1)
# l.insert(1,2)
# l.insert(2,3)
# l.insert(3,4)

# print(l)
# l.remove(1)
# print(l)

# d = deque(())

# d.append(1)
# d.append(2)
# d.append(3)
# print(d)
# d.popleft()
# d.popleft()
# d.popleft()
# print(d)



import heapq

h = []

