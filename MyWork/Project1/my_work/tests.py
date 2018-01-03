# class Test:
   
#     def __call__(self,*args,**kwargs):
#         print(args,kwargs)

# t = Test()
# t(1,2,3,4, thimma="krish")

class Test2:
    def __init__(self):
        pass

    def calling(self):
        return 42
    def called(self):
        return self.calling()

print(Test2().called())