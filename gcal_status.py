"""Script to set slack status based on the google calendar event.
"""
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from dateutil import parser
from dateutil import tz
from typing import NamedTuple
import slack
from typing import List


default_status = {
    "text": "Working EST (0730 - 1530 PST)",
    "emoji": ":home:",
}


BASE_PATH = '/nail/home/varun/pg/personal/slack_tools/'


class Event(NamedTuple):
    summary: str
    description: str
    start_timestamp: str
    end_timestamp: int  # UTC
    response: str
    out_of_office: bool
    lunch_or_snack: bool


class Status(NamedTuple):
    status_text: str
    status_emoji: str
    status_expiration: int


def get_gcal_creds():
    if os.path.exists(BASE_PATH + 'token.pickle'):
        with open(BASE_PATH + 'token.pickle', 'rb') as token:
            creds = pickle.load(token)

    return creds


def get_slack_client():
    token = ''
    with open(BASE_PATH + 'slack_token') as f:
        token = f.read().strip()

    return slack.WebClient(token=token)


def get_current_events():
    creds = get_gcal_creds()

    service = build('calendar', 'v3', credentials=creds)

    # search for events starting after this time
    min_time = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time

    # search for events starting before this time
    max_time = (datetime.datetime.utcnow() + datetime.timedelta(minutes=20)).isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary',
        timeMin=min_time,
        timeMax=max_time,
        maxResults=3,
        singleEvents=True,
        showDeleted=False,
        orderBy='startTime',
    ).execute()

    events = events_result.get('items', [])

    if not events:
        return

    def format_event(event):
        start_time = parser.isoparse(event['start']['dateTime']).astimezone(tz.tzutc())
        end_time = parser.isoparse(event['end']['dateTime']).astimezone(tz.tzutc())
        response = next((attendee['responseStatus'] for attendee in event.get('attendees', []) if attendee.get('self', False)), None)
        return Event(
            summary=event['summary'],
            description=event.get('description'),
            start_timestamp=int(start_time.timestamp()),
            end_timestamp=int(end_time.timestamp()),
            response=response,
            out_of_office='out-of-office' in event.get('description', ''),
            lunch_or_snack='Lunch' in event['summary'] or 'Coffee' in event['summary'],
        )

    formatted_events = [format_event(event) for event in events]
    return formatted_events
    return [format_event(event) for event in events]


def filter_events(events: List[Event]):
    # filter out all events for which response is declined/tentative/needsAction
    if not events:
        return []

    return [event for event in events if event.response not in ['declined', 'needsAction', 'tentative']]


def set_slack_status(status_text, status_emoji, status_expiration=0):
    client = get_slack_client()
    status_data = {
        "status_text": status_text,
        "status_emoji": status_emoji,
        "status_expiration": status_expiration,
    }
    response = client.users_profile_set(profile=status_data)

    assert response["ok"]


def get_slack_status():
    client = get_slack_client()
    profile = client.users_profile_get()

    return Status(
        status_text=profile['profile']['status_text'],
        status_emoji=profile['profile']['status_emoji'],
        status_expiration=profile['profile']['status_expiration'],
    )


def main():
    current_events = filter_events(get_current_events())

    if not current_events:
        # Get current slack status
        current_status = get_slack_status()
        if current_status.status_text == "In a meeting" or current_status.status_text == "":
            # clear that since there is no meeting now.
            set_slack_status(
                status_text=default_status['text'],
                status_emoji=default_status['emoji'],
            )
        return

    current_event = current_events[0]
    if current_event.out_of_office:
        set_slack_status(
            status_text='Out-of-office',
            status_emoji=":away:",
        )

        return

    set_slack_status(
        status_text="In a meeting",
        status_emoji=":calendar:",
        status_expiration=current_event.end_timestamp,
    )


if __name__ == '__main__':
    main()
