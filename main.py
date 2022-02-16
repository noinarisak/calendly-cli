import datetime
import os
import random
import typing as t

import requests
from calendly import Calendly

calendly = None
calendly_user_uri = None


def event_id_with_duration(duration: int) -> str:
    all_events = calendly.event_types(user=calendly_user_uri)["collection"]
    selected_event = next((event for event in all_events if event["duration"] == duration and event["active"] is True), None)

    if not selected_event:
        print("No event found for duration")
        exit(1)

    event_uri = selected_event["uri"]
    event_id = event_uri.split("/")[-1]
    return event_id


def get_event_slots(event_id, range_in_days: int, duration: int, target_timezone: str, after_hour: t.Optional[int] = None):
    start_day = datetime.datetime.now().strftime("%Y-%m-%d")
    end_day = (datetime.datetime.now() + datetime.timedelta(days=range_in_days)).strftime("%Y-%m-%d")

    result = requests.get(
        f"https://calendly.com/api/booking/event_types/{event_id}/calendar/range?timezone={target_timezone}&diagnostics=false&range_start={start_day}&range_end={end_day}"
    )

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

    available_days = [day for day in result.json()["days"] if day["status"] != "unavailable"]

    # now, cleanup the slots picked: remove slots which overlap
    # this will make it easier to output a bunch of scheduling options for multiple people at once

    # iterate through the copy of the array
    # https://stackoverflow.com/questions/10665591/how-to-remove-list-elements-in-a-for-loop-in-python
    for day in available_days:
        last_spot = None

        for spot in day["spots"][:]:
            if spot["status"] != "available":
                day["spots"].remove(spot)
                continue

            spot_start_time = datetime.datetime.fromisoformat(spot["start_time"])
            if after_hour is not None and spot_start_time.hour <= after_hour:
                # TODO should add logging for this
                day["spots"].remove(spot)
                continue

            if not last_spot:
                last_spot = spot
                continue

            last_start_time = datetime.datetime.fromisoformat(last_spot["start_time"])
            last_end_time = last_start_time + datetime.timedelta(minutes=duration)

            if spot_start_time < last_end_time:
                day["spots"].remove(spot)
            else:
                last_spot = spot

            # randomize the order of the slots
            random.shuffle(day["spots"])

    return available_days


def human_readable_slot(slot):
    # target format: Jan 10th, 7:30pm MT

    start_time = datetime.datetime.fromisoformat(slot["start_time"])

    # TODO need to inherit the timezone from the event

    # https://stackoverflow.com/questions/31299580/python-print-the-time-zone-from-strftime
    # also, I hate MST vs MT which is why I'm converint ST => T
    timezone_identifier = start_time.astimezone().tzname().replace("ST", "T")

    start_time_str = start_time.strftime("%b %-d, %-I:%M%p")

    # easiest way to get the am/pm to lowercase is to set the locale to de_DE, but this also messes with month formatting
    # https://stackoverflow.com/questions/38863210/how-to-make-pythons-datetime-object-show-am-and-pm-in-lowercase/38863352
    start_time_str = start_time_str.replace("AM", "am").replace("PM", "pm")

    return f"{start_time_str} {timezone_identifier}"


# duration = 30
# schedule_range = 25

# total_slots = 20
# slots_per_day = 2
# events_to_schedule = 1
# # after_hour = 12 + 5
# after_hour = None
# target_timezone = "EST"
# # target_timezone = "America/Denver"

# TODO option to exclude weekends


def calendly_times(duration, days, timezone, after_hour, total, events, slots_per_day, api_key):
    global calendly
    global calendly_user_uri

    calendly = Calendly(os.getenv("CALENDLY_API_KEY"))
    calendly_user = calendly.about()
    calendly_user_uri = calendly_user["resource"]["uri"]

    # self documenting, baby
    schedule_range_in_days = days
    number_of_events_to_schedule = events
    number_of_slots_per_event = total

    event_id = event_id_with_duration(duration)
    available_days = get_event_slots(event_id, schedule_range_in_days, duration, timezone, after_hour)

    chosen_slots_by_events = []
    output = ""

    for _ in range(number_of_events_to_schedule):
        slots_for_event = []

        for day in available_days:
            slots_left = min(slots_per_day, number_of_slots_per_event - len(slots_for_event), len(day["spots"]))

            for _ in range(slots_left):
                slots_for_event.append(day["spots"].pop())

        chosen_slots_by_events.append(slots_for_event)

    for event_slots in chosen_slots_by_events:
        for slot in sorted(event_slots, key=lambda slot: slot["start_time"]):
            output += f"- {human_readable_slot(slot)}\n"

        output += "\n"

    return output
