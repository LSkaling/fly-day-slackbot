import os
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from dotenv import load_dotenv
from pathlib import Path
import json
import urllib.parse
from datetime import datetime 
import mysql.connector
from json_view_parser import parse_json
import io
from icalendar import Calendar, Event
from urllib.parse import urlencode
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaInMemoryUpload
from datetime import timedelta
import time
from boto.s3.connection import S3Connection

from flask import Flask, request


## Slack Parameters
FLIGHT_APPROVAL_CHANNEL = "C05SKL4BLQM" #Channel ID for #flight-coordinators
FLIGHT_ANNOUNCEMENT_CHANNEL = "CJHTZE9T8" #Channel ID for #fly-day
FLIGHT_COORDINATOR_CHANNEL = "C05SKL4BLQM" #Channel ID for #flight-coordinators

NON_FLIGHT_COORDINATOR = False

DEBUG_MODE = False

MESSAGE_TIME_DELAY_1 = 800
MESSAGE_TIME_DELAY_2 = 1000

# Initializes your app with your bot token and socket mode handler
# env_path = Path('.') / '.env'
# load_dotenv(dotenv_path=env_path)

# db_config = {
#     'user': os.environ.get("DB_USER"),
#     'password': os.environ.get("DB_PASSWORD"),
#     'host': os.environ.get("DB_HOST"),
#     'database': os.environ.get("DB_NAME"),
#     'raise_on_warnings': True
# }

print(repr(os.environ.get('PRIVATE_KEY')))


app = App(token=os.environ["SLACK_TOKEN"], signing_secret=os.environ["SIGNING_SECRET"])
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


# Helper functions
def get_flight_coordinators():
    #Get array of user IDs who are in the #slack-bot-testing channel

    #Get list of users in the channel
    response = app.client.conversations_members(
        channel=FLIGHT_COORDINATOR_CHANNEL
    )
    return response["members"]

def upload_ics_content_to_google_drive(ics_content, folder_id):
    # Sets up Google Drive API credentials
    credentials_info = {
        "type": "service_account",
        "project_id": os.environ["PROJECT_ID"],
        "private_key_id": os.environ["PRIVATE_KEY_ID"],
        "private_key": os.environ["PRIVATE_KEY"].replace('\\n', '\n'),
        "client_email": os.environ["CLIENT_EMAIL"],
        "client_id": os.environ["CLIENT_ID"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.environ["CLIENT_X509"],
        "universal_domain": "googleapis.com"
    }

    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=['https://www.googleapis.com/auth/drive']
    )

    # Create a Google Drive API client
    drive_service = build('drive', 'v3', credentials=credentials)

    # List folders accessible by the service account
    folders = drive_service.files().list(q="mimeType='application/vnd.google-apps.folder'").execute()
    print("Folders with access:")
    # Print the list of folder names and IDs
    for folder in folders.get('files', []):
        print(f"Folder Name: {folder['name']}, Folder ID: {folder['id']}")

    # Create a Google Drive API client
    drive_service = build('drive', 'v3', credentials=credentials)

    # Set the file name
    file_name = "Fly Day Event.ics"

    # Create a file metadata
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]  # ID of the target folder where you want to upload the file
    }

    # Convert the ics_content to bytes
    ics_bytes = ics_content

    # Upload the file
    media = MediaInMemoryUpload(ics_bytes, mimetype='text/calendar', resumable=True)
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    # Get the file ID
    file_id = file.get('id')

    # Generate a download link
    download_link = f"https://drive.google.com/uc?id={file_id}"

    return download_link

def generate_event_description(event_details, location, coordinating_user_name):
    if location == "Lake Lagunita":
        directions = "visit flightclub.stanford.edu/getting-lake-lagunita"
    elif location == "Coyote Hill":
        directions = "visit flightclub.stanford.edu/getting-coyote-hill"
    else:
        directions = f"contact {coordinating_user_name} on Slack"    

    return f"Join Stanford Flight Club for a Fly Day! \n\nFor directions to the flying site, {directions} \n\n Event Details:\n" + event_details

def generate_event_location(location):
    if(location == "Lake Lagunita"):
        return "Lake Lagunita Barbecue Pit"
    elif(location == "Coyote Hill"):
        return "Coyote Hill Rd, Palo Alto, CA 94304"
    else:
        return "Off Campus"
