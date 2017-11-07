##def variable(*mytuble):
##	for var in mytuble:
##		print(var)
##	return
##variable(10,20,30,30,40,50)
##
##product = lambda var1, var2: var1*var2
##print("result", product(5,12))
##
##var=100
##def sample(var):
##        #var=0
##        print("Local value",var)
##        return
##
##
##print("Global Value",var)
##
##sample(var)

##
##var=100
##def test():
##        print(var)
##        global var
##        var=var +10
##        print(var)
##        return
##test()
##print(var)

##def Hello():
##        print("What is your name?")
##        name=input()
##        print("Hello ", name , ",have a nice day")
##        return
##
##
##myobj=open("test.txt ","w")
##myobj.write("""This is so cool!
##now i can create text files using python!""")
##myobj.close()
##


##print("Enter numeration")
##num=input()
##print("Enter Denominator")
##den= input()
##try:
##    res=int(num)/int(den)
##except:
##    print("You can't divide by zero bye")
##
##else:
##    print("result",res)
##
##finally:
##    print("Evrytime it will be printed ")



class myclass:
    sample = 0
    color_list = ['black', 'white', 'gray']

    def __init__(self):
        print("Enter you name ")
        myclass.name = input()
        myclass.sample = myclass.sample + 1

    def display_result(self):
        print(" Hello " + myclass.name + " Good Day")
        print("No of time object called is ", myclass.sample)

var = 0
mylist = []
while var < 4:
    mylist.append(myclass())
    mylist[var].display_result()
    print(mylist[var])
    var = var + 1

for m in mylist:
    print(m)
