

# #Iterators example  in python

#
# s= 'thimma'
# it = iter(s)  # also assigned  as it=s.__iter__()
# next(it)  # can also iterate as it.__next__()
#
# # Iterators Example
#
# class Reversed():
#
#     def __init__(self, data):
#
#         self.data = data
#         self.index = len(data)
#
#     def __iter__(self):
#
#         return self
#
#     def __next__(self):
#
#         if self.index == 0:
#             raise StopIteration
#         else:
#             self.index = self.index - 1
#             return self.data[self.index]
#
#
# re = Reversed('thimma')
# iter(re)
#
# for i in re:
#     print(i)


'''Generators are similar to Iterator but it will automatically
    create __iter__ and __next__ function and also it save  state
    of the function where it called last time and raise IterationStop
    exception if no data found '''


# def reverse(data):
#     for index in range(len(data)-1, -1, -1):
#         yield data[index]
#
# for char in reverse("thimma"):
#     print(char)

# for v in range(10):
#     print(v)

''' Generator Expression are similar to list comprehension but with 
    parentheses instead of brackets '''

xvec = [10, 20, 30]
yvec = [7, 5, 3]

print(sum(x*y for x, y in zip(xvec,yvec)))

#unique_words = set(word for line in page for word in line.split())

# data = "thimma"
#
# l=list(data[i] for i in range(len(data)-1,-1,-1))
# print(l)