def generate_google_calendar_link(start_datetime, end_datetime, description, location, coordinating_user_name):


    start = start_datetime.strftime('%Y%m%dT%H%M%S')
    end = end_datetime.strftime('%Y%m%dT%H%M%S')
    title = urllib.parse.quote("Flight Club Fly Day")
    description = urllib.parse.quote(generate_event_description(description, location, coordinating_user_name))
    location = urllib.parse.quote(generate_event_location(location))
    
    link = f"https://www.google.com/calendar/render?action=TEMPLATE&text={title}&dates={start}/{end}&details={description}&location={location}"
    
    return link

def generate_apple_calendar_link(event_title, event_description, event_start, event_end, event_location, coordinating_user_name):
    # Create a new Event
    cal = Calendar()

    event = Event()
    event.add('summary', event_title)
    event.add('description', generate_event_description(event_description, event_location, coordinating_user_name))
    event.add('location', generate_event_location(event_location))
    event.add('dtstart', event_start)
    event.add('dtend', event_end)
    cal.add_component(event)

    ics_content = cal.to_ical()
    with open('Fly Day Event.ics', 'wb') as ics_file:
        ics_file.write(ics_content)
    
    return upload_ics_content_to_google_drive(ics_content, "1DAThCfFEQArqYtepkRSpHjSsYGV23FQu")


def convert_to_datetime(date_str, start_time_str, end_time_str):
    # Combine date and time strings
    start_datetime_str = f"{date_str} {start_time_str}"
    end_datetime_str = f"{date_str} {end_time_str}"

    # Define date and time format
    date_format = "%Y-%m-%d %H:%M"

    try:
        # Parse the datetime strings into datetime objects
        start_datetime = datetime.strptime(start_datetime_str, date_format)
        end_datetime = datetime.strptime(end_datetime_str, date_format)
    except ValueError as e:
        # Handle parsing errors (e.g., invalid format)
        return None, None  # Return None for both if parsing fails

    return start_datetime, end_datetime

def notify_flight_coordinators(user_id, flying_field, start_event, end_event, event_details, event_type):

    fly_day_notification = parse_json("post_fly_day.json", {
        "user_id": user_id,
        "event_type": event_type,
        "date": start_event.strftime('%A, %B %d, %Y'),
        "start_time": start_event.strftime('%I:%M %p'),
        "end_time": end_event.strftime('%I:%M %p'),
        "flying_field": flying_field,
        "event_details": event_details

        
        })
    
    app.client.chat_postMessage(
        channel=FLIGHT_APPROVAL_CHANNEL,
        blocks=fly_day_notification["blocks"],
        text="Flying Event Scheduled",
    )


def send_fly_day_announcement(user_id, flying_field, start_event, end_event, event_details, coordinating_user_name):
    calendar_link = generate_google_calendar_link(start_event, end_event, event_details, flying_field, coordinating_user_name)
    apple_calendar_link = generate_apple_calendar_link("Flight Club Fly Day", event_details, start_event, end_event, flying_field, coordinating_user_name)

    #ternary operator example
    if flying_field == "Lake Lagunita":
        flying_field_directions = " (<https://flightclub.sites.stanford.edu/getting-lake-lagunita|Directions>)"
    elif flying_field == "Coyote Hill":
        flying_field_directions = " (<https://flightclub.sites.stanford.edu/getting-coyote-hill|Directions>)"
    else:
        flying_field_directions = ""

    fly_day_announcement = parse_json("fly_day_announcement.json", {
        "user_id": user_id,
        "flying_field": flying_field + flying_field_directions,
        "date": start_event.strftime('%A, %B %d, %Y'),
        "start_time": start_event.strftime('%I:%M %p'),
        "end_time": end_event.strftime('%I:%M %p'),
        "event_details": event_details,
        "google_calendar_link": calendar_link,
        "apple_calendar_link": apple_calendar_link,
    })

    metadata = {
        "event_type": "request_fly_day",
        "event_payload": {
            "user_id": user_id,
            "start_datetime": start_event.strftime('%Y-%m-%d %H:%M:%S'),
            "end_datetime": end_event.strftime('%Y-%m-%d %H:%M:%S'),
            "event_details": event_details,
            "location": flying_field,
        }
    }

    message = app.client.chat_postMessage(
        channel=FLIGHT_ANNOUNCEMENT_CHANNEL,
        blocks=fly_day_announcement["blocks"],
        metadata=metadata,
        text="Fly Day Announcement",
        unfurl_links=False
    )

    message_ts = message["ts"]

    # Add a reaction to the message
    app.client.reactions_add(
        channel=FLIGHT_ANNOUNCEMENT_CHANNEL,
        name="paperplane", 
        timestamp=message_ts
    )

