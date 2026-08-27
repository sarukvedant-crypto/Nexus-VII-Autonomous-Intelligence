import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import datetime

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.readonly'
]

def get_google_credentials():
    """
    Returns valid Google credentials for the defined SCOPES.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'auth', 'token.json')
    credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'auth', 'credentials.json')
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                # If refresh fails, we need to re-auth
                creds = None
                
        if not creds:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError("Missing 'credentials.json'. Please download it from Google Cloud Console and place it in the auth/ folder.")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            
    return creds

def get_calendar_service():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    try:
        creds = get_google_credentials()
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        raise Exception(f"Failed to build calendar service: {e}")

def check_schedule(date_str):
    """
    date_str: "YYYY-MM-DD"
    Fetches the top 10 upcoming events for the given date.
    """
    try:
        service = get_calendar_service()
    except Exception as e:
        return f"Error connecting to Google Calendar: {e}"

    try:
        # Create start of day and end of day
        start_time = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + datetime.timedelta(days=1)
        
        # Local time ISO format
        start_iso = start_time.isoformat() + 'Z'
        end_iso = end_time.isoformat() + 'Z'

        # Call the Calendar API
        events_result = service.events().list(calendarId='primary', timeMin=start_iso, timeMax=end_iso,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return f"No upcoming events found on {date_str}."

        result = f"Schedule for {date_str}:\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            result += f"- {start}: {event['summary']}\n"
            
        return result
    except Exception as e:
        return f"Error fetching schedule: {e}"

def add_event(summary, start_time, end_time, description=""):
    """
    summary: String
    start_time: ISO 8601 string (e.g., '2023-10-15T09:00:00-07:00')
    end_time: ISO 8601 string (e.g., '2023-10-15T10:00:00-07:00')
    """
    try:
        service = get_calendar_service()
    except Exception as e:
        return f"Error connecting to Google Calendar: {e}"

    try:
        event = {
          'summary': summary,
          'description': description,
          'start': {
            'dateTime': start_time,
          },
          'end': {
            'dateTime': end_time,
          },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Event created successfully: {event.get('htmlLink')}"
    except Exception as e:
        return f"Error creating event: {e}"
