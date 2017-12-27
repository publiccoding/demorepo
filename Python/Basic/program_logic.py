

'''Generate prime numbers for the given number'''

# def primeNumber(x):
#     t = x
#     count =0
#     while  t > 0:

#         if t%2 == 0:
#             #print(str(t)+" is prime number ")
#             count += 1
#         t -=1
#     print("Total Prime number count is "+str(count))

# primeNumber(100)

'''Generating fibonacci Series'''

# def fibonacciSeries(x):
#    # a = 0
#     b,a = 0,1
#     #print(a)
#     while b < x:

#         print(b)
#         a , b = b , a+b

# fibonacciSeries(51)

'''palindromNumber Number Generation'''

def palindromNumber(x):
    n = x
    t = 0
    while x > 0:
        m = x % 10
        t = t * 10 + m
        x = x // 10

    if t is n :
        print("Plaindrom Number")
    else:
        print("Not Plaindrom Number")

palindromNumber(121)

'''Factorial of the Number'''
def factorialNumber(x):

    t = x
    while x > 1:
        x = x - 1
        t = t * x

    print(t)

factorialNumber(6)

'''Amstron Number generation'''

def amstrongNumber():

    for x in range(1 ,9999):
        a = 0
        if len(str(x)) == 2:
            a = 2
        elif len(str(x)) == 3:
            a = 3
        elif len(str(x)) == 4:
            a = 4
        else:
            a = 0

        t = x
        y = 0
        while x > 1:

            m = x % 10
            y = y + m ** a
            x = x // 10

        if t == y :
            print("Amstrong number "+ str(t))

amstrongNumber()

'''Sorting Number in asecending order'''
# def sortingNumber():
#
#     a = [3,4,2,5,6]
#     l = len(a)
#
#     for i in range(l):
#         for j in range(l):
#             if a [i] < a [j]:
#                 temp = a[i]
#                 a[i] = a[j]
#                 a[j] = temp
#
#
#     print(a)
#
#
# sortingNumber()

































