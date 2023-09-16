import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from pathlib import Path
import json  # Import the json module
import urllib.parse
import datetime

# Initializes your app with your bot token and socket mode handler
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = App(token=os.environ.get("SLACK_TOKEN"))

# Read the view JSON from the file
with open("create_fly_day_view.json", "r") as view_file:
    create_fly_day_view = json.load(view_file)

with open ("request_fly_day_view.json", "r") as view_file:
    request_fly_day_view = json.load(view_file) #TODO: Implement request fly day view



# Helper functions
def get_flight_coordinators():
    #Get array of user IDs who are in the #slack-bot-testing channel

    #Get list of users in the channel
    response = app.client.conversations_members(
        channel="C05SKL4BLQM"
    )
    return response["members"]

def generate_google_calendar_link(title, start_datetime, end_datetime, description, location):
    start = start_datetime.strftime('%Y%m%dT%H%M%S')
    end = end_datetime.strftime('%Y%m%dT%H%M%S')
    title = urllib.parse.quote(title)
    description = urllib.parse.quote(description)
    location = urllib.parse.quote(location)
    
    link = f"https://www.google.com/calendar/render?action=TEMPLATE&text={title}&dates={start}/{end}&details={description}&location={location}"
    
    return link

@app.command("/flyday")
def open_modal(ack, body, client):
    # Acknowledge the command request
    ack()
    flight_coordinators = get_flight_coordinators()
    user_id = body["user_id"]

    # Check if the user is a flight coordinator
    if user_id in flight_coordinators: #Shows modal to directly schedule a fly day
        print("User is a flight coordinator")
        client.views_open(
            trigger_id=body["trigger_id"],
            view=create_fly_day_view  # Use the view JSON read from the file
        )
    else: #Shows modal to request a fly day
        print("User is not a flight coordinator")
        client.views_open(
            trigger_id=body["trigger_id"],
            view=request_fly_day_view  # Use the view JSON read from the file
        )

    print(get_flight_coordinators())
    # Call views_open with the built-in client and the view JSON


@app.view("create-fly-day-modal") #Handles submission of the modal
def handle_view_events(ack, body, logger):
    ack()
    print(body)
    
    # Extract user ID
    user_id = body['user']['id']
    
    # Extract all the fields the user entered data from the modal
    flying_field = body['view']['state']['values']['section-1']['flying-field']['selected_option']['text']['text']
    event_type = body['view']['state']['values']['section-2']['event_type']['selected_option']['text']['text']
    selected_date = body['view']['state']['values']['date_picker_input']['date_picker_action']['selected_date']
    start_time = body['view']['state']['values']['start_time_picker_input']['start_time_picker_action']['selected_time']
    end_time = body['view']['state']['values']['end_time_picker_input']['end_time_picker_action']['selected_time']
    event_details = body['view']['state']['values']['long_text_input']['long_text_input']['value']
    
    # Now you have all the extracted data
    print(f"User ID: {user_id}")
    print(f"Flying Field: {flying_field}")
    print(f"Event Type: {event_type}")
    print(f"Selected Date: {selected_date}")
    print(f"Start Time: {start_time}")
    print(f"End Time: {end_time}")
    print(f"Event Details: {event_details}")

    event_title = "Sample Event"
    start_time = datetime.datetime(2023, 9, 30, 10, 0)
    end_time = datetime.datetime(2023, 9, 30, 12, 0)
    event_description = "This is a sample event description."
    event_location = "Sample Location"

    calendar_link = generate_google_calendar_link(event_title, start_time, end_time, event_description, event_location)
    print(calendar_link)

    with open("fly_day_announcement.json", "r") as view_file:
        fly_day_announcement = json.load(view_file)

    fly_day_announcement["blocks"][0]["text"]["text"] = f"*FLY DAY FLY DAY FLY DAY*\n<@{user_id}> is hosting an upcoming fly day event."
    fly_day_announcement["blocks"][1]["text"]["text"] = f"*Location:* {flying_field}"
    fly_day_announcement["blocks"][2]["text"]["text"] = f" "
    fly_day_announcement["blocks"][3]["text"]["text"] = f"*Date:*{selected_date}"
    fly_day_announcement["blocks"][4]["text"]["text"] = f"*Time:* {start_time} - {end_time}"
    fly_day_announcement["blocks"][5]["text"]["text"] = f" "
    fly_day_announcement["blocks"][6]["text"]["text"] = f"*Details:*\n{event_details}"
    fly_day_announcement["blocks"][8]["text"]["text"] = f"Questions? Contact <@{user_id}>\n\nInterested? React with :paperplane: to RSVP. This is not a commitment, just a way to gauge interest.\n<{calendar_link}|Click here to add this event to your calendar>"



    app.client.chat_postMessage(
        channel="C05TAMAAD08",
        blocks=fly_day_announcement["blocks"]
    )


@app.action("flying-field")
def handle_some_action(ack, body, logger):
    ack()
    logger.info(body)

@app.action("event_type")
def handle_some_action(ack, body, logger):
    ack()
    logger.info(body)

