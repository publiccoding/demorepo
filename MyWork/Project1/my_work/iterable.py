import iterable

# class iterable_test1:
#     def __init__(self,value):
#         self.value = value

#     def __iter__(self):
#         return repeaterobject(self)

# class repeaterobject:
    
#     def __init__(self,num):
#         self.num = num  

#     def __next__(self):
#         return self.num.value

# it = iterable_test1('Hello')

# print(next(it))

# for i in iterable_test('Hi'):
#     print(i)

#print(next(itr))



# class iterable_test:
#     def __init__(self,value):
#         self.value = value

#     def __iter__(self):
#         return self

#     def __next__(self):
#         return self.value

# it = iterable_test('Hello')

# next(it)





class dict_object:
    
    def __init__(self, data):
        self.data = data
    
    def __setitem__(self,k,v):
        self.data[k]=v

    def __getitem__(self,k):

        try:
            print(self.data[k])
        except:
            print("Key error")


mydata = {x: x*x for x in range(10)}
dic = dict_object(mydata)


dic[5]
dic[11]=121

dic[12]