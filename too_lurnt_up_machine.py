import csv
import sys
import time
from email.utils import parsedate
from collections import defaultdict
from datetime import datetime
from sklearn.linear_model import LinearRegression 
from sklearn import cross_validation

csv.field_size_limit(sys.maxsize)

avg_response_times = {}

def get_emails_from_file(email_file):
    reader = csv.DictReader(email_file, delimiter='\t')
    emails_converted = {}
    for line in reader:
        e = {}
        e['ID'] = line['Message-ID']
        e['From'] = line['From'].strip()
        e['To'] = [t for t in line['To'].strip().split(' ') if t.strip() != '']
        e['Cc'] = [c for c in line['Cc'].strip().split(' ') if c.strip() != '']
        e['Subject'] = line['Subject'].strip()
        e['In-Reply-To'] = line['In-Reply-To'].strip()
        d = parsedate(line['Date'].strip())
        e['Date'] = time.mktime(d) if d else None
        e['Body'] = line['Body'].strip()
        emails_converted[line['Message-ID']] = e
    return emails_converted


def label_for_email(email, emails):
    if 'Followed-By' not in email:
        return None
    idx = email['Followed-By']
    if idx in emails:
        if emails[idx]['From'] != 'joseph_engelman@brown.edu':
            return None
        t = (emails[idx]['Date'] - email['Date']) / 3600. # convert to hours
        if t < 0:
            t = -t
        return t
    else:
        return None


def get_avg_response_times(emails):
    response_times = defaultdict(list)
    for email in emails:
        time = label_for_email(email, emails)
        if not time:
            continue
        response_times[email['From']].append(time)
    for sender in response_times:
        avg = float(sum(response_times[sender])) / float(len(response_times[sender]))
        avg_response_times[sender] = avg
    return avg_response_times


def features_for_email(email):
    if not email['Date']:
        return None
    d = datetime.fromtimestamp(email['Date'])
    
    day_of_week = d.weekday()
    time_of_day = d.hour + d.minute / 60. + d.second / 3600.
    time_of_day = time_of_day + 18. if time_of_day < 6. else time_of_day - 6.
    time_of_day = -time_of_day
    num_recipients = len(email['To']) + len(email['Cc'])
    length_of_body = len(email['Body'])
    sent_time = float(email['Date'])
    
    if email['From'] not in avg_response_times:
        return None
    features = [avg_response_times[email['From']], num_recipients, day_of_week, time_of_day, length_of_body, sent_time]
    return features


def get_model():
    emails = {}
    with open('emails.tsv', 'r') as f:
        emails = get_emails_from_file(f)
        response_emails = []
        for id in emails:
            e = emails[id]
            if e['From'] == 'joseph_engelman@brown.edu' and e['In-Reply-To'] != '':
                response_emails.append(e)
            idx = e['In-Reply-To']
            if idx != '' and idx in emails:
                emails[idx]['Followed-By'] = id


    avg_response_times = get_avg_response_times(emails.values())
    print avg_response_times

    labeled_samples = []

    for e in emails.values():
        if e['From'] == 'joseph_engelman@brown.edu':
            continue
        features = features_for_email(e)
        if not features:
            continue
        
        label = label_for_email(e)
        if label:
            labeled_samples.append((features, label))

    labeled_samples.sort(key=lambda sample: sample[0][5])
    X = [ls[0] for ls in labeled_samples]
    y = [ls[1] for ls in labeled_samples]
    length = len(y)
    weights = [i/float(length) for i in range(0,length)]


    lr = LinearRegression() 
    lr.fit(X, y, weights) 
    return lr
    #lrScores = cross_validation.cross_val_score(lr, X, y) 

    #print lrScores 
    #print("Accuracy: %0.2f (+/- %0.2f)" % (lrScores.mean(), lrScores.std() * 2))


