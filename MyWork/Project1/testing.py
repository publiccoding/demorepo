
import subprocess
import logging
import os
import shutil
import re
import datetime


import test1

def thiMethod():
    print("testing.py")
    valu=test1.addprint()
    print(valu)

#test1.test.addprint(test1.test)

thiMethod()
# def configureBootLoader():
#
#     out = "kernel-default-base-3.0.101-68.1 kernel-default-base-3.0.101-107.1"
#     print(out)
#     out = out.strip()
#     kernelList = out.split()
#     print(kernelList)
#
#     try:
#         with open(r"C:\Users\kristhim\Desktop\mybackup\bootloader") as f:
#             print("printing bootloader",f)
#             print("\n\n")
#             for line in f:
#                 print("print each line",line)
#                 if 'LOADER_TYPE' in line:
#                     loader = re.match('^.*="\\s*([a-zA-Z]+)".*', line).group(1)
#                     print("loder before lowercase",loader)
#                     loader = loader.lower()
#                     print("loader after lower case",loader)
#                     break
#
#     except IOError as err:
#         print("Error")
#
#
#     if loader == 'grub':
#         configureGrubBootLoader(kernelList)
#     else:
#         configureEliloBootLoader(kernelList)
#
# def configureGrubBootLoader(kernelList):
#     pass
#
# def configureEliloBootLoader(kernelList):
#
#     out ="3.0.101-107-default"
#     currentKernel = out.strip ()
#     currentKernel = 'vmlinuz-' + currentKernel
#     kernelVersionList = []
#     for kernelPackage in kernelList:
#         print("printing kernelpackage",kernelPackage)
#         kernelVersionList.append ( re.match ( '([a-z]+-){1,4}(.*)', kernelPackage ).group ( 2 ) )
#
#     print("Priniting Kernel version list",kernelVersionList)
#     finalKernelList = kernelSort(kernelVersionList)
#     print("Final kernel version list is determined to be",finalKernelList)
#     vmlinuzList = []
#     initrdList = []
#     print("final kernel version list",finalKernelList)
#     for kernelVersion in finalKernelList:
#         print("kernelversion list before",kernelVersion)
#         print ( "kernelversion list after", kernelVersion[:-1] )
#         kernelVersion = kernelVersion[:-2]
#         print ("kernelversion list after", kernelVersion )
#         vmlinuzList.append ( 'vmlinuz-' + kernelVersion + '-default' )
#         initrdList.append ( 'initrd-' + kernelVersion + '-default' )
#
#     print('The kernel list was determined to be: ' + str ( vmlinuzList ) )
#     print('The initrd list was determined to be: ' + str ( initrdList ) )
#     bootloaderConfig = ['timeout = 150', 'secure-boot = on', 'prompt']
#     failsafeResources = 'ide=nodma apm=off noresume edd=off powersaved=off nohz=off highres=off processsor.max+cstate=1 nomodeset x11failsafe'
#     print("Curren kernel is",currentKernel)
#     try:
#
#         f = open (r"C:\Users\kristhim\Desktop\bootloader", 'r' )
#         eliloConfData = f.readlines ()
#         f.close ()
#     except IOError as err:
#         print("error",err)
#     kernelPresent = 'no'
#     #print(eliloConfData)
#     for line in eliloConfData:
#         if 'image' in line and currentKernel in line:
#             kernelPresent = 'yes'
#
#     if kernelPresent == 'no':
#         currentKernel = 'vmlinuz'
#     print( 'The current kernel reference in elilo.conf was determined to be: ' + currentKernel )
#     currentKernelPattern = re.compile ( currentKernel + '\\s*$' )
#     for line in eliloConfData:
#         #print("inside the eliloconf Data file",line)
#         line = line.strip ()
#         if 'root' in line and 'append' not in line:
#             root = re.sub ( ' +', ' ', line )
#             print("ROOT",root)
#         elif 'append' in line and 'noresume' not in line:
#             append = re.sub ( ' +', ' ', line )
#             append = re.sub ( '" ', '"', append )
#             append = re.sub ( ' "$', '"', append )
#             failsafeAppend = re.sub ( 'resume=(/[a-z0-9-_]*)+\\s+', failsafeResources + ' ', append )
#             failsafeAppendList = failsafeAppend.split ()
#             tmpList = []
#             objects = set ()
#             for object in failsafeAppendList:
#                 if object not in objects:
#                     tmpList.append ( object )
#                     objects.add ( object )
#
#             failsafeAppend = ' '.join ( tmpList )
#         # try:
#         #     if root and append:
#         #         break
#         # except NameError:
#         #     pass
#
#     print('append has been determined to be: ' + append)
#     print('failsafeAppend has been determined to be: ' + failsafeAppend)
# #     for i in range ( len ( vmlinuzList ) ):
# #         bootloaderConfig.append ( '' )
# #         bootloaderConfig.append ( '' )
# #         bootloaderConfig.append ( 'image = /boot/' + vmlinuzList[i] )
# #         bootloaderConfig.append ( '\tlabel = Linux_' + str ( i + 1 ) )
# #         bootloaderConfig.append ( '\tdescription = "SAP HANA kernel(' + vmlinuzList[i] + ')"' )
# #         bootloaderConfig.append ( '\t' + append )
# #         bootloaderConfig.append ( '\tinitrd = /boot/' + initrdList[i] )
# #         bootloaderConfig.append ( '\t' + root )
# #         bootloaderConfig.append ( '' )
# #         bootloaderConfig.append ( 'image = /boot/' + vmlinuzList[i] )
# #         bootloaderConfig.append ( '\tlabel = Linux_Failsafe_' + str ( i + 1 ) )
# #         bootloaderConfig.append ( '\tdescription = "Failsafe SAP HANA kernel(' + vmlinuzList[i] + ')"' )
# #         bootloaderConfig.append ( '\t' + failsafeAppend )
# #         bootloaderConfig.append ( '\tinitrd = /boot/' + initrdList[i] )
# #         bootloaderConfig.append ( '\t' + root )
# #
# #     print( 'The final elilo bootloader configuration was determined to be: ' + str ( bootloaderConfig ) )
# #     try:
# #         f = open ( '/etc/elilo.conf', 'w' )
# #         for item in bootloaderConfig:
# #             f.write ( item + '\n' )
# #
# #     except IOError as err:
# #         print("error")
# #     f.close ()
# #
#
#
#
# def kernelSort(verList):
#     versionList = []
#     revisionList = []
#     finalVersionList = verList
#     print("finalversion list",finalVersionList)
#     print("inside kernelsort",verList)
#     for ver in verList:
#         print("inside FOR loop ver",ver)
#         version, revision = re.split('-', ver)
#         print(version+" and"+revision)
#         versionList.append(re.sub('\\.', '', version))
#         revisionList.append(re.sub('\\.', '', revision))
#
#     print(versionList)
#     print(revisionList)
#
#     # versionList = map(int, versionList)
#     # revisionList = map(int, revisionList)
#     print("length of the version list is ",versionList)
#     #print(revisionList)
#     for j in range(len(versionList)):
#         print("print the j value",j)
#         for i in range(j + 1, len(versionList)):
#             print("print the i value",i)
#             #print(versionList[i],versionList[j])
#             if versionList[i] > versionList[j] or versionList[i] == versionList[j] and revisionList[i] > revisionList[j]:
#                 versionList[i], versionList[j] = versionList[j], versionList[i]
#                 print("print the version list"+versionList[i], versionList[j])
#                 revisionList[i], revisionList[j] = revisionList[j], revisionList[i]
#                 print("print the version list"+revisionList[i], revisionList[j])
#                 finalVersionList[i], finalVersionList[j] = finalVersionList[j], finalVersionList[i]
#                 print(finalVersionList[i])
#                 print(finalVersionList[j])
#     print("final versino list",finalVersionList)
#     del finalVersionList[2:]
#     return finalVersionList
#
# configureBootLoader()