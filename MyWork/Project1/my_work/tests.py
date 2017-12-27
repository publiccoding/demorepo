class Test:
   
    def __call__(self,*args,**kwargs):
        print(args,kwargs)

t = Test()
t(1,2,3,4, thimma="krish")
