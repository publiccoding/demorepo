
# Implementing special variable _, __ 
# class Test:
#     def __init__(self):
#         self.foo = 42
#         self._bar = 52 
#         self.__baz = 62
    
# class Test1(Test):
#     def __init__(self):
#         super().__init__()
#         self.foo = 'test foo'
#         self._bar = 'test _bar'
#         self.__baz = 'test __baz'


# print(Test().foo)
# print(Test()._bar)
# #print(Test().__baz)
# print(Test()._Test__baz)

# print(Test1().foo)
# print(Test1()._bar)
# #print(Test1().__baz)
# print(Test1()._Test1__baz)

# def special_method(name, class_):
#     pass 
# special_method('thimma','rayan')

# class MangleTest():
    
#     def __init__(self):
#         self._manglevalue=42
#     def external(self):
#         return self._manglevalue
# #print(MangleTest()._manglevalue)
# print(MangleTest().external())

# Mangle method Test

# def _manglemethod():
#     return "_manglemethod"

# def externalmangle():
#     return "external mangle"

# class MangleMethod:

#     def __init__(self):
#         self.__mangleval = 50
        
#     def call_it(self):
#         return self.__mangleval

# #print(MangleMethod().__mangleval)
# print(MangleMethod().call_it())

# class MangleTest:

#     def __manglemethod(self):
#         return 444
#     def externalCall(self):
#         return self.__manglemethod()

# #print(MangleTest().__manglemethod())
# print(MangleTest().externalCall())

# _Mangle__mangle = 500

# class MangleGlobal:

#     def call_ext(self):
#         return _Mangle__mangle

# #print(MangleGlobal().__mangle)
# print(MangleGlobal().call_ext())

# class Testmang:
#     def __init__(self):
#         self.__mangle__ = 9909
    

# print(Testmang().__mangle__)

# for _ in range(5):
#     print('i am ')

# color = ['red','blue','yellow','white','orange']

# car,_,_,nov,val = color
# print(car,nov,val,_)



# name = 'thimma'
# error = 457235723957239

# print('Hello %s you got the Error %x'%(name,error))
# print('Hello %(name)s you got the Error 0x%(error)x'
# % {'name':name,'error':error})
# print('Hello {} you got the Error {:x}'.format(name,error))
# print('Hello {name} you got the below Error {error:x}'
# .format(name=name,error=error))
# print(f'Helow {name} you got the Error {error:x}')

# def greet(name,error):
#     return f' Hellow {name} you got the Error {error:x}'

# print(greet(name,error))

# from string import Template

# print(Template('Hey $name').substitute(name=name))

# SECRET='THis is the Secret key'

# class Error:
#     def __init__(self):
#         pass 

# err = Error()

# print('{error.__init__.__globals__[SECRET]}'.format(error=err))
# print(Template('${error.__init__.__globals__[SECRET]}')
# .substitute(error=err))