from contextlib import contextmanager

# print(len(data))
# print(f.close())

# class mywith():

#     def __init__(self, name, mode):
#         self.name = name 
#         self.mode = mode

#     def __enter__(self):
#         self.file = open(self.name, self.mode)
#         return self.file

#     def __exit__(self, exc_type, exc_value, traceback):
#         if self.file:
#             self.file.close()

    
# with mywith('tests.py', 'r') as f:
#     data = f.read()

# print(data)

# @contextmanager
# def mywithfunc(name, mode):
#     try :
#         file = open(name, mode)
#         yield file
#     except Exception as e:
#         print(e)
#         raise FileNotFoundError("File is not present")
#     finally :
#         file.close()

# with mywithfunc('tests.py','r') as f:
#     data = f.read()
#f.close()
#print(data)

# Couroutine in python 


# def Coroutine():
    
#     count = 0
#     avg = 0
#     val = 0
#     while True:
#         data = yield avg
#         count += 1
#         val = data + val 
#         avg = val / count
#         #print(val)
   
        
# mycor = Coroutine()
# next(mycor)
# mycor.send(40)
# mycor.send(50)
# mycor.send(30)

