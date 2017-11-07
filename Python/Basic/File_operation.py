

#open file and write data into it.

f = open("test.txt", "w")
f.write("This data will goes into test file \nIt's sample file operation")
f.close()

# Append data in the existing test file
f = open("test.txt", "a")
f.write("\nThis data will append at  last line")
f.close()

#Read the data from the file.

f = open("test.txt", "r")
a=f.read()
print(a)
f.close()