def send_fly_day_request(user_id, flying_field, start_event, end_event, event_details, event_type):

    request_fly_day_message = parse_json("request_fly_day_message.json", {
        "user_id": user_id,
        "event_type": event_type,
        "date": start_event.strftime('%A, %B %d, %Y'),
        "start_time": start_event.strftime('%I:%M %p'),
        "end_time": end_event.strftime('%I:%M %p'),
        "flying_field": flying_field,
        "event_details": event_details
    })

    metadata = {
        "event_type": "request_fly_day",
        "event_payload": {
            "user_id": user_id,
            "user_name": app.client.users_info(user=user_id)["user"]["name"],
            "start_datetime": start_event.strftime('%Y-%m-%d %H:%M:%S'),
            "end_datetime": end_event.strftime('%Y-%m-%d %H:%M:%S'),
            "event_details": event_details,
            "location": flying_field,
            "event_type": event_type
        }
    }

    app.client.chat_postMessage(
        channel=FLIGHT_APPROVAL_CHANNEL,
        blocks=request_fly_day_message["blocks"],
        text="Fly Day Request",
        metadata=metadata
    )

def get_metadata(body, parameter):
    return body['message']['metadata']['event_payload'][parameter]
    
def validate_scheduled_time(start_datetime, end_datetime):
    # Check if the start time is before the end time
    if start_datetime > end_datetime:
        return False

    # Check if the start time is at least 2 hours in the future
    if start_datetime < datetime.now() + timedelta(hours=1):
        return False

    return True

@app.command("/flyday")
def open_modal(ack, body, client):
    # Acknowledge the command request
    ack()
    flight_coordinators = get_flight_coordinators()
    user_id = body["user_id"]
    # Read the view JSON from the file
    with open("create_fly_day_view.json", "r") as view_file:
        create_fly_day_view = json.load(view_file)

    # Check if the user is a flight coordinator
    if user_id in flight_coordinators and not NON_FLIGHT_COORDINATOR:# and user_id != "U020661S3FY": #Shows modal to directly schedule a fly day
        print("User is a flight coordinator")
        create_fly_day_view["blocks"][0]["text"]["text"] = f"You are a Flight Coordinator, so this form will be sent directly to the #fly-day or #flight-coordinators channel when you submit it."
        create_fly_day_view["submit"]["text"] = "Submit"
        client.views_open(
            trigger_id=body["trigger_id"],
            view=create_fly_day_view,  # Use the view JSON read from the file
        )
    else: #Shows modal to request a fly day
        print("User is not a flight coordinator")
        create_fly_day_view["blocks"][0]["text"]["text"] = f"This form will be sent to the Flight Coordinators for approval before being sent to the #fly-day channel."
        create_fly_day_view["submit"]["text"] = "Request Fly Day"
        client.views_open(
            trigger_id=body["trigger_id"],
            view=create_fly_day_view,  # Use the view JSON read from the file
        )

    # Call views_open with the built-in client and the view JSON


