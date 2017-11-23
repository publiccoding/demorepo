
# Python code to illustrate Sending mail from
# your Gmail account
import smtplib
# creates SMTP session
s=smtplib.SMTP('smtp.gmail.com',587)
#s.ehlo()
# start TLS for security
s.starttls()
# Authentication
s.login("thimmarayan.krishnappa@gmail.com", "Lakrthkuv@1")
# message to be sent
FROM = input("Enter your email ID")
TO =[]
TO.append(input("Enter receiver email ID"))
subject = "Hello Test email using python"
text = "This was sent using python email SMTP method"
message = """\
From: %s
To: %s
Subject: %s
%s 
""" % (FROM, ", ".join(TO), subject, text)

# sending the mail
s.sendmail(FROM, TO, message)

# terminating the session
s.quit()