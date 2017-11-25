import smtplib
from  module import userRegistration


class sendEmailOpration:

    def __init__(self):
        self.server = smtplib.SMTP ('smtp.gmail.com', 587 )
        self.server.starttls ()
        self.server.login ( 'thimmarayan.krishnappa@gmail.com', 'Lakrthkuv@1' )
        self.userdata = userRegistration.userRegistration.getValue ()

    def emailPassword(self, email):

        #data = userRegistration.userRegistration.getValue()
        for pwd in self.userdata.values():
            if email == pwd ["email"]:
                password = pwd["pwd"]

        FROM = "thimmarayan.krishnappa@gmail.com"
        TO = email
        SUBJECT = "Your password is sent with this email"
        TEXT = "Your passwor is :"+password+" Please try login again "
        message ="""
        From : %s
        To : %s 
        Subject : %s
        %s
        """ % (FROM,TO,SUBJECT,TEXT)

        self.server.sendmail(FROM,TO,message)
        self.server.quit()

    def emailBalance(self):
        pass
    def emailwithdraw(self):
        pass
    def emailDeposit(self):
        pass