@app.view("create-fly-day-modal") #Handles submission of the modal
def handle_view_events(ack, body, logger):
    ack()
    # Extract user ID
    user_id = body['user']['id']
    
    # Extract all the fields the user entered data from the modal
    flying_field = body['view']['state']['values']['section-1']['flying-field']['selected_option']['text']['text']
    event_type = body['view']['state']['values']['section-2']['event_type']['selected_option']['text']['text']
    selected_date = body['view']['state']['values']['date_picker_input']['date_picker_action']['selected_date']
    start_time = body['view']['state']['values']['start_time_picker_input']['start_time_picker_action']['selected_time']
    end_time = body['view']['state']['values']['end_time_picker_input']['end_time_picker_action']['selected_time']
    event_details = body['view']['state']['values']['long_text_input']['long_text_input']['value']
    user_is_flight_coordinator = user_id in get_flight_coordinators()
    coordinating_user_name = body['user']['name']

    start_event, end_event = convert_to_datetime(selected_date, start_time, end_time)

    # Validate the scheduled time
    if not validate_scheduled_time(start_event, end_event):
        app.client.chat_postMessage(
            channel=user_id,
            text="Please enter a valid time and date. The start time must be at least 1 hour in the future."
        )
        return
    elif user_is_flight_coordinator and not NON_FLIGHT_COORDINATOR:# and user_id != "U020661S3FY":
        if event_type == "Public":
            send_fly_day_announcement(user_id, flying_field, start_event, end_event, event_details, coordinating_user_name)
        else:
            notify_flight_coordinators(user_id, flying_field, start_event, end_event, event_details, event_type)
    else:
        send_fly_day_request(user_id, flying_field, start_event, end_event, event_details, event_type)

@app.action("accept_button") #Accepts a request
def accept_request(ack, body, logger):
    ack()

    accepter_id = body['user']['id']

    #All info stored in metadata
    user_id = get_metadata(body, "user_id")
    user_name = get_metadata(body, "user_name")
    start_datetime = get_metadata(body, "start_datetime")
    end_datetime = get_metadata(body, "end_datetime")
    event_details = get_metadata(body, "event_details")
    location = get_metadata(body, "location")
    event_type = get_metadata(body, "event_type")

    start_datetime = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
    end_datetime = datetime.strptime(end_datetime, '%Y-%m-%d %H:%M:%S')

    date = start_datetime.strftime('%A, %B %d, %Y')

    updated_message = parse_json("request_fly_day_message.json", {
        "user_id": user_id,
        "event_type": event_type,
        "date": date,
        "start_time": start_datetime.strftime('%I:%M %p'),
        "end_time": end_datetime.strftime('%I:%M %p'),
        "flying_field": location,
        "event_details": event_details,
        "accepter_id": accepter_id,
        "fake testing": "fake testing" #TODO: Remove
    })
    updated_message["blocks"][3] = {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f":white_check_mark: <@{accepter_id}> approved this fly day."
            }
        ]
    }

    app.client.chat_update(
        channel=FLIGHT_APPROVAL_CHANNEL,
        ts=body['message']['ts'],
        text="Approved",
        blocks=updated_message["blocks"]
    )

    #Message user that their request was accepted
    app.client.chat_postMessage(
        channel=user_id,
        text=f"Your fly day request for {date} was approved! Please familiarize yourself with the policies detailed in our <https://docs.google.com/document/d/1pyoxCYjjysrCgiVqAd8dqCVMsu4x6yLDWyLQt181KcI/edit?usp=sharing|Program Operating Handbook> prior to the flight. Safe Flying!"
    )

    if event_type == "Public":
        send_fly_day_announcement(user_id, location, start_datetime, end_datetime, event_details, user_name)

@app.action("deny_button")
def deny_request(ack, body, logger):
    ack()

    accepter_id = body['user']['id']

    #All info stored in metadata
    user_id = get_metadata(body, "user_id")
    start_datetime = get_metadata(body, "start_datetime")
    end_datetime = get_metadata(body, "end_datetime")
    event_details = get_metadata(body, "event_details")
    location = get_metadata(body, "location")
    event_type = get_metadata(body, "event_type")

    start_datetime = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
    end_datetime = datetime.strptime(end_datetime, '%Y-%m-%d %H:%M:%S')

    date = start_datetime.strftime('%A, %B %d, %Y')

    updated_message = parse_json("request_fly_day_message.json", {
        "user_id": user_id,
        "event_type": event_type,
        "date": date,
        "start_time": start_datetime.strftime('%I:%M %p'),
        "end_time": end_datetime.strftime('%I:%M %p'),
        "flying_field": location,
        "event_details": event_details,
        "accepter_id": accepter_id,
        "fake testing": "fake testing" #TODO: Remove
    })
    updated_message["blocks"][3] = {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f":x: <@{accepter_id}> denied this fly day."
            }
        ]
    }

    app.client.chat_update(
        channel=FLIGHT_APPROVAL_CHANNEL,
        ts=body['message']['ts'],
        text="Approved",
        blocks=updated_message["blocks"]
    )

    #Message user that their request was accepted
    app.client.chat_postMessage(
        channel=user_id,
        text=f"Your fly day request for {date} was denied. Message <@{accepter_id}> for more information."
    )

