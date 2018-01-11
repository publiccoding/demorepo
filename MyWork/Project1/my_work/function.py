
# def yell(x):
#     return x.upper() + '!'

# bark = yell 

# print(bark.__name__)
# print(bark("Hello"))

# del yell 

# #print(yell("myname"))
# funcs = [bark, str.lower,str.capitalize]
# # def whisper(x):
# #     return x.lower() +'......'
# print(funcs[1]('HelloWORLD'))
# for f in funcs:
#     print(f, f("MyNameis"))

# def greet(func):
#     greeting =func('Hello this is test called')
#     return greeting

# #print(greet(whisper))
# print(list(map(bark, ['Hello','hello','class'])))

# def speak(text):
#     def whisper(t):
#         return t.lower() + '.....?'
#     return whisper(text)

# print(speak('i am '))

# # def get_func(volume):
# #     def yell(t):
# #         return t.upper()+'!!!'
# #     def whisper(t):
# #         return t.lower()+'...........'
# #     if volume > 0.5:
# #         return yell
# #     else:
# #         return whisper

# def get_func(text,volume):
#     def yell():
#         return text.upper()+'!!!'
#     def whisper():
#         return text.lower()+'...........'
#     if volume > 0.5:
#         return yell()
#     else:
#         return whisper()

# print(get_func('Thimmarayan',0.7))

# print(type(object))


# def make_it(x):
#     def add_it(n):
#         return x+n
#     return add_it

# value = make_it(7)
# print(value(5))


# class Average:
#     def __init__(self, n):
#         self.n = n 

#     def __call__(self,x):
#         return self.n + x


# avg = Average(4)
# print(avg(5))
# print(callable(bark))


# add = lambda x,y:x+y
# print(add(4,5))

# def add(x,y):
#     return x +y
# print(add(3,4))

# print((lambda x, y:x+y)(4,5))

# tuple_ = ((1,'b'),(5,'c'),(4,'m'))

# print(sorted(tuple_, key=lambda x:x[1]))

# print(sorted(range(-5,6),key=lambda x:x*x))

# class MyCar:
#     rec = lambda self: print("i am receivere")
#     crash = lambda self: print("Boom crashed")

# car = MyCar()
# car.crash()

# def make_add(n):
#     return lambda x:x + n
# madd=make_add(9)
# print(madd(9))

# print(list(filter(lambda x:x%2 == 0, range(15))))
# print([x for x in range(15) if x%2 == 0])

# Decrator function 

# def nonfuncdec(func):
#     return func

# @nonfuncdec
# def greet():
#     """ Sample greet documentation """
#     return "Hello"

# #greet = nonfuncdec(greet)

# print(greet)
# print(nonfuncdec)

# print(greet())
# print(greet.__name__)
# print(greet.__doc__)

# alter the callable function functionality 
# import functools 

# def funcdec(func):

#     @functools.wraps(func)
#     def wrapper():
#         original_result = func()
#         new_result = original_result.upper()
#         return new_result
#     return wrapper

# @funcdec
# def greet():
#     """ Sample greet documentation """
#     return "Hello"

# upp_func = funcdec(greet)


# print(upp_func.__name__)
# print(upp_func.__doc__)
# print(upp_func)


# def strong(func):
#     def wrapper():
#         return f'<strong>' + func() + '</strong>'
#     return wrapper

# def emphasis(func):
#     def wrapper():
#         return f'<em>'+ func() +'</em>'
#     return wrapper

# @strong
# @emphasis
# def greet():
#     return 'Hello'

#print(greet())

# def logtrace(func):
#     def wrapper(*args,**kwargs):
#         print(f'TRACE {func.__name__} received with {args} and {kwargs}')
#         result = func(*args,**kwargs)
#         print(f'TRACE {func.__name__} called and {}closed')
#         print(result)
#     return wrapper

# @logtrace
# def greet(name, line):
#     return f'{name} {line}'

# greet('Thimma','Hello World')



# def argtest(result, *args, **kwargs):
    # if args:
    #     print(args)
    # elif kwargs:
    #     print(kwargs)
#     print(f'{result} and  {args} keword args are {kwargs} ')

# argtest('Hellow',1,2,3, key='thimma',value='rayan')

# def Argmodify(*args,**kwargs):
#     kwargs['name']='Alice'
#     newargs = args + ('extra',)
#     bing(*newargs,**kwargs)

# def bing(*args,**kwargs):
#         print(f'{args} and {kwargs}')

# Argmodify('this','that','and',name='Thimma')

# class ColorTest:
#     def __init__(self, color, value):
#         self.color = color
#         self.value = value

# class AlwaysBlue(ColorTest):
#     def __init__(self,color, value):
#         super().__init__(color, value)
#         self.color = 'Blue'
# print(AlwaysBlue('Green',344354).color)


# def printVector(x,y,m):
#     print('<%s %s %s>'%(x,y,m))

# tup = (1,0,1)
# list_=[1,0,2]
# dic = {'x':2,'y':4,'m':8 }


# printVector(*tup)
# printVector(*list_)
# printVector(*dic)
# printVector(**dic)
# #print(**dic)


# def foo(value):
#     if value:
#         return value
#     else:
#         return None

