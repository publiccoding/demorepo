import os 
import psutil

# from contexmanger import contexmanger

# # #print(dir(os))
# # print(dir(psutil))

# class Base(object):
#     def __init__(self):
#         print("Class Base is called")

# class A(Base):
#     def __init__(self):
#         print("Class A is called with super")
#         super(A, self).__init__()
# class B(Base):
#     def __init__(self):
#         print("Class B is called without super")
#         Base.__init__(self)

# class NonReleated(A):
#     def __init__(self):
#         print("Non Releatged class called")
#         super().__init__()

# class subA(A):
#     def __init__(self):
#         print("subclass A is called")
#         super().__init__()

# class subB(B):
#     def __init__(self):
#         print("Sub Class B is called")
#         B.__init__(self)

# class childA(subA,NonReleated):
#     def __init__(self):
#         print("Child A is called along with non Releated class")
#         super().__init__()

# class childB(subB,NonReleated):
#     def __init__(self):
#         print("Child B is called along with non releated class")
#         super().__init__()

# obj = childB()
# print(obj)
# print(childB.__mro__)



# #__new__ returns an object that has the right type
# #__init__ initialises the object created by __new__
# # class A(object):
# #     def __init__(self, arg):
# #         self.arg = arg 

# # a = A('An argument')

# # tmp = A.__new__(A,"An Argument")
# # tmp.__init__("An Argument")
# # a = tmp 

# # A.__new__ is object.__new__
# # id(a.__new__) == id (object.__new__)

# """A slot is nothing more than a memory management nicety: when you define __slots__ on a class, you’re telling the Python interpreter that the list of attributes described within are the only attributes this class will ever need, and a dynamic dictionary is not needed to manage the references to other objects within the class. This can save enormous amounts of space if you have thousands or millions of objects in memory.

# For example, if you define:"""

# # class Foo:
# #     __slots__ = ['x']
# #     def __init__(self, n):
# #         self.x = n

# # y = Foo(1)
# # print(y.x)  # prints "1"
# # y.x = 2
# # print(y.x) # prints "2"
# # y.z = 4    # Throws exception.
# # print(y.z)


# for key in ["a", "b", "c"]:
#     print(getattr(myobject, key, None))

# def minimize():
#     current = yield
#     #maxvalue = yield
#     print("first current",current)
#     #print("max value is ", maxvalue)
#     while True:
#         value = yield "myvalue"
#         print("value in while ",value)
#         print("2nd current in while",current)
#         current = min(value,current)
#         print("3rd current in while",current)


# it = minimize()
# next(it)            # Prime the generator
# print(it.send(10))
# print(it.send(4))
# print(it.send(22))
# print(it.send(-1))