@app.action("flying-field")
def handle_some_action(ack, body, logger):
    ack()
    logger.info(body)

@app.action("event_type")
def handle_some_action(ack, body, logger):
    ack()
    logger.info(body)

# Function to schedule a reminder message
def schedule_reminder(channel, text, delay_seconds):
    current_time = time.time()
    post_at = current_time + delay_seconds
    print(f"Scheduling message for {int(post_at)}. Current time: {current_time}. Delay: {delay_seconds}")
    print(f"channel: {channel}")
    response = app.client.chat_scheduleMessage(
        channel=channel,
        post_at=int(post_at),
        text=text
    )
    #return response id
    return response["scheduled_message_id"]

#run when a reaction is added to a message - eventually want to have this send reminders, but for now it just gauges interest
@app.event("reaction_added")
def handle_reaction_added(body, logger):
    #check if the reaction was a paper airplane and was in the #fly-day channel
    if body["event"]["reaction"] == "paperplane" and body["event"]["item"]["channel"] == FLIGHT_ANNOUNCEMENT_CHANNEL:
        #get the metadata from the message
        message_ts = body["event"]["item"]["ts"]
        
        reacting_member_id = body["event"]["user"]

        #get the message
        message = app.client.conversations_history(
            channel=FLIGHT_ANNOUNCEMENT_CHANNEL,
            latest=message_ts,
            limit=1,
            inclusive=True
        )

        #use the content of the message to retrieve the date, start time, end time, and flying field
        message = message["messages"][0]
        location = message["blocks"][1]["text"]["text"].split(":* ")[1]
        date_str = message["blocks"][2]["text"]["text"].split(":* ")[1]
        start_time_str, end_time_str = message["blocks"][3]["text"]["text"].split(":* ")[1].split(" - ")
        event_type = message["metadata"]["event_type"]

        message_link = f"https://stanfordflightclub.slack.com/archives/{FLIGHT_ANNOUNCEMENT_CHANNEL}/p{message_ts.replace('.', '')}"

        # Convert the date strings to datetime objects
        start_datetime = datetime.strptime(f"{date_str} {start_time_str}", "%A, %B %d, %Y %I:%M %p")
        end_datetime = datetime.strptime(f"{date_str} {end_time_str}", "%A, %B %d, %Y %I:%M %p")

        reminder_time_2_hours = start_datetime - timedelta(hours=2)
        reminder_time_2_hours_str = reminder_time_2_hours.strftime("%Y-%m-%d %H:%M:%S")
        reminder_message_2_hours = f"Reminder: Fly day happening in 2 hours at {location}!"
        user_channel = message["user"]

        # Schedule the 2-hour reminder
        #print(schedule_reminder(reacting_member_id, reminder_message_2_hours, delay_seconds=remind))  # 1 second for debug, 7200 seconds (2 hours) for normal

        # Calculate the time at 9 am the day before the event
        reminder_time_9_am = start_datetime.replace(hour=9) - timedelta(days=1)
        reminder_time_9_am_str = reminder_time_9_am.strftime("%Y-%m-%d %H:%M:%S")
        reminder_message_9_am = f"Reminder: Fly day happening tomorrow at {start_datetime.strftime('%I:%M %p')} at {location}! Unreact to the message to stop receiving reminders." + "\n" + message_link

        # Schedule the 9 am reminder
        #print(schedule_reminder(reacting_member_id, reminder_message_9_am, MESSAGE_TIME_DELAY_2 if DEBUG_MODE else (reminder_time_9_am - time.time())))  # 10 seconds for debug, actual time difference for normal


