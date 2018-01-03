# coding: utf-8
def yell(text):
    return text.upper()+'....!!!'
bark = yell
bark
bark('Hello')
del yell
yell('hello')
bark.__name__
funcs = [bark,str.lower,str.upper]
for f in funcs:
    print(f)
    
for f in funcs:
    print(f,f('Hello There'))
    
list(map(bark,['hello','i am ','there']))
def whisper(func)
def whisper(func):
    return func('I am thimma Called this function')
def greet(func):
    return func('I am thimma Called this function')
def whisper(t):
    return t.lower()+'....?'
greet(whisper)
greet(bark)
def get_func(t):
    def yell(text):
        return text.upper()+'....!!'
    def whisper(text):
        return text.lower()+'......????'
    if t >0.5:
        return yell
    else:
        return whisper
    
   
get_func(0.5)
get_func(0.6)
getfunc = get_func(0.6)
getfunc('Thimmarau')
def get_func(text,volume):
    def yell():
        return text.upper()+'....!!'
    def whisper():
        return text.lower()+'......????'
    if t >0.5:
        return yell()
    else:
        return whisper()
    
    
   
get_func('Thimmareauraefn',0.8)
def get_func(text,volume):
    def yell():
        return text.upper()+'....!!'
    def whisper():
        return text.lower()+'......????'
    if volume >0.5:
        return yell()
    else:
        return whisper()
    
    
   
get_func('Thimmarayan',0.8)
get_func('Thimmarayan',0.4)
def add_more(v):
    def add_it(n):
        return v + n
    return add_it
add = add_more(6)
add(5)
def speak(t):
    def whisp(val):
        return "i am called"
    return whisp(t)
speak('Thimma')
def speak(t):
    def whisp(val):
        return val.lower()+'.....????'
    
    return whisp(t)
speak('Thimma')
class call:
    def __init__(self,x):
        self.x = x
        
class call:
    def __init__(self,x):
        self.x = x
    def __call__(self,n):
        return x + n
    
        
call = call()
call = call(7)
call(8)
call(8)
class call:
    def __init__(self,x):
        self.x = x
    def __call__(self,n):
        return self.x + n
    
    
        
call = call(9)
call(5)
callable(bark)
callable('hello')
add = lambda x,y:x+y
add(4,5)
(lambda x,y:x+y)(8,9)
tup = ((1,'c'),(3,'b'),(5,'a'),(2,'d'))
sorted(tup, lambda x:x[1])
sorted(tup, key=lambda x:x[1])
sorted(tup, key=lambda x:x[0])
sorted(range(-5,6),key=lambda x:x*x)
def make_add(n):
    return lambda y:y+n
add = make_add(8)
add(7)
class MyCar:
    rec = lambda self:print("Received Car")
    crash = lambda self:print("Boom Crashed Car")
    
car = MyCar()
car.crash()
car = MyCar
print(car)
car = MyCar()
print(car)
get_ipython().run_line_magic('save', '-a mysession 1-999999')
