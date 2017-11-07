
# # This example explains Functions
# # Variable Global ( destoryed once it class is called )  and Local scope will be destoryed once is out of function exit
# # Exceptional Handling
# # Gussing Game
#
# #--------------------------------------------------------------------------------------
#
# #Example 1
#
# def method():
#     print("Hello")
#     print("Hello !")
#     print("Hello World ")
#
# method()
#
# #----------------------------------------------------------------------------------------
# # Example 2:
#
# def method(name):
#     print("Hello" + name)
#     print("Hello !" + name)
#     print("Hello World "+name)
#
# method("Thimmarayan")
# print(name)
#
# #----------------------------------------------------------------------------------------
# #Example 3:
#
# def VariablScope():
#     eggs = "thimmarayan" # Global Scope
#     becon()
#     print(eggs)
#
#
# def becon():
#     eggs ="Kumar" # Local scope
#
# VariablScope()
#

# #----------------------------------------------------------------------------------------
# #Example 4:
#
# def spam():
#     print(eggs)  # Error call call before assignment
#     eggs="this is golden eggs"
#
# eggs="Global"
#
# spam()

# #----------------------------------------------------------------------------------------
# #Example 5:
#
#
# def GlobalDeclaration():
#     global eggs
#     eggs = "This is global declaration from local function"
#
# def becon():
#     eggs="localvariabl"
#
# def Ham():
#     print(eggs)
#
# global eggs
# eggs = 42
# print(eggs)
# GlobalDeclaration()
# becon()
# Ham()
# print(eggs)


# Exceptional Handling
# #----------------------------------------------------------------------------------------
# #Example 6:

#
# def ExceptionHandling(divid):
#     try:
#         return 42 / divid
#     except ZeroDivisionError:
#         print("Invaild Value")
#
#
# print(ExceptionHandling(0))
# print(ExceptionHandling(12))
# print(ExceptionHandling(6))


# #----------------------------------------------------------------------------------------
# #Example 7:
#
# import random
# # Guessing Game
# def SteakGuess():
#     guess = random.randint(1,20)
#
#     for i in range(1,7):
#         steakvalue = int(input("Enter your gusseing value"))
#
#         if steakvalue > guess:
#             print("Your Guess is larger value")
#         elif steakvalue < guess:
#             print("Your Guess is lower value")
#         else:
#             break
#
#     if guess == steakvalue:
#         print("Your guessed correct "+ str(guess))
#     else:
#         print(" guessed value was " + str(guess))
#
# SteakGuess()


# #----------------------------------------------------------------------------------------
# #Example 7:



# def collatz(number):
#
#     if number %2 == 0:
#         print(number // 2)
#         return number // 2
#
#     else:
#         print(3 * number + 1)
#         return 3 * number + 1
#
# print("Enter number ")
# while True:
#     try:
#         number = int(input())
#         value=collatz(number)
#     except ValueError:
#         print("Please enter integer value")
#
#     if value == 1:
#         break



















