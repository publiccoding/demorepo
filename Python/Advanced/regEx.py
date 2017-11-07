import re

theStr = " Cate rataa pat bat mat Rat the ape was rate at apee the apex"
# for i in re.findall("[CrmR]at",theStr):
#      print(i)
#
# regex = re.compile("[Crp]at")
# owlFood = regex.sub("own", theStr)
# print(owlFood)

matchresult = re.match(r'Cat+', theStr)
if matchresult:
    print("Match found "+matchresult.group())
else:
    print("No Match found")

# randStr = "Here is \\stuff"
# print("Find \\stufff :", re.search("\\\\stuff",randStr))

#randstr ="F.B.I. I.R.S. CIA"
#print("Matches:", len(re.findall(".\..\..\.",randstr)))

# randstr = "@ Get this string"

# regex = re.compile(r"[^@\s].*$")
# matches = re.findall(regex,randstr)