##Testing
def test_handle_view_events():
    # Simulate the payload
    payload = {'type': 'view_submission', 'team': {'id': 'T0KSB4BBJ', 'domain': 'stanfordflightclub', 'enterprise_id': 'E7SAV7LAD', 'enterprise_name': 'Stanford University'}, 'user': {'id': 'U020661S3FY', 'username': 'lskaling', 'name': 'lskaling', 'team_id': 'T0KSB4BBJ'}, 'api_app_id': 'A05SJNZT87P', 'token': 'SmYzuYupo9pmxh3DQ4nX1AgL', 'trigger_id': '5906688437730.19895147392.dd0264afaeb3d0391767bda3a2c1b1c9', 'view': {'id': 'V05SNL82D6E', 'team_id': 'T0KSB4BBJ', 'type': 'modal', 'blocks': [{'type': 'section', 'block_id': 'section-1', 'text': {'type': 'mrkdwn', 'text': 'Where will you be flying?', 'verbatim': False}, 'accessory': {'type': 'static_select', 'action_id': 'flying-field', 'placeholder': {'type': 'plain_text', 'text': 'Select a field', 'emoji': True}, 'options': [{'text': {'type': 'plain_text', 'text': 'Lake Lagunita', 'emoji': True}, 'value': 'lake-lag'}, {'text': {'type': 'plain_text', 'text': 'Coyote Hill', 'emoji': True}, 'value': 'coyote-hill'}, {'text': {'type': 'plain_text', 'text': 'Off Campus', 'emoji': True}, 'value': 'off-campus'}]}}, {'type': 'section', 'block_id': 'section-2', 'text': {'type': 'mrkdwn', 'text': 'What type of event?', 'verbatim': False}, 'accessory': {'type': 'static_select', 'action_id': 'event_type', 'placeholder': {'type': 'plain_text', 'text': 'Select an option', 'emoji': True}, 'options': [{'text': {'type': 'plain_text', 'text': 'Private', 'emoji': True}, 'value': 'private'}, {'text': {'type': 'plain_text', 'text': 'Public', 'emoji': True}, 'value': 'public'}]}}, {'type': 'section', 'block_id': 'context-section', 'text': {'type': 'mrkdwn', 'text': '*Private:* Only notifies the leadership team. \n *Public:* Notifies all members, and sends alerts leading up to the event.', 'verbatim': False}}, {'type': 'input', 'block_id': 'date_picker_input', 'label': {'type': 'plain_text', 'text': 'Select Date', 'emoji': True}, 'optional': False, 'dispatch_action': False, 'element': {'type': 'datepicker', 'action_id': 'date_picker_action', 'placeholder': {'type': 'plain_text', 'text': 'Select a date', 'emoji': True}}}, {'type': 'input', 'block_id': 'start_time_picker_input', 'label': {'type': 'plain_text', 'text': 'Start Time', 'emoji': True}, 'optional': False, 'dispatch_action': False, 'element': {'type': 'timepicker', 'action_id': 'start_time_picker_action', 'placeholder': {'type': 'plain_text', 'text': 'Select a start time', 'emoji': True}}}, {'type': 'input', 'block_id': 'end_time_picker_input', 'label': {'type': 'plain_text', 'text': 'End Time', 'emoji': True}, 'optional': False, 'dispatch_action': False, 'element': {'type': 'timepicker', 'action_id': 'end_time_picker_action', 'placeholder': {'type': 'plain_text', 'text': 'Select an end time', 'emoji': True}}}, {'type': 'input', 'block_id': 'long_text_input', 'label': {'type': 'plain_text', 'text': 'Event Details (Optional)', 'emoji': True}, 'optional': False, 'dispatch_action': False, 'element': {'type': 'plain_text_input', 'action_id': 'long_text_input', 'multiline': True, 'dispatch_action_config': {'trigger_actions_on': ['on_enter_pressed']}}}], 'private_metadata': '', 'callback_id': 'create-fly-day-modal', 'state': {'values': {'section-1': {'flying-field': {'type': 'static_select', 'selected_option': {'text': {'type': 'plain_text', 'text': 'Lake Lagunita', 'emoji': True}, 'value': 'lake-lag'}}}, 'section-2': {'event_type': {'type': 'static_select', 'selected_option': {'text': {'type': 'plain_text', 'text': 'Public', 'emoji': True}, 'value': 'public'}}}, 'date_picker_input': {'date_picker_action': {'type': 'datepicker', 'selected_date': '2023-09-20'}}, 'start_time_picker_input': {'start_time_picker_action': {'type': 'timepicker', 'selected_time': '03:00'}}, 'end_time_picker_input': {'end_time_picker_action': {'type': 'timepicker', 'selected_time': '05:00'}}, 'long_text_input': {'long_text_input': {'type': 'plain_text_input', 'value': 'theaudhauf'}}}}, 'hash': '1694887246.8ZOvWgWY', 'title': {'type': 'plain_text', 'text': 'My Modal', 'emoji': True}, 'clear_on_close': False, 'notify_on_close': False, 'close': None, 'submit': {'type': 'plain_text', 'text': 'Submit', 'emoji': True}, 'previous_view_id': None, 'root_view_id': 'V05SNL82D6E', 'app_id': 'A05SJNZT87P', 'external_id': '', 'app_installed_team_id': 'T0KSB4BBJ', 'bot_id': 'B05SMMDM6QJ'}, 'response_urls': [], 'is_enterprise_install': False, 'enterprise': {'id': 'E7SAV7LAD', 'name': 'Stanford University'}}

    # Call the handler function with the simulated payload
    handle_view_events(lambda: None, payload, None)

# Run the testing function
test_handle_view_events()

# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
