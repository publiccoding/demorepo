# class A:
#     def __init__(self,a):
#         self.a = a


# In [34]: tmp = object.__new__(A)

# In [35]: A.__init__(tmp,5)


# a = [1,2,3]
# b = a

# print(a)
# print(b)
# print(id(a))
# print(id(b))
# b.append(10)
# print(a)
# print(id(a))

# class Test:
#     def __init__(self):
#         print("The value is %d"%id(self))

# t = Test()

# names = {'charlie':'value','bob':'montria','lewis':500,
# 'montrial':'value ','latter':'last chance'}

# name = names 
# print(name is names )
# name['lewis']=6000
# print(name is names )
# print(id(name),id(names))

# alex = {'charlie':'value','bob':'montria','lewis':6000,
# 'montrial':'value ','latter':'last chance'}

# print(alex == name)
# print(alex is not name)

# t1 = (1,2,3, [4,5])
# t2 = (1,2,3, [4,5])
# print(t1 == t2)
# print(id(t1[-1]))
# print(t1[-1].append(99))
# print(id(t1[-1]))
# print(t1 == t2)
# print(t1,t2)

# l = [1,[2,3,4],(5,6,7)]
# l2 = l
# print(l,l2)
# print(id(l),print(id(l2)))
# print(l is l2)
# print(l == l2)
# print('\n')
# l.append(100)
# l[1].remove(3)

# print(l,l2)
# print('\n')
# print(id(l),print(id(l2)))
# l2[1] += [33,22]
# l2[2] += (10,11)

# print(l,l2)
# print('\n')
# print(id(l),print(id(l2)))

# class Bus:
#     def __init__(self, passenger=[]):
#        self.passenger = passenger

#     def pick(self, name):
#         self.passenger.append(name)
    
#     def drop(self, name):
#         self.passenger.remove(name)


# import copy 

# bus1 = Bus(['Alice','Bill','Claire','David'])
# bus2 = copy.copy(bus1)
# bus3 = copy.deepcopy(bus1)
# print(id(bus1),id(bus2),id(bus3))

# bus1.drop('Bill')
# print(bus2.passenger)
# print(id(bus1.passenger),id(bus2.passenger),id(bus3.passenger))


# bus1 = Bus(['Alice','Bill'])
# print(bus1.passenger)
# bus1.pick('Charlie')
# bus1.drop('Alice')
# print(bus1.passenger)
# bus2 = Bus()
# bus2.pick('Carrie')
# print(bus2.passenger)
# bus3 = Bus()
# print(bus3.passenger)
# bus3.pick('Dave')
# print(bus2.passenger)

# #print(dir(Bus.__init__))
# print(Bus.__init__.__defaults__[0] is bus2.passenger)

import pdb 
import weakref

s1 = {1,2,3}
s2 = s1
pdb.set_trace()
def bye():
    print('Test bye...')
end = weakref.finalize(s1,bye)
print(end.alive)
del s1
print(end.alive)
s2 = 'spam'
print(end.alive)

