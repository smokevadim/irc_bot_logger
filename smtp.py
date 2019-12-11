# -*- coding: utf-8 -*-
from vars import *
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_mail(subject, body):
    """
    Function to send email message
    """
    if (not EMAIL_PASSWORD) or (not EMAIL_SERVER) or (not ADDR_FROM) or (not ADDR_TO):
        return
    msg = MIMEMultipart()
    msg['From'] = ADDR_FROM
    msg['To'] = ADDR_TO
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(EMAIL_SERVER, 587)
    #server.set_debuglevel(True)
    server.starttls()
    server.login(ADDR_FROM, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()