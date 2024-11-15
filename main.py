from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import datetime

# Define the scopes for Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def main():
    # Authenticate and create service
    creds = None
    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)  # Path to your credentials.json
        creds = flow.run_local_server(port=0)

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    print('Getting the upcoming events')
    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=10, singleEvents=True,
        orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(f"{start} - {event['summary']}")


if __name__ == '__main__':
    main()