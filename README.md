This is a Slack bot used by the Stanford Flight Club for coordinating fly day events. Stanford Flight Club is a student organization at Stanford for engineering and aviation enthusiasts. Read more about the club [here](https://flightclub.sites.stanford.edu).

Part of the club's events includes frequent "Fly Days", which students bring RC planes to fly, or fly planes from Flight Club's fleet. These events are open to all Stanford affiliates, and is the only on campus drone activity sanctioned by the university. 

# Functionality
Users are differentiated into two groups, flight coordinators and affiliates. Flight coordinators are anyone added to the `#flight-coordinators` private Slack channel. These members are certified to safety operate aircraft, so can fly on their own and host events. Affiliates can request fly days which flight coordinators approve.

Users request an event with `/flyday`. A modal is presented which lets the user specify the location, time, and type of event (described below). If the member is a flight coordinator, this is automatically approved and recorded. Otherwise, it is sent to the `#flight-coordinators` private Slack channel for approval. 

There are two types of fly day events: private and public. Private events are intended for individuals or small groups who are flying on their own. Public events are shared with the `#flyday` channel for anyone to come to. Our agreement with the university stipulates anyone flying on campus must be a Flight Club member with permission to fly, and therefore this process lets us track that. 

Public flight events are shared to `#flyday` with options to add the event to various calendars. Users can also react to the message to be automatically notified on Slack before the event. 

# API and Deployment
This bot uses the Slack Bolt SDK for Python. It also uses the google drive API for storing calendar events.

The file is deployed to Heroku for hosting. Lawton maintains access to the Slack App and Heroku hosting. 
