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
