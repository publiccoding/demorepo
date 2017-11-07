# class Time:
#     def __init__(self,hour=0,minute=0,second=0):
#         self.hour = hour
#         self.minute = minute
#         self.second = second
#     def __str__(self):
#         return "{}:{:02d}:{:02d}".format(self.hour,self.minute,self.second)
#
#
#     def __add__(self, other_time):
#
#         new_time = Time()
#
#         # Add the second and correct if sum >= 60
#         if (self.second + other_time.second) >= 60 :
#             self.minute +=1
#             new_time.second = (self.second + other_time.second) - 60
#         else:
#             new_time.second = self.second + other_time.second
#         # Add the minute and correct if minute is > 60
#         if (self.minute + other_time.minute) >= 60:
#             self.hour += 1
#             new_time.minute = (self.minute + other_time.minute) - 60
#         else:
#             new_time.minute = self.minute + other_time.minute
#
#         # Add the hours and correct if hours is > 24
#
#         if (self.hour + other_time.hour) >= 24:
#
#             new_time.hour = (self.hour + other_time.hour) - 24
#         else:
#             new_time.hour = self.hour - other_time.hour
#         return  new_time
#
#
# def main():
#     time = Time(1,20,30)
#     print(time)
#     time2 = Time(24,41,20)
#     print(time + time2)
#
# main()
#


#Call method

class Accumulator:
    def __init__(self):
        self.value = 0

    def __call__(self, v=None):
        if v:
            self.value +=v
        else:
            return self.value

a = Accumulator()
a(10)
a(20)
a(30)
print(a())