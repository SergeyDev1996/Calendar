import datetime
import os

import gspread
import gspread as gc
import googleapiclient
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as service_credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dateutil import parser
from dotenv import load_dotenv

load_dotenv()

# Define the scopes for Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/contacts.readonly',
          'https://www.googleapis.com/auth/spreadsheets']

CREDENTIALS_FILE_PATH = os.environ.get("CREDENTIALS_FILE_PATH")
SPREADSHEET_URL = os.environ.get("SPREADSHEET_URL")

COLUMN_TO_INDEX_MAPPING = {
    "Timestamp": "A",
    "Length of Meeting": "B",
    "Person": "C",
    "Meeting Name": "D",
    "Meeting Description": "E",
    "Link to Meeting": "F",
    "Meeting Unique Id": "G"

}


def build_credentials():
    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_FILE_PATH, SCOPES)  # Path to your credentials.json
    # creds = flow.run_local_server(host="localhost", port=8080, open_browser=False)
    creds = flow.run_local_server(
        open_browser=False, bind_addr="0.0.0.0", port=8080
    )
    return creds


def column_letter_to_index(column_letter: str) -> int:
    """
    Converts a column letter to a numeric index, starting from 1.

    Args:
    - column_letter (str): The column letter (e.g., 'A', 'B', ..., 'Z', 'AA').

    Returns:
    - int: The numeric index corresponding to the column letter.
    """
    column_letter = column_letter.upper()  # Ensure the letter is uppercase
    index = 0
    for char in column_letter:
        index = index * 26 + (ord(char) - ord('A') + 1)
    return index


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
    start_date = datetime.datetime.strptime(os.environ.get("START_DATE"), "%Y-%m-%d")
    end_date = datetime.datetime.strptime(os.environ.get("END_DATE"), "%Y-%m-%d")

    # Ensure start date is before end date
    while start_date > end_date:
        print("Start date cannot be later than end date. Please try again.")
        raise Exception
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


def push_new_meetings_to_spreadsheet(events: list, credentials) -> None:
    """
    Push events data to a Google Spreadsheet.

    Args:
    - spreadsheet_id (str): The ID of the Google Spreadsheet.
    - events (list): List of dictionaries containing event data.
    - credentials: Google API credentials object.
    - column_mapping (dict): Mapping of column names to spreadsheet column letters.
    """
    # Authenticate and open the spreadsheet
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_url(SPREADSHEET_URL).sheet1

    # Transform column mapping to numeric indexes
    column_indexes = {key: column_letter_to_index(value) for key, value in COLUMN_TO_INDEX_MAPPING.items()}

    # Get all existing unique IDs from the spreadsheet
    unique_id_column_index = column_indexes["Meeting Unique Id"]
    existing_unique_ids = sheet.col_values(unique_id_column_index)

    # Push new events
    for event in events:
        unique_id = event["link unique id"]
        if unique_id in existing_unique_ids:
            print(f"Event with unique ID '{unique_id}' already exists. Skipping...")
            continue  # Skip if the event already exists

        # Prepare the row data in the correct order
        row_data = [
            event["timestamp"],
            event["length of meeting"],
            event["person"],
            event["meeting name"],
            event["meeting description"],
            event["meeting link"],
            unique_id
        ]
        # Append the new row to the sheet
        sheet.append_row(row_data)
        print(f"Added event with unique ID '{unique_id}'.")


def build_service():
    # Load credentials from the service account file
    credentials = service_credentials.from_service_account_file(
        CREDENTIALS_FILE_PATH, scopes=SCOPES
    )

    # Build the Google Calendar API service
    service = build('calendar', 'v3', credentials=credentials)
    return service


def add_shared_calendar_to_service_account(calendar_id):
    """
    Adds a shared calendar to the service account's calendar list.
    :param calendar_id: The ID of the shared calendar (email or unique calendar ID).
    """
    service = build_service()
    try:
        # Add the calendar to the service account's calendar list
        calendar_entry = {'id': calendar_id}
        added_calendar = service.calendarList().insert(body=calendar_entry).execute()
        print(f"Calendar added: {added_calendar.get('summary')}")
    except Exception as e:
        print(f"Error adding calendar: {e}")


def main():
    credentials = build_credentials()
    start_date, end_date = get_date_range()
    # Fetch events for the selected date range
    events = fetch_data_from_calendar(start_date, end_date, credentials)
    push_new_meetings_to_spreadsheet(events=events, credentials=credentials)


if __name__ == '__main__':
    main()
