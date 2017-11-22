import os
import re
# path =r"C:\Users\kristhim\Desktop\patch\modules"
#
# files=os.listdir(os.chdir(path))
# for f in files:
#
#     if f.endswith("pyc_dis"):
#         os.rename(f , "{}.py".format(f.split('.')[0]))
#     elif f.endswith("pyc"):
#         os.remove(f)
# print("File not found with above extension")



import os
import signal


def signal_handler(signum,frame):
    regex = r"^(y|n)$"

    print("\nThe update should not be interrupted once started, since it could put the system in an unknown state.\n")

    while True:
        response = input( "Do you really want to interrupt the update [y|n]: " )

        if not re.match( regex, response ):
            print("A valid response is y|n.  Please try again.")

            continue
        elif (response == 'y'):
            exit( 1 )
        else:
            return


# End signal_handler(signum, frame):

signal_handler()