# Slack Gcal Status

Script to set the slack status based on the events in Google Calendar.
The Calendar plugin for slack doesn't work in case you have a default status set. This script was written to provide
a minimal functionality that bypasses that.

## Pre-requisites

1. Enable the Google Calendar API by following the instructions [here](https://developers.google.com/calendar/quickstart/python) and copy the *token.pickle* file to the base project directory.
2. Get your slack token and put it in a *slack_token* file.
