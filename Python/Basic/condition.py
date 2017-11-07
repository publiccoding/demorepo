
#Inheritance


class A():

    a=10
    def __init__(self,x):
        self.x=x


    def Call(self):
        print("class A called ")

class B(A):
    b=0

    def __init__(self,y):
        self.y = y

    def Call(self):
        print("Class B called")

class C(B):

    c=0
    def __init__(self,z):
        self.z=z

    def Call(self):
        print("Class C is called ")


class T(A):
    pass




a=A(3)
b=B(4)
c=C(5)
t=T(c)
print(t.Call())
print(t.a)



# String operation

# str = "this is stirng maniplulation"
# print(str.split(" "))



# list = ['l','m','p']
# for i , v in enumerate(list):
#     print ( '{} --> {}'.format(i,v))
#
#
# import random
# from urllib import request
#
# goog_url ='www.domain.co.uk/prices.csv'
#
# def download_stock_data(csv_url):
#     response = request.urlopen(csv_url)
#     csv = response.read()
#     csv_str = str(csv)
#     lines = csv_str.split("\\n")
#     dest_url = r'goog.csv'
#     fx = open(dest_url,"w")
#     for line in lines:
#         fx.write(line + "\n")
#     fx.close()
# download_stock_data(goog_url)
#
# fw = open('sample.txt','w')
# fw.write("This is sample test for writing data in file\n")
# fw.write("i like programming")
# fw.close()
#
#
# fr = open('sample.txt', 'r')
# text = fr.read()
# print(text)
# fr.close()

#
# def download_web_image(url):
#     name = random.randrange(1,100)
#     full_name = str(name) + ".jpg"
#     urllib.request.urlretrieve(url,full_name)
#
# download_web_image("http://www.21stcenturytiger.org/wp-content/blogs.dir/2/files/public-photos/DSC_0091-1.jpg")
#

# x = random.randrange(1,20)
# print(x)

# classmates = {'Tony':'cool', 'Emma':'Sites behind me', 'lucy':'asks too many question'}
#
# for k, v in classmates.items():
#     print(k +"\t-->"+ v)

# def health_calc(age,apple_ate,cigs_smoked):
#     answer = (100-age) + (apple_ate*3.5) - (cigs_smoked * 2)
#     print(answer)
#
# bucky_data = [27,20,0]
#
# health_calc(bucky_data[0],bucky_data[1],bucky_data[2])
# health_calc(*bucky_data)

# def add_numbers(*args):
#     total = 0
#     for a in args:
#         total += a
#     print(total)
#
# add_numbers(9)
# add_numbers(3,6,7)

# def get_gender(sex='Unknown'):
#     if sex is 'm':
#         sex = "Male"
#     elif sex is 'f':
#         sex = "Female"
#     print(sex)
#
# get_gender('m')
# get_gender('f')
# get_gender()


# def allowed_dating_age(my_age):
#     girls_age = my_age/2 + 7
#     return round(girls_age)
#
# print(allowed_dating_age(27))

# numtoken = [2,5,12,13,17]
#
# print("here are the numbers ")
#
# for n in range(1,20):
#     if n in numtoken:
#         continue
#     print(n)

# for n in range(100):
#     if n%4==0:
#         print("Matched 4 multiples",n)





# name = str(input("Enter you name"))
# print(name)
#
# if name is "Bucky":
#     print("Hey there bucky")
# elif name is "Lucy":
#     print("Hey there Lucy")
# elif name is "Sammy":
#     print("Whats up Sammy")
# else:
#     print("please sign up the site\n")