@app.event("reaction_removed")
def handle_reaction_removed(body, logger):
    #check if the reaction was a paper airplane and was in the #fly-day channel
    if body["event"]["reaction"] == "paperplane" and body["event"]["item"]["channel"] == FLIGHT_ANNOUNCEMENT_CHANNEL:
        #get user id
        reacting_member_id = body["event"]["user"]
        direct_message_channel = app.client.conversations_open(
            users=reacting_member_id
        )["channel"]["id"]

        #get scheduled messages
        scheduled_messages = app.client.chat_scheduledMessages_list(
            channel=direct_message_channel
        )

        #get the message
        message = app.client.conversations_history(
            channel=FLIGHT_ANNOUNCEMENT_CHANNEL,
            latest=body["event"]["item"]["ts"],
            limit=1,
            inclusive=True
        )

        #use the content of the message to retrieve the date, start time, end time, and flying field
        message = message["messages"][0]
        location = message["blocks"][1]["text"]["text"].split(":* ")[1]
        date_str = message["blocks"][2]["text"]["text"].split(":* ")[1]
        start_time_str, end_time_str = message["blocks"][3]["text"]["text"].split(":* ")[1].split(" - ")
        event_type = message["metadata"]["event_type"]

        # Convert the date strings to datetime objects
        start_datetime = datetime.strptime(f"{date_str} {start_time_str}", "%A, %B %d, %Y %I:%M %p")
        end_datetime = datetime.strptime(f"{date_str} {end_time_str}", "%A, %B %d, %Y %I:%M %p")
        
        #determine the post_at time for the 2 hour reminder
        reminder_time_2_hours = start_datetime - timedelta(hours=2)
        if DEBUG_MODE:
            reminder_time_2_hours = datetime.now() + timedelta(seconds=MESSAGE_TIME_DELAY_1)
        #convert to unix    
        reminder_time_2_hours_unix = reminder_time_2_hours.timestamp()

        #determine the post_at time for the 9 am reminder
        reminder_time_9_am = start_datetime.replace(hour=9) - timedelta(days=1)
        if DEBUG_MODE:
            reminder_time_2_hours = datetime.now() + timedelta(seconds=MESSAGE_TIME_DELAY_2)
        reminder_time_9_am_unix = reminder_time_9_am.timestamp()

        def check_similar_timestamp(timestamp1, timestamp2):
            return abs(int(timestamp1) - int(timestamp2)) < 10

        #loop through scheduled messages
        for scheduled_message in scheduled_messages["scheduled_messages"]:
            #check if the scheduled message is for the 2 hour reminder
            #if check_similar_timestamp(scheduled_message["post_at"], reminder_time_2_hours_unix) or check_similar_timestamp(scheduled_message["post_at"], reminder_time_9_am_unix):
                #delete the scheduled message
            try:
                app.client.chat_deleteScheduledMessage(
                    channel=direct_message_channel,
                    scheduled_message_id=scheduled_message["id"]
                )
                print("Deleted scheduled message")

            except:
                print("Wrong message")

        print ("Remaining scheduled messages:")
        
        print(app.client.chat_scheduledMessages_list(
            channel=direct_message_channel
        ))

        
    

