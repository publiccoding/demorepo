

# # List operation
# #list operation is used for
#
spam = ['cat','bat','rat','mat',
        'That','elephant']
# print(len(spam))
# print(spam)
# #print(spam[6])
#
# #Unpacking list values
# a,b,c,d,e = spam
# print(a,b,c,d,e)
#

# # Convert list to tuple
# tuple_value = tuple((spam))
# print(type(tuple_value))

# # Convert tuple to list
# list_value = list(tuple_value)
# print(type(list_value))

#Floating index value not expected
#print(spam[1.0])

#Multiple list values
# spam1 = [[1,2,3],['cat','bat','rat','that']]
# print(spam1[1], spam1[0])
# print(spam1[0][1])
#
# print(spam[:3])
# print(spam[3:])
#
# spam = spam + ['A','B','C']
# print(spam)

#
# # looping List
#
# for i in range(len(spam)):
#     print(" Index value "+str(i)+" list value is "+spam[i])
#
# # In and Not in operation usage
#
# print('cat' in spam) # Return True value
# print('tat' in spam) # Return False value
# print('tat' not in spam) # Return True value

#
# # Example 1
#
# list = []
#
# while True:
#     print("Enter the list values for "+str(len(list) + 1)+" Nothing to stop")
#     name = input()
#
#     if name == '':
#         break
#     else:
#         list.append(name)
#
# for name in list:
#     print(name)
#
# # Example 2:
#
# while True:
#
#     value = input("Enter the value need to check")
#
#     if value in spam:
#         print("Value is in list"+value)
#         break
#     else:
#         print("Trye again ...")
#

## Assginment operator
#
# value =42
# value +=1
# print(value)
#
# print(type(['Hello',]))
# print(type('Hello'))
#
# # find incex value of object in list
# print(spam.index('cat'))
# print(spam.append('myvalue'))
# print(spam.insert(1,'total'))
# print(spam.remove('cat'))
# print(spam)
# print(spam)

# spam.sort()
# print(spam)
# spam.sort(reverse=True)
# print(spam)
# spam.sort(key=str.lower)
# print(spam)

# # list Reference operation

##List assignment always take reference ID to assign another list instead of values if you modify any list value , value will refelected in another list


# print(spam)
# cheese = spam
# print(cheese)
# cheese[0]='What'
# print(spam)
# print(cheese)

## copy module will one list to another with different reference id
## copy.deepcopy will be used to modify the inner list
# import copy
#
# print(spam)
# cheese = copy.copy(spam)
# print(cheese)
# cheese[0]='What'
# print(spam)
# print(cheese)

# # Practice program for list
#
# def Comma_code(spam):
#     l = len(spam)
#     t=0
#     while t <=l:
#
#
#
#
# spam = ['apples','bananas','tofu','cats']
#
# value = Comma_code(spam)


#
# ##Grip Picture
#
# grid = [
# ['.', '.', '.', '.', '.', '.'],
# ['.', 'O', 'O', '.', '.', '.'],
# ['O', 'O', 'O', 'O', '.', '.'],
# ['O', 'O', 'O', 'O', 'O', '.'],
# ['.', 'O', 'O', 'O', 'O', 'O'],
# ['O', 'O', 'O', 'O', 'O', '.'],
# ['O', 'O', 'O', 'O', '.', '.'],
# ['.', 'O', 'O', '.', '.', '.'],
# ['.', '.', '.', '.', '.', '.']]
#
# for i in range(len(grid[0])):
#     print( '\n' )
#
#     for j in range(len(grid)):
#         print(grid[j][i],end='')










