text =\
'''Filesystem                    1K-blocks    Used Available Use% Mounted on
/dev/mapper/vg_redhat-lv_root   6926264 2970112   3604308  46% /
tmpfs                            510172      72    510100   1% /dev/shm
/dev/sda1                        495844   34854    435390   8% /boot
'''

import re

match = re.match('(.*\s)',text).group()
print(match)

#tmpVar = re.match('(.*\s+){3}([0-9]+)\s+', out).group(2)

# allApes = re.finditer("ape.", "The ape was at the apex")
# for i in allApes:
#     localtup = i.span()
#     print(localtup)
#     print(i)
# animalStr = "Cat rat mat pat"
# someAnimals = re.findall("[c-mC-M]at", animalStr)

## RegEx Substitution method.

# owlFood = "rate catjkl sat fat mat pat"
# owf = re.sub('[cr]at',"owl", owlFood)
# print(owf)




### Using raw String format

# randStr = "Here is \\stuff"
# print("Find \\stuff:", re.search(r"\\stuff", randStr))

### Sustitution method

# randStr = '''This is a long
# string that goes
# on for many lines
# '''
# randStr = re.sub("\n"," ",randStr)
# print(randStr)

# \b : Backspace
# \f : Form Feed
# \r : Carriage Return
# \t : Tab
# \v : Vertical Tab

#\r\n

#\d : [0-9]
#\D : [^0-9]



# randStr = "12345, 122 , 8908"
# print("Matches :", len(re.findall("(\d){4}",randStr)))
#

# \w : [a-zA-Z0-9_]
# \W : [^a-zA-Z0-9_]

# phNum = "412-555-1221, ahjbse-435-3432"
# match=re.search("\d{3}-\d{3}-\d{4}", phNum)
# print(match)

# emailList ="yar+an@fsld.fnd f sd%fl@sk.dfs d-b@ao-l.com, m@.com, @apple.com, db@.com thimma@ryana-krish.com"
# email = re.findall("[\w.%+-]{1,20}@[\w.-]{2,20}\.[A-Za-z]{2,3}", emailList)
# print(email)

#[] : Match what is in the brackets
#[^] : Match anything not in the brackets
#.  : Match any 1 character or space
#+ : Match 1 or more of what proceeds
#\n : Newline
#\d : Any 1 Number
#\D : Anything but a number
#\w : Same as [



# emails = ["john@example.com", "python-list@python.org", "wha.t.`1an?ug{}ly@email.com"]
#
# strings="john@example.com, python-list@python.org, wha.t.`1an?ug{}ly@email.com"
# for email in emails:
#     if re.search( "[\w].*[._-]?[\w]+@[\w]+\.[a-zA-Z]{2,3}", email ):
#         print("found")
























