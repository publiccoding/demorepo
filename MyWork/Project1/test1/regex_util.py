
# for i in range(10):
#     print(i)
#     if i == 5:
#         break

# else:
#     print("this will print")

# try : 
#     f =open('data.txt') 
#     #var = bar_var
# except FileNotFoundError:
#     print("File not found excetion")
# except Exception:
#     print("Exception arravied unable to access file")
# else:
#     print(f.read())
# finally:
#     f.close()

# import random 
# value = random.uniform(1,5)
# print(value)

# result = random.randint(1,10)
# print(result)

# l = ['l','b','c','m']

# val = random.choices(l, weights=[24,24,15,3], k=10 )
# print(val)

# shuf = random.shuffle(l)
# print(l)


# sam = random.sample(l, k=3)
# print(sam)



#Regular expression

import re 

import time


text_search ='''
abcdefghifslkfjadfklj
ABCDAFDGEARAWEGGAFASDF
1243412798571934719278341
thimma.com
thimma@gmail.com
thimmrayan@hpe.com
thimm.rayan@hpe.com
thimma-rayan@hpe.com
thimma-rayan@hpe-co.in 

https://www.thimmarayan.com
http://www.gmail.com 
http://thimmarayan.com 
https://youtube.com 
http://www.gmail.co.in

Ha HaHa
234-424-2145
765*876-4321
456.908.6574
800-876-4321
900.908.6574


Mr. Scrahf
Ms Davis
Mrs. Robinson
Mr. T
Mr Smith

mat 
bat
cat 
pat
'''

fake_name='''
Dave Martin
643-555-7654
173 Main St., Springfield RI 78907
davemarting@bogusemail.com

Charles Harris
800-555-5668
987 High St., Alantis VA 34075
charlesharris@bogusemail.com
'''
urls='''
https://www.thimmarayan.com
http://www.gmail.com 
http://thimmarayan.com 
https://youtube.com 
http://www.gmail.co.in
'''

sentence = 'Start a sentence and then bring it to an end'

#patter = re.compile(r'[89]00[-.]\d{3}[-.]\d{4}')
#patter = re.compile(r'\d{3}.\d{3}.\d{4}')
#patter = re.compile(r'(M(r|s|rs))\.?\s([A-Z]\w*)')
#patter = re.compile(r'[a-zA-Z.-]+@[a-zA-Z-]+\.\w{2,3}')
#patter = re.compile(r'https?://(www\.)?(\w+)(\.[\w.-]+)')
#patter = re.compile(r'start', re.I)
#sub_url= patter.sub(r'\2\3',urls)
#print(sub_url)
#matches = patter.finditer(text_search) 
#matches = patter.findall(text_search)
#matches = patter.search(sentence) 
# matches = patter.match(sentence) 
# print(matches)

# for match in matches:
#     print(match)

#CSV FILE OPERATION 

import csv 

# with open('name.csv', 'r') as csv_file:
#     csv_reader = csv.DictReader(csv_file, delimiter='\t')

#     with open('names.csv', 'w') as new_dict:
#         fieldname = ['Name','Operation']
 
#         csv_writer = csv.DictWriter(new_dict, fieldnames=fieldname, delimiter='=')
#         csv_writer.writeheader()
#         for line in csv_reader:
#             del line['Status']
#             csv_writer.writerow(line)


# with open('name.csv', 'r') as csv_file:
#     csv_reader = csv.reader(csv_file)
#     with open('names.csv', 'w') as csv_write:
#         csv_writer = csv.writer(csv_write, delimiter='\t')
#     #next(csv_reader)
#         for line in csv_reader:
#             csv_writer.writerow(line)


