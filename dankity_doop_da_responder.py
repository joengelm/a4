import getpass
from mailbot import MailBot, register, Callback
from email.utils import parsedate
import too_lurnt_up_machine
from sklearn.externals import joblib
import pickle
import time
from datetime import datetime
import smtplib
import os
import math

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

avg_response_times = pickle.load(open( "art.pkl", "rb" ))

def features_for_email(email):
    if not email['Date']:
        print 'no date'
        return None
    d = datetime.fromtimestamp(email['Date'])
    
    day_of_week = d.weekday()
    time_of_day = d.hour + d.minute / 60. + d.second / 3600.
    time_of_day = time_of_day + 18. if time_of_day < 6. else time_of_day - 6.
    time_of_day = -time_of_day
    num_recipients = len(email['To']) + len(email['Cc'])
    length_of_body = len(email['Body'])
    sent_time = float(email['Date'])
    
    avg_res_time = 24.0
    if email['From'] in avg_response_times:
        avg_res_time = avg_response_times[email['From']]
    features = [avg_res_time, num_recipients, day_of_week, time_of_day, length_of_body, sent_time]
    return features


def send_email(address, time, reply=None):
    # me == my email address
    # you == recipient's email address
    me = 'joseph_engelman@brown.edu'

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Automated Response"
    msg['From'] = me
    msg['To'] = address

    if reply:
        msg["In-Reply-To"] = reply
        msg["References"] = reply

    warn = ""
    if time > 18:
        warn = "Joe is facing unusually high levels of work today. He'll make an effort to respond as soon as he gets a chance."
    elif time > 6:
        warn = "Joe is moderately "

    # Create the body of the message (a plain-text and an HTML version).
    text = "Hi there! This is an automatically generated response from one of Joe's machine learning projects. Based on the characteristics your email, Joe's predicted response time is about  " + str(time) + " hours."
    html = """\
    <html>
      <head>
        <style>
            p {
                font-size: 14px;
            } 
            .center {
                margin: auto;
                text-align: center;
            }
        </style>
      </head>
      <body>
        <h2 class="center">Hi there!</h2>
        <p>""" + warn + """</p>
        <p>Based on the characteristics your email, Joe's predicted response time is about <strong>""" + str(time) + """ hours</strong>.</p>
        <br />
        <img src='http://66.media.tumblr.com/tumblr_lzt1e1bs6A1rn95k2o1_500.gif'/>
        <p><em>This is an automatically generated response from one of Joe's machine learning projects.</em></p>
      </body>
    </html>
    """

    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)

    s = smtplib.SMTP("smtp.gmail.com", 587)
    s.starttls()
    s.login(os.environ['GMAIL_USER'], os.environ['GMAIL_PASS'])

    # sendmail function takes 3 arguments: sender's address, recipient's address
    # and message to send - here it is sent as one string.
    print(s.sendmail(me, address, msg.as_string()))
    s.quit()


class Autoresponder(Callback):

    def trigger(self):
        try:
            print "Processing email from:", self.message['From']
            e = {}
            e['From'] = [t.lower() for t in self.message['From'].strip().split(' ') if t.strip() != '' and t[0] == '<'] if 'From' in self.message else []
            e['From'] = e['From'][0]
            e['To'] =  [t.lower() for t in self.message['To'].strip().split(' ') if t.strip() != ''] if 'To' in self.message else []
            e['Cc'] =  [t.lower() for t in self.message['Cc'].strip().split(' ') if t.strip() != ''] if 'Cc' in self.message else []

            d_ = parsedate(self.message['Date'].strip())
            e['Date'] = time.mktime(d_) if d_ else None

            e['Body'] = self.get_email_body()

            f = features_for_email(e)

            est = lr.predict(f)[0]
            est = int(math.ceil(est))

            if "<joseph_engelman@brown.edu>" in e['To'] or "joseph_engelman@brown.edu" in e['To']:
                if est > 2 and est < 168:
                    print "Sending email for " + str(est) + " hour estimate to " + e['From']
                    send_email(e['From'], est, reply=self.message['Message-ID'])
                else:
                    print "Did not send email for " + str(est) + " hour estimate to " + e['From']
            else:
                print "Did not respond to " + e['From'] + " because the message was not directed to me"
        except:
            print "Error occurred - aborting..."


mailbot = MailBot('imap.gmail.com', os.environ['GMAIL_USER'], os.environ['GMAIL_PASS'], port=993, ssl=True)

lr = joblib.load('lr.pkl')

# register your callback
register(Autoresponder)

print "Processing new messages..."
# check the unprocessed messages and trigger the callback
mailbot.process_messages()
