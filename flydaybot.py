import slack
import os
from pathlib import Path
from dotenv import load_dotenv
from slackeventsapi import SlackEventAdapter
import json

# For local development, set environment variables defined in .env
from flask import Flask, request, Response
app = Flask(__name__)


env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])

#client.chat_postMessage(channel='#slack-bot-testing', text="Hello World!")

@app.route('/flyday', methods=['POST'])
def flyday():
    with open('create_fly_day_view.json', 'r') as file:
        modal_view = json.load(file)

    payload = json.loads(request.form["payload"])

    response = client.views_open(
        trigger_id = payload["trigger_id"],
        view=modal_view)

    return Response(), 200

@app.route('/slack/events', methods=['POST'])
def slack_events():
    try:
        # Verify the request comes from Slack (using SlackEventAdapter)
        slack_event_adapter.on_event(request.data)

        # Return a 200 OK response to Slack
        return Response(), 200
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 400




#Start the connection
if __name__ == "__main__":
    app.run(debug=True, port=5001)
