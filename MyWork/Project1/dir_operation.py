import os
import re
import random
import pickle
import json

# Find the file which is more than 5MB and check if any file with .pyc_dis then rename it .py and remove the pyc files

# file_size = {}
# path_start =r"C:\Users\kristhim\Desktop\thimma 01302017\programming\Practice\demorepo"
# for paths, dirs, files in os.walk(path_start):
#         if os.path.exists(paths):
#             files=os.listdir(os.chdir(paths))
#             for f in files:
#                 if os.path.isfile(f) and (os.stat(f).st_size/1024/1024) > 5:
#                     file_size[paths]=f
#                 elif f.endswith("pyc_dis"):
#                     os.rename(f , "{}.py".format(f.split('.')[0]))
#                 elif f.endswith("pyc"):
#                     print(f)
#                     os.remove(f)
#
#
# for path, file in file_size.items():
#     print(path,file)

# this method stores the user data in text file in  String format.

# data_final = {}
# data_dic = {}
# name = input ("Enter your name")
# pwd = input ("Enter your password")
# email = input ("Enter your email id")
#
# data_dic["name"] = name
# data_dic["pwd"] = pwd
# data_final[email] = data_dic
#
# with open ( r"C:\Users\kristhim\Desktop\thimma 01302017\programming\Practice\demorepo\MyWork\Project1\testdb.txt",
#             "a" ) as test_db:
#     test_db.write(str(data_final))
#     test_db.write('\n')

import ast

username = input("Enter your username")

with open(r"C:\Users\kristhim\Desktop\thimma 01302017\programming\Practice\demorepo\MyWork\Project1\testdb.txt",
            "r") as read_db:
    for line in read_db:
        line=ast.literal_eval(line)
        if username in line.keys():
            for p in line.values():
                print(p['pwd'])


                    # if username in line.keys ():
                    #     print ( line )
                    #     pwd = input ( "Enter Password" )
                    #     print ( line.values () )
                    #     for d in line.values ():
                    #         if d['pwd'] == pwd:
                    #             print ( "Your Logged in successfully" )


                                # import os
    # import signal
    #
    #
    # def signal_handler(signum,frame):
    #     regex = r"^(y|n)$"
    #
    #     print("\nThe update should not be interrupted once started, since it could put the system in an unknown state.\n")
    #
    #     while True:
    #         response = input( "Do you really want to interrupt the update [y|n]: " )
    #
    #         if not re.match( regex, response ):
    #             print("A valid response is y|n.  Please try again.")
    #
    #             continue
    #         elif (response == 'y'):
    #             exit( 1 )
    #         else:
    #             return
    #
    #
    # # End signal_handler(signum, frame):
    #
    # signal_handler()


# username =
# password =
# email_id =
# address =
# phone =
# account_no=
# pan_id =