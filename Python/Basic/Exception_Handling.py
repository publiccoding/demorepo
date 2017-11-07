
# # Exception handling using try, except, else and finally clauses
#
# try:
#     x=5
#     n = x / 0
#
# except ZeroDivisionError as e:
#
#     #errno, strerror = e.args
#     #print("I/O error({0}): {1}".format(errno, strerror))
#     # e can be printed directly without using .args:
#     print(e)
#
# except (IOError,ValueError):
#     print("Trying to divid number by zero\n")
#
# else:
#     print("Enter correct numberical value")
#
# finally:
#     print("This statement will execute")
#
#
# # Another example for Exception
#
# import sys
#
# try:
#     f = open('integers.txt')
#     s = f.readline()
#     i = int(s.strip())
# except IOError as e:
#     errno, strerror = e.args
#     print("I/O error({0}): {1}".format(errno,strerror))
#     # e can be printed directly without using .args:
#     print(e.args)
# except ValueError:
#     print("No valid integer in line.")
# except:
#     print("Unexpected error:", sys.exc_info()[0])


# User defined Python Exception

class myexception(Exception):
    '''Base class for other exception'''
    pass

class valueTosmall(myexception):
    '''Raised when input value is too small '''
    pass

class valueTolarge(myexception):
    '''Raised when input value is too large '''
    pass

n=10

while True:

    try:
        x = int(input("Enter you number"))
        if x < n :
            raise valueTosmall
        elif x > n:
            raise valueTolarge
    except valueTosmall:
        print("Vaue is too small \t Please try again")
    except valueTolarge:
        print("Value is larger than expected \t Please try again")
    else:
        print("Congradulation you guessed it correctly")
        exit()










