
# dic = [
#         {'name':'Thimmarayan','age':30,'address':'bangalore'},
#         {'name':'kumar','age':26,'address':'hosur'},
#         {'name':'lakshmi','age':46,'address':'Varaganappalli'},
#         {'name':'krishnappa','age':52,'address':'Unknown'}
# ]
#
# dict={'name':'Thimmarayan','age':30,'address':'bangalore'}
# print(dict['name'])
#

a="This is test string for test the string contents is which is exist all the strings"

d ={}
for n in a.split():
    if n in d:
        d[n] +=1
        print(n,d[n])
    else:
        d[n]=1
        print(n,d[n])
#print(d)