#Testing
def test_handle_view_events():
    # Simulate the payload
    payload = {'type': 'view_submission', 'team': {'id': 'T0KSB4BBJ', 'domain': 'stanfordflightclub', 'enterprise_id': 'E7SAV7LAD', 'enterprise_name': 'Stanford University'}, 'user': {'id': 'U020661S3FY', 'username': 'lskaling', 'name': 'lskaling', 'team_id': 'T0KSB4BBJ'}, 'api_app_id': 'A05SJNZT87P', 'token': 'SmYzuYupo9pmxh3DQ4nX1AgL', 'trigger_id': '5906688437730.19895147392.dd0264afaeb3d0391767bda3a2c1b1c9', 'view': {'id': 'V05SNL82D6E', 'team_id': 'T0KSB4BBJ', 'type': 'modal', 'blocks': [{'type': 'section', 'block_id': 'section-1', 'text': {'type': 'mrkdwn', 'text': 'Where will you be flying?', 'verbatim': False}, 'accessory': {'type': 'static_select', 'action_id': 'flying-field', 'placeholder': {'type': 'plain_text', 'text': 'Select a field', 'emoji': True}, 'options': [{'text': {'type': 'plain_text', 'text': 'Lake Lagunita', 'emoji': True}, 'value': 'lake-lag'}, {'text': {'type': 'plain_text', 'text': 'Coyote Hill', 'emoji': True}, 'value': 'coyote-hill'}, {'text': {'type': 'plain_text', 'text': 'Off Campus', 'emoji': True}, 'value': 'off-campus'}]}}, {'type': 'section', 'block_id': 'section-2', 'text': {'type': 'mrkdwn', 'text': 'What type of event?', 'verbatim': False}, 'accessory': {'type': 'static_select', 'action_id': 'event_type', 'placeholder': {'type': 'plain_text', 'text': 'Select an option', 'emoji': True}, 'options': [{'text': {'type': 'plain_text', 'text': 'Private', 'emoji': True}, 'value': 'private'}, {'text': {'type': 'plain_text', 'text': 'Public', 'emoji': True}, 'value': 'public'}]}}, {'type': 'section', 'block_id': 'context-section', 'text': {'type': 'mrkdwn', 'text': '*Private:* Only notifies the leadership team. \n *Public:* Notifies all members, and sends alerts leading up to the event.', 'verbatim': False}}, {'type': 'input', 'block_id': 'date_picker_input', 'label': {'type': 'plain_text', 'text': 'Select Date', 'emoji': True}, 'optional': False, 'dispatch_action': False, 'element': {'type': 'datepicker', 'action_id': 'date_picker_action', 'placeholder': {'type': 'plain_text', 'text': 'Select a date', 'emoji': True}}}, {'type': 'input', 'block_id': 'start_time_picker_input', 'label': {'type': 'plain_text', 'text': 'Start Time', 'emoji': True}, 'optional': False, 'dispatch_action': False, 'element': {'type': 'timepicker', 'action_id': 'start_time_picker_action', 'placeholder': {'type': 'plain_text', 'text': 'Select a start time', 'emoji': True}}}, {'type': 'input', 'block_id': 'end_time_picker_input', 'label': {'type': 'plain_text', 'text': 'End Time', 'emoji': True}, 'optional': False, 'dispatch_action': False, 'element': {'type': 'timepicker', 'action_id': 'end_time_picker_action', 'placeholder': {'type': 'plain_text', 'text': 'Select an end time', 'emoji': True}}}, {'type': 'input', 'block_id': 'long_text_input', 'label': {'type': 'plain_text', 'text': 'Event Details (Optional)', 'emoji': True}, 'optional': False, 'dispatch_action': False, 'element': {'type': 'plain_text_input', 'action_id': 'long_text_input', 'multiline': True, 'dispatch_action_config': {'trigger_actions_on': ['on_enter_pressed']}}}], 'private_metadata': '', 'callback_id': 'create-fly-day-modal', 'state': {'values': {'section-1': {'flying-field': {'type': 'static_select', 'selected_option': {'text': {'type': 'plain_text', 'text': 'Lake Lagunita', 'emoji': True}, 'value': 'lake-lag'}}}, 'section-2': {'event_type': {'type': 'static_select', 'selected_option': {'text': {'type': 'plain_text', 'text': 'Public', 'emoji': True}, 'value': 'public'}}}, 'date_picker_input': {'date_picker_action': {'type': 'datepicker', 'selected_date': '2023-09-20'}}, 'start_time_picker_input': {'start_time_picker_action': {'type': 'timepicker', 'selected_time': '03:00'}}, 'end_time_picker_input': {'end_time_picker_action': {'type': 'timepicker', 'selected_time': '05:00'}}, 'long_text_input': {'long_text_input': {'type': 'plain_text_input', 'value': 'theaudhauf'}}}}, 'hash': '1694887246.8ZOvWgWY', 'title': {'type': 'plain_text', 'text': 'My Modal', 'emoji': True}, 'clear_on_close': False, 'notify_on_close': False, 'close': None, 'submit': {'type': 'plain_text', 'text': 'Submit', 'emoji': True}, 'previous_view_id': None, 'root_view_id': 'V05SNL82D6E', 'app_id': 'A05SJNZT87P', 'external_id': '', 'app_installed_team_id': 'T0KSB4BBJ', 'bot_id': 'B05SMMDM6QJ'}, 'response_urls': [], 'is_enterprise_install': False, 'enterprise': {'id': 'E7SAV7LAD', 'name': 'Stanford University'}}

    # Call the handler function with the simulated payload
    handle_view_events(lambda: None, payload, None)

# Run the testing function
#test_handle_view_events()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    flask_app.run(host='0.0.0.0', port=port)