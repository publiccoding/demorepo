

# Multiple  Boolean operation which is used in the python

# print(not False)
# print(not True)
# print(not not not not True)
# print('hello' == 'hello')
# print('hello' == 'Hello')  # understand Why it is used like this
# print('dog' != 'cat')
# print(True == True)
# print(True != False)
# print(42 == 42.2)
# print(24 == '24')
# print( 42 < 100)
# print( 42 > 100)
# print(True and True)
# print(False and True)

# if statement it will evaluates True and ends with colon(:) if the condition is true print the( output) else no output
# if , else , elif - all are keywords

#----------------------------------------------------------------------------------------------------

#example 1

#
# name =input("Enter your name ")
# age = int(input("Enter your age"))
#
# if name in 'Thimmarayan':
#     print("Hello Thimamrayan")
# elif age == 30:
#     print("Your age is 30")
# else:
#     print("Your are not one i guessed")
#

## while condition to check username and password check

#----------------------------------------------------------------------------------------------------
#exmaple 1
# while True:
#     name = input("Enter you name")
#     if name != 'Thimma':
#         continue
#     print("Hi Thimma!, Enter your password\n")
#     while True:
#         password = input("Enter your password")
#         if password =='Lakrthkuv@1':
#             break
#
#     break
#     print("Password Correct!")
# print("outside inner while loop")
#
#
# print("Credentials are correct")

#----------------------------------------------------------------------------------------------------
#Example 2

# while True:
#     name = input("Enter you name")
#     if name != 'Thimma':
#         continue
#     print("Hi Thimma!, Enter your password\n")
#     password = input("Enter your password")
#     if password =='Lakrthkuv@1':
#         break
#     print("password not correct")

#----------------------------------------------------------------------------------------------------
#Exampel 3:

# while loop  ends with colone(:)
#
# count = 0
#
# while count < 5:
#     count = count +1
#     if count != 4:
#         print(count)
#         continue
#     else:
#         print("else block executed")
#         break
# print("Exit out of the while loop after break ")

#----------------------------------------------------------------------------------------------------
# #Example 4: ( Correct python idiom code )
#
# while True:
#     name = input("Enter you name")
#     password = input("Enter your password")
#     if (name != 'Thimma' or password !='Lakrthkuv@1'):
#         print("Username and password not correct")
#         continue
#     break
# print("Credentials are correct")


# FOR loop


# #Example 1
#
# import sys
# import random
# import sys
# for i in range(5):
#     print(random.randint(1,10))
#
#
# while True:
#     status = input("Enter status code")
#     if status == "Exit":
#         sys.exit()


# Generator Object declaration

# def function(x):
#     for i in range(x,0,-2):
#         yield(i)
#
# a = function(10)
# for i in a:
#     print(i)




















