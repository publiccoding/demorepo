import logging 

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fmt=logging.Formatter('%(asctime)s:[%(levelname)s]:%(name)s:%(message)s')
file_handler = logging.FileHandler('example.log')
file_handler.setFormatter(fmt)
logger.addHandler(file_handler)


#logging.basicConfig(format=fmt, filename='example.log',level=logging.INFO)

class Log(object):
	
    def __init__(self,name):

        self.a_name=name
        logger.info(" Constructer for log class initiated {}".format(self.a_name))

    def Getter(self):

        logger.warning("value is assinged  {}".format(self.a_name))

        logger.error("this value is not printed")

        return self.a_name
        
    def Settter(self, name):


        self.a_name=name
        logger.debug(" values is assingned  {}".format(self.a_name))
	
log = Log("thimma")
log1 = Log('rayan')

log.Settter(45)
	
t=log.Getter()
print(t)
