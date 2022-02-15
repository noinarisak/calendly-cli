from calendly import Calendly
import requests
import datetime
import random
import os

from dotenv import load_dotenv
load_dotenv()

calendly = Calendly(os.getenv("CALENDLY_API_KEY"))

user = calendly.about()
user_uri = user['resource']['uri']

all_events = calendly.event_types(user=user_uri)['collection']

duration = 30
schedule_range = 14

total_slots = 5
slots_per_day = 2
events_to_schedule = 3

selected_event = next((event for event in all_events if event['duration'] == duration and event['active'] is True), None)

if not selected_event:
  print("No event found for duration")
  exit(1)

event_uri = selected_event["uri"]
event_id = event_uri.split("/")[-1]

def get_event_slots(event_id, range_in_days: int):
  start_day = datetime.datetime.now().strftime("%Y-%m-%d")
  end_day = (datetime.datetime.now() + datetime.timedelta(days=range_in_days)).strftime("%Y-%m-%d")

  result = requests.get(f"https://calendly.com/api/booking/event_types/{event_id}/calendar/range?timezone=America%2FDenver&diagnostics=false&range_start={start_day}&range_end={end_day}")

  if result.status_code != 200:
    print("Error fetching slots")
    return []

  # {
  #   'invitee_publisher_error': False,
  #   'today': '2022-02-15',
  #   'availability_timezone': 'America/Denver',
  #   'days': [
  #       {'date': '2022-02-19', 'status': 'unavailable', 'spots': [], 'invitee_events': []},
  #       {
  #           'date': '2022-02-22',
  #           'status': 'available',
  #           'spots': [
  #               {'status': 'available', 'start_time': '2022-02-22T07:00:00-07:00', 'invitees_remaining': 1},
  #               {'status': 'available', 'start_time': '2022-02-22T07:15:00-07:00', 'invitees_remaining': 1},

  available_days = [day for day in result.json()['days'] if day['status'] != 'unavailable']

  # now, cleanup the slots picked: remove slots which overlap
  # this will make it easier to output a bunch of scheduling options for multiple people at once

  # iterate through the copy of the array
  # https://stackoverflow.com/questions/10665591/how-to-remove-list-elements-in-a-for-loop-in-python
  for day in available_days:
    last_spot = None

    for spot in day['spots'][:]:
      if not last_spot:
        last_spot = spot
        continue

      if spot['status'] != 'available':
        day['spots'].remove(spot)
        continue

      last_start_time = datetime.datetime.fromisoformat(last_spot['start_time'])
      last_end_time = last_start_time + datetime.timedelta(minutes=duration)

      if datetime.datetime.fromisoformat(spot['start_time']) < last_end_time:
        day['spots'].remove(spot)
      else:
        last_spot = spot

      # randomize the order of the slots
      random.shuffle(day['spots'])

  return available_days

def human_readable_slot(slot):
  # target format: Jan 10th, 7:30pm MT

  # easiest way to get the am/pm to lowercase
  # https://stackoverflow.com/questions/38863210/how-to-make-pythons-datetime-object-show-am-and-pm-in-lowercase/38863352
  import locale
  locale.setlocale(locale.LC_ALL, 'de_DE')

  start_time = datetime.datetime.fromisoformat(slot['start_time'])

  # https://stackoverflow.com/questions/31299580/python-print-the-time-zone-from-strftime
  timezone_identifier = start_time.astimezone().tzname()

  start_time_str = start_time.strftime("%b %-d, %-I:%M%p")
  return f"{start_time_str} {timezone_identifier}"


available_days = get_event_slots(event_id, schedule_range)
chosen_slots = []

for _ in range(events_to_schedule):
  slots_for_event = []

  for day in available_days:
    slots_left = min(slots_per_day, total_slots - len(slots_for_event), len(day['spots']))

    for _ in range(slots_left):
      slots_for_event.append(day['spots'].pop())

  chosen_slots.append(slots_for_event)

for event_slots in chosen_slots:
  for slot in sorted(event_slots, key=lambda slot: slot['start_time']):
    print(f"- {human_readable_slot(slot)}")

  print("")

