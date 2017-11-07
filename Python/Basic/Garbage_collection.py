# import weakref, gc
#
#
# class A:
#     def __init__(self, value):
#         self.value = value
#
#     def __repr__(self):
#         return str(self.value)
#
#
# a = A(10)
# d = weakref.WeakValueDictionary()
# d['primary'] = a
#
# print(d['primary'])
# del a
# gc.collect()
# print(d['primary'])

#
# import tempfile
# import subprocess
#
#
# def UpdagteZypp():
#     result = True
#     script = '''print("This value and")
#     print("another value")
#     '''
#
#     try:
#         with tempfile.NamedTemporaryFile() as updatefile:
#             updatefile.write()
# def UpdateZypp():
#     result = True
#     script=''' ls -l /tmp/
#
#     cp /root/thimma/out /tmp/
#
#     '''
#
#     try:
#
#         with tempfile.NamedTemporaryFile() as updateZyppConfScript:
#                 updateZyppConfScript.write(script)
#                 updateZyppConfScript.flush()
#             returnCode = subprocess.call(['/bin/bash',updateZyppConfScript.name])
#     except OSError:
#         print("ERROR OCCURED")

