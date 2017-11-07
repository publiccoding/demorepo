
# Variable will be declared and assingned with value ( object reference - value always referred as object )
#sys.getrefcount() -> used to get the object count(value count for a variable)

# a = 10
# print(a)
# b='String' * 10
# print(b)
# print(type(str(100)))
# print(int(2.5)) # will print rounded value


# Sample program to get input and store in value display output


print("This is simple program to get user input")
name = input("Enter your name")
mAge = input("Enter your age")
print(name +' you age is '+ str(mAge)+' and name contains ' + str(len(name))+' Characters')

