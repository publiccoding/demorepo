import optparse


def main():

    usage = 'usage: %prog [[-a] [-k] [-o] -d] [-h]'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-a', action='store_true', default=False,
                      help='This option will result in the application of both OS and Kernel security patches.')
    parser.add_option('-d', action='store_true', default=False,
                  help='This option is used when problems are encountered and additional debug information is needed.')
    parser.add_option('-k', action='store_true', default=False,
                  help='This option will result in the application of Kernel security patches.')
    parser.add_option('-o', action='store_true', default=False,
                  help='This option will result in the application of OS security patches.')
    (options, args) = parser.parse_args()
    if (options.a):
        print(" All Option called")
    elif (options.k):
        print(" Only Kernel patch update called ")
    elif (options.o):
        print("Security Patch update called")
    else:
        print("Option not provided")

if __name__ == '__main__':
    main()



