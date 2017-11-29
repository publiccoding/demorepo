# #Keyword Arguments
#
# ''' Default arguments should follow  Non default arguments '''
#
# def parrot(voltage,state='a stiff', action="voom", type='Norwegian Blue'):
#     print("if you put", voltage, "volts through it.")
#     print("-- Lovely plumage, the", type)
#     print("-- You don't miss the action from", action)
#     print("-- It's", state, "!")
#
# '''if positional and keyword arguments passed to the function
#  positional should be first then keyword arguments'''
#
# parrot(1000) # 1 positional argument
# parrot(voltage=1000) # 1 keyword argument
# parrot(1000, 'VOOOOM') # 2 Positional arguments,  value will get assigned sequencly
# print()
# parrot(voltage=1000000, action='VOOOOOM') # 2 keyword arguments
# parrot(action='VOOOOOM', voltage=1000000) # 2 keyword arguments
# parrot('a million', 'bereft of life', 'jump') # 3 positional arguments
# parrot('a thousand', state='pushing up the daisies')
#
# # non keywork should be first and follows keywork argument.
#
# #parrot(voltage=5.0, 'dead') # non-keyword argument after a keyword argument
# print("_"* 40)
#
# def cheeseshop(kind, *arguments, **keywords):
#     print("-- Do you have any", kind, "?")
#     print("-- I'm sorry, we're all out of", kind)
#     for arg in arguments:
#         print(arg)
#     print("-" * 40)
#     for kw in keywords:
#         print(kw, ":", keywords[kw])
#
# cheeseshop("Limburger", "It's very runny, sir.",
# "It's really very, VERY runny, sir.",
# shopkeeper="Michael Palin",
# client="John Cleese",
# sketch="Cheese Shop Sketch")
#
# print("_" * 40)
# #Arbitrary Argument Lists
# def concat(*args, sep="/"):
#     return sep.join(args)
#
# print(concat("earth", "mars", "venus"))
# print(concat("earth", "mars", "venus", sep="."))
# print("_" * 40)
#
# #Unpacking arguments
# def parrot(voltage, state='a stiff', action='voom'):
#     print("-- This parrot wouldn't", action, end=' ')
#     print("if you put", voltage, "volts through it.", end=' ')
#     print("E's", state, "!")
# d = {"voltage": "four million", "state": "bleedin' demised", "action": "VOOM"}
# parrot(**d)
# print("_" * 40)
# #Lambda Expressions
#
# def make_increment(n):
#     return n%2 == 0
# print(make_increment(5))
#
# k=lambda x:x%2 == 0
# print(k(2))
#
#
#
#





#
# def myfunction(start=1,stop ,step=1):
#     while start < stop:
#         yield start
#         start = start + step
#
# for i in myfunction(2,20,2):
#     print(i)


def function():
    value=1
    if value in dict:
        print("this is test")
