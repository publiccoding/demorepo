## Dictionary Value

myCat = {'size': 'fat', 'color': 'gray', 'disposition': 'loud'}
# print('My cat has color  '+myCat['color']+'  and it is fur')
#
# # List is ordered collection of items but same values of another set is not equal
# spam = ['cats', 'dogs', 'moose']
# bacon = ['dogs', 'moose', 'cats']

# myCat['positiona']='sleeping'
# print(myCat)
## Dictonary vs List
# if spam is not bacon: print("True")
# print(spam == bacon)
# eggs = {'name': 'Zophie', 'species': 'cat', 'age': '8'}
# ham = {'species': 'cat', 'age': '8', 'name': 'Zophie'}
# print(eggs == ham)

## Example 1
## Update date of birth database

# #def Birthday_Dict(birthdays):
# birthdays = {'Alice': 'Apr 1', 'Bob': 'Dec 12', 'Carol': 'Mar 4'}
# while True:
#     name = input("Enter a name:(blank to quit)")
#     if name == '':
#         break
#
#     if name in birthdays:
#         print('Date of birth for the '+ name + ' is '+ birthdays[name])
#     else:
#         print('Name and Date of birth not found in the database ')
#         print('Enter the Date of Birth')
#         bday = input()
#         birthdays[name]=bday
#
# print(birthdays)


 ## Keys, values, items function
#
spam = {'color': 'red', 'age': 42}
#
#
# for k in spam.keys():
#     print(k)
#
# for v in spam.values():
#     print(v)
#
# for k,v in spam.items():
#     print('Key'+k+'value'+str(v))
#
# print(spam.keys())
# print(spam.values())
# print(list(spam.items()))
#
# print('color' in spam)
#

# picnicitem = {'apples': 5,'cups':3}
#
# value = input("Key value")
# print('Available '+value+' value is '+str(picnicitem.get(value,0)))
#
# if 'name' not in spam:
#     spam['name']='thimma'
# print(spam)

# # setdefault used to assign the default value
#
# value =input("Enter the value")
# spam.setdefault(value,0)
# print(spam)

import pprint

def Character():

    message = 'It was a bright cold day in April, and the clocks were the striking thirteen.'

    count = {}
    message=message.split(' ')

    for msg in message:
        count.setdefault(msg,0)
        count[msg]=count[msg]+1
        yield count

character =Character()

for char in character:
    print(char)
#
# count = {}
#
# for char in message:
#     count.setdefault(char,0)
#     count[char]=count[char] +1
#     pprint.pprint(count)


