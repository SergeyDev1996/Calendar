import datetime

import gspread as gc
import googleapiclient
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dateutil import parser

# Define the scopes for Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/contacts.readonly']
CREDENTIALS_FILE_PATH = "credentials.json"


def build_credentials():
    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_FILE_PATH, SCOPES)  # Path to your credentials.json
    creds = flow.run_local_server(port=0)
    return creds


# Function to get a valid date from the user
def get_date_input(prompt):
    while True:
        date_input = input(prompt)
        try:
            # Parse the input as a date (ensure it matches the expected format)
            date_obj = datetime.datetime.strptime(date_input, "%Y-%m-%d")
            return date_obj
        except ValueError:
            print("Invalid date format. Please enter the date in YYYY-MM-DD format.")


def format_meeting_duration(length_in_minutes: [int, float]) -> str:
    """
    Formats the meeting duration in a readable string format.

    Args:
        length_in_minutes (int, float): The meeting duration in minutes.

    Returns:
        str: The formatted meeting duration as a string.
    """
    # Convert length to integer in case it's a float
    total_minutes = int(length_in_minutes)
    hours, minutes = divmod(total_minutes, 60)

    if hours > 0:
        if minutes > 0:
            return f"{hours} hour{'s' if hours > 1 else ''} {minutes} minute{'s' if minutes > 1 else ''}"
        return f"{hours} hour{'s' if hours > 1 else ''}"
    return f"{minutes} minute{'s' if minutes > 1 else ''}"


# Function to select a date range
def get_date_range():
    print("Please enter the start and end date for the date range.")

    # Get start date and end date from the user
    start_date = get_date_input("Enter the start date (YYYY-MM-DD): ")
    end_date = get_date_input("Enter the end date (YYYY-MM-DD): ")

    # Ensure start date is before end date
    while start_date > end_date:
        print("Start date cannot be later than end date. Please try again.")
        start_date = get_date_input("Enter the start date (YYYY-MM-DD): ")
        end_date = get_date_input("Enter the end date (YYYY-MM-DD): ")

    print(f"Selected date range: {start_date.date()} to {end_date.date()}")
    return start_date, end_date


def get_user_by_email(creds, email):
    # Build the People API service
    service = build('people', 'v1', credentials=creds)

    # Search for the user by email in contacts, specifying the fields we want (names and emailAddresses)
    results = service.people().searchContacts(query=email, pageSize=1, readMask="names,emailAddresses").execute()

    # Check if any contacts were found
    if 'results' in results:
        contact = results['results'][0].get("person").get("names")
        if not contact:
            return email
        full_name = contact[0].get("displayName")
        if not full_name:
            return email
        return full_name
    return email


# Function to fetch data from Google Calendar within a specific date range
def get_calendars(service):
    """Fetches the list of all calendars accessible to the user."""
    calendar_list_result = service.calendarList().list().execute()
    return calendar_list_result.get('items', [])


def fetch_events_from_calendar(service, calendar_id, time_min, time_max):
    """Fetches events from a specific calendar within the given time range."""
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        maxResults=100,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])


def process_event(event, calendar_id, credentials):
    """Processes and formats a single event."""
    start_time_str = event["start"].get("dateTime", event["start"].get("date"))
    end_time_str = event["end"].get("dateTime", event["end"].get("date"))

    if start_time_str:
        dt_object = parser.isoparse(start_time_str)
        formatted_date = dt_object.strftime('%d/%m/%Y %H:%M')
    else:
        formatted_date = "no start time"

    if end_time_str:
        end_dt_object = parser.isoparse(end_time_str)
        length_of_meeting_in_minutes = (end_dt_object - dt_object).total_seconds() / 60
        formatted_meeting_time = format_meeting_duration(length_in_minutes=length_of_meeting_in_minutes)
    else:
        formatted_meeting_time = "no meeting time"

    user_full_name = get_user_by_email(email=event["creator"]["email"], creds=credentials)
    meeting_name = event.get("summary") or "no meeting name"
    meeting_description = event.get("description") or "no meeting description"
    meeting_link = event.get("hangoutLink") or "no meeting link"
    event_id = event.get("id")

    return {
        "calendar_id": calendar_id,
        "timestamp": formatted_date,
        "length of meeting": formatted_meeting_time,
        "person": user_full_name,
        "meeting name": meeting_name,
        "meeting description": meeting_description,
        "meeting link": meeting_link,
        "link unique id": event_id,
    }


def fetch_data_from_calendar(start_date, end_date, credentials):
    """Fetches and processes events from all accessible calendars."""
    service = build('calendar', 'v3', credentials=credentials)

    # Convert start_date and end_date to ISO format required by the API
    time_min = start_date.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
    time_max = end_date.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat() + 'Z'

    print(f"Fetching events from {time_min} to {time_max}")

    # Fetch all calendars
    calendars = get_calendars(service)
    all_events = []

    for calendar in calendars:
        calendar_id = calendar['id']
        events = fetch_events_from_calendar(service, calendar_id, time_min, time_max)
        for event in events:
            formatted_event = process_event(event, calendar_id, credentials)
            all_events.append(formatted_event)

    return all_events


def parse_existing_meetings():
    meetings_spreadsheet = gc.open_by_url()


def main():
    # Get the date range from the user
    credentials = build_credentials()
    start_date, end_date = get_date_range()
    # Fetch events for the selected date range
    fetch_data_from_calendar(start_date, end_date, credentials
                             )


if __name__ == '__main__':
    main()
