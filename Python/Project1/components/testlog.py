#import tools
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fmt=logging.Formatter('%(asctime)s:%(name)s:%(message)s')
file_handler = logging.FileHandler('sample.log')
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(fmt)
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)
#format = "%(asctime)s [%(name)s] %(message)s"
#logging.basicConfig(filename='sample.log',format = format,level=logging.DEBUG)

#critical - 50
#error - 40
#warnig - 30
#info - 20
#debug - 10 

class Item(object):
         """ Base item class """
         
 
         def __init__(self, name , value):
            self.name = name
            self.value = value
 
         def buy(self, quantity=1):
             
             """ Buys item """
             logger.debug("Bought item {}".format(self.name))
             try:
                 result = 7/0
             except ZeroDivisionError:
                 logger.exception('Tried to divide by zero')
             else:
                 return result
         def sell(self, quantity=1):
             """ Sells item"""
             logger.debug("sold item {}".format(self.name))

			 
item_01 = Item('sword',50)
item_01.buy()
item_01.sell()
			 
			 
    
