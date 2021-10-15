from __future__ import print_function
import datetime
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os
import pwd
import sys
import email
import datetime

userDir = pwd.getpwuid( os.getuid() )[ 0 ]

sys.path.insert(0, f'/home/{userDir}/Git/Tools')
sys.path.insert(0, f'/home/{userDir}/Git/SecureData')

import mail
import secureData


data = mail.check()

# Get Reservation Email
def getBody():
    global results_checkout
    global email_subject
    global results_address

    for response_part in data:
        arr = response_part[0]
        if isinstance(arr, tuple):
            msg = email.message_from_string(str(arr[1],'utf-8'))
            email_subject = msg['subject']

            if "Confirmed Reservation: Check-in" in email_subject:
                # if the email message is multipart
                if msg.is_multipart():
                    # iterate over email parts
                    for part in msg.walk():
                        # extract content type of email
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        try:
                            # get the email body
                            results_body = part.get_payload(decode=True).decode()
                        except:
                            pass
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            # return text/plain emails and skip attachments
                            return results_body
                        elif "attachment" in content_disposition:
                            # download attachment
                            filename = part.get_filename()
                            if filename:
                                folder_name = "".join(c if c.isalnum() else "_" for c in email_subject)
                                if not os.path.isdir(folder_name):
                                    # make a folder for this email (named after the subject)
                                    os.mkdir(folder_name)
                                filepath = os.path.join(folder_name, filename)
                                # download attachment and save it
                                open(filepath, "wb").write(part.get_payload(decode=True))
                else:
                    # extract content type of email
                    content_type = msg.get_content_type()
                    # get the email body
                    results_body = msg.get_payload(decode=True).decode()
                    if content_type == "text/plain":
                        # return only text email parts
                        return results_body

def calendar():
    SCOPES = ['https://www.googleapis.com/auth/calendar']

    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                        maxResults=10, singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
        print('Creating a test event')


        # test event
        event = {
            'summary': 'Google I/O 2022',
            'location': '800 Howard St., San Francisco, CA 94103',
            'description': 'A chance to hear more about Google\'s developer products.',
            'start': {
                'dateTime': '2022-05-28T09:00:00-07:00',
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': '2022-05-28T17:00:00-07:00',
                'timeZone': 'America/Los_Angeles',
            },
            'recurrence': [
                'RRULE:FREQ=DAILY;COUNT=2'
            ],
            'attendees': [
                {'email': 'lpage@example.com'},
                {'email': 'sbrin@example.com'},
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }
        service.events().insert(calendarId='primary',body=event).execute()
        print(f"Event created: {event.get('htmlLink')}")
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])

def main():
    # parse body
    results_body = getBody()

    # assumes date in email is in format like: Dec 9, 2021
    if(results_body): 
        if('Check-Out:' in results_body):
            if(len(results_body.split('Check-Out:')[1].split('\n')[0].strip())):
                results_checkout = results_body.split('Check-Out:')[1].split('\n')[0].strip()
            elif(len(results_body.split('Check-Out:')[1].split('\n')[1].strip())):
                results_checkout = results_body.split('Check-Out:')[1].split('\n')[1].strip()
            else:
                secureData.log("Checked for Evolve reservations - found one but couldn't parse check-out date")
                quit()
            
            results_cleaning_date = (datetime.datetime.strptime(results_checkout, "%b %d, %Y") + datetime.timedelta(days=1))
            results_cleaning_date_string = results_cleaning_date.strftime('%B %-d')
            results_cleaning_date_string_log = results_cleaning_date.strftime('%Y-%m-%d')
            
            # parse address
            if(' at ' in email_subject):
                results_address = email_subject.split(' at ')[1].split(', ')[0]

            if(results_cleaning_date_string and results_address):
                email = f"""Hi,\n\nCould you please schedule a cleaning again at {results_address} at any time on {results_cleaning_date_string}?"""

            # send email
            if(results_cleaning_date_string_log not in secureData.file('AIRBNB_CHECKOUT_LOG')):
                secureData.appendUnique("AIRBNB_CHECKOUT_LOG", results_cleaning_date.strftime('%Y-%m-%d'))
                mail.send(f"Cleaning Request, {results_cleaning_date_string}", email, secureData.variable("AIRBNB_CLEANER_EMAIL_SIGNATURE"), secureData.variable("AIRBNB_CLEANER_EMAIL"), "Tyler Woodfin")
                secureData.log(f"Checked for Evolve reservations - found and sent to {secureData.variable('AIRBNB_CLEANER_EMAIL')}")
            else:
                secureData.log("Checked for Evolve reservations - found only existing reservations")
        else:
            secureData.log("Checked for Evolve reservations - found reservation, but no Check-Out Date")
    else:
        secureData.log("Checked for Evolve reservations- none found")

params = {
	"calendar": calendar
}

if __name__ == "__main__":
    if(len(sys.argv) > 1):
        func = params.get(sys.argv[1], lambda: main)
        func()
    else:
        main()