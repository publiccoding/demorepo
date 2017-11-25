

def acc_test():

    print(accountNumber())


def accountNumber(self):
    acc_no = (x for x in range ( 1000, 9999 ))
    return acc_no.__next__ ()


acc_test()