# def foo1(value):
#     if value:
#         return value
#     else:
#         return 

# def foo2(value):
#     if value:
#         return value
   
# print(foo(0))
# print(foo1(0))
# print(foo2(0))


# a = [1,2,3]
# b = a

# print(id(a),id(b))
# print(a,b)

# print(a == b)
# print(a is b)

# c = list(a)
# print(c, id(c))
# print(a == c )
# print(a is c)


# class Car:
#     def __init__(self, color , speed):
#         self.color = color 
#         self.speed = speed

#     def __str__(self):
#         return f'a {self.color} Car'

#     def __repr__(self):
#         return f'{self.__class__.__name__} ({self.color!r}, {self.speed!r})'
    
# car = Car('blue',100)

# print(car)
# print(str(car))
# print(f'{car}')
# print(str([car]))

# import datetime

# today = datetime.date.today()

# print(today)

# class MyException(ValueError):
#     pass

# def nametest(name):
#     if len(name) < 10:
#         raise MyException(name)

# nametest('thimma')

# l = [[1,2,3],[4,5,6],[7,8,9]]
# a = l 



# import copy
# b = copy.deepcopy(l)

# l.append('external')


# l.append('another')

# l[1][1]=9
# print(l)
# print(a)
# print(b)

# print(l is b)
# print(l == b)

# from abc import ABCMeta, abstractmethod

# class Base(metaclass=ABCMeta):

#     @abstractmethod
#     def foo(self):
#         pass
#         #return " i am from Base"

#     @abstractmethod
#     def bar(self):
#         pass
#         #return ' i am from Base bar'


# class Concret(Base):
#     def foo(self):
#         return "foo in concret" 
#     def bar(self):
#         return "bar from concret"

    
# #b = Base()
# #print(b.foo())
# #print(b.bar())
# c = Concret()
# print(c.foo())
# #print(c.bar())
 
# Namedtuples in python 

# from collections import namedtuple
# Car = namedtuple('MyCar', 'color spead')
# mycar = Car('red',100)

# print(mycar.color)
# print(mycar)
# print(*mycar)
# color, speed = mycar
# print(color, speed)

# # mycar.color = 'Blue'
# # print(mycar.color)

# class MyExtendedCar(Car):
    
#     def hexcar(self):
#         if self.color =='red':
#             return '000FFFF'
#         else:
#             return '0000000'

# myexcar = MyExtendedCar('red',200)
# print(myexcar.hexcar())

# ExtendedCar = namedtuple('ExtendedCar',Car._fields + ('charges',))
# excar = ExtendedCar('red',150, 40)
# print(excar.charges)

# print(mycar._asdict())
# import json 
# data = json.dumps(mycar._asdict(),indent=4)
# print(data)

# mycar=mycar._replace(color='Blue')
# print(mycar)

# new_car = Car._make(['white',200])
# print(new_car.color)
# print(new_car._replace(color='Blue'))


#Class Variable

# class Dog:
#     num_of_legs = 4

#     def __init__(self,name):
#         self.name = name

# jack=Dog('jack')
# jill=Dog('jill')

# print(jill.num_of_legs)
# print(jack.num_of_legs)
# print(Dog.num_of_legs)
# # Dog.num_of_legs=6
# # print(Dog.num_of_legs)
# # print(jill.num_of_legs)
# # print(jack.num_of_legs)
# jack.num_of_legs=6
# print(Dog.num_of_legs)
# print(jill.num_of_legs)
# print(jack.num_of_legs)
# print(jack.__class__.num_of_legs)


# class ObjectCount():
#     num_instance = 0

#     def __init__(self):
#         self.__class__.num_instance +=1

# print(ObjectCount.num_instance)
# print(ObjectCount().num_instance)
# print(ObjectCount().num_instance)
# print(ObjectCount().num_instance)
# print(ObjectCount().num_instance)


# class ObjectCount():
#     num_instance = 0

#     def __init__(self):
#         self.num_instance +=1

# print(ObjectCount.num_instance)
# print(ObjectCount().num_instance)
# print(ObjectCount().num_instance)
# print(ObjectCount().num_instance)
# print(ObjectCount().num_instance)

# class MyClass:

#     def method(self):
#         return " You have called instance method",self
#     @classmethod
#     def classmethod(cls):
#         return "you have called classmethod",cls
#     @staticmethod
#     def staticmethod():
#         return "you have called static method:"


# obj = MyClass()
# print(obj.method())
# print(obj.classmethod())
# print(obj.staticmethod())

# print(MyClass.classmethod())
# print(MyClass.staticmethod())
# print(MyClass.method(obj))

# class Pizza:
#     def __init__(self, ingredients):
#         self.ingredients = ingredients

#     def __repr__(self):
#         return f'Pizza({self.ingredients})'

#     @classmethod
#     def margrita(cls,ingredent):
#         return cls(ingredent)
    
#     @classmethod
#     def prosudo(cls,ingredent):
#         return cls(ingredent)


# # pizza = Pizza(['tomota','pericone'])
# # print(pizza)
# print(Pizza.margrita(['tomota','pericone']))
# print(Pizza.margrita(['tomota','pericone','capcicum']))




