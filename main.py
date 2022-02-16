import datetime
import random
import typing as t

import requests
from calendly import Calendly

calendly = None
calendly_user_uri = None

NICE_TO_UGLY_TIMEZONE_MAPPING = {
    "CST": "CST6CDT",
    "PST": "PST8PDT",
}

# https://stackoverflow.com/questions/483666/reverse-invert-a-dictionary-mapping
UGLY_TO_NICE_TIMEZONE_MAPPING = dict((v, k) for k, v in NICE_TO_UGLY_TIMEZONE_MAPPING.items())


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
        # private API which gives us the schedule
        f"https://calendly.com/api/booking/event_types/{event_id}/calendar/range?timezone={target_timezone}&diagnostics=false&range_start={start_day}&range_end={end_day}"
    )

    if result.status_code != 200:
        print("Error fetching slots")
        return []

    # structure of the response:
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

            # remove weekend dates. I leave some weekend slots on my calendly, but I don't want to send
            # these to folks I'm emailing.
            if spot_start_time.weekday() >= 5:
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


def timezones_for_offset(offset):
    import pytz

    utc_offset = datetime.timedelta(hours=offset, minutes=0)
    now = datetime.datetime.now(pytz.utc)

    return [tz.zone for tz in map(pytz.timezone, pytz.all_timezones_set) if now.astimezone(tz).utcoffset() == utc_offset]


# extracting a TZ identifier from an offset is hard. They aren't standardized and it's a one-to-many mapping
# https://stackoverflow.com/questions/35085289/getting-timezone-name-from-utc-offset
def human_timezone_for_offset(time: datetime.datetime) -> str:
    # TODO there has got to be a better way to do this, seems insane there isn't a package or builtin for this
    timezone_offset = -int(24 - time.utcoffset().seconds / 3600)
    timezone_names = timezones_for_offset(timezone_offset)
    timezone_names = sorted(timezone_names, key=lambda x: len(x))

    timezone_identifier = timezone_names[0]

    timezone_identifier = UGLY_TO_NICE_TIMEZONE_MAPPING.get(timezone_identifier, timezone_identifier)

    # https://stackoverflow.com/questions/31299580/python-print-the-time-zone-from-strftime
    # also, I hate MST vs MT which is why I'm converint ST => T
    timezone_identifier = timezone_identifier.replace("ST", "T")

    return timezone_identifier


def human_readable_slot(slot: dict) -> str:
    # target format: Jan 10th, 7:30pm MT

    start_time = datetime.datetime.fromisoformat(slot["start_time"])
    timezone_identifier = human_timezone_for_offset(start_time)

    start_time_str = start_time.strftime("%b %-d, %-I:%M%p")

    # easiest way to get the am/pm to lowercase is to set the locale to de_DE, but this also messes with month formatting
    # https://stackoverflow.com/questions/38863210/how-to-make-pythons-datetime-object-show-am-and-pm-in-lowercase/38863352
    start_time_str = start_time_str.replace("AM", "am").replace("PM", "pm")

    return f"{start_time_str} {timezone_identifier}"


def calendly_times(duration, days, timezone, after_hour, total, events, slots_per_day, api_key) -> str:
    # TODO not awesome, but this is a quick script and I'm getting lazy
    global calendly
    global calendly_user_uri

    calendly = Calendly(api_key)

    # weirdly enough, we need the URI (not UID) for the user in order to use the calendly API
    calendly_user = calendly.about()
    calendly_user_uri = calendly_user["resource"]["uri"]

    # self documenting, baby
    schedule_range_in_days = days
    number_of_events_to_schedule = events
    number_of_slots_per_event = total

    # not sure why, but "PST" & "CST" are not a valid timezone identifiers either in calendly or python
    timezone = NICE_TO_UGLY_TIMEZONE_MAPPINGg.get(timezone, timezone)

    event_id = event_id_with_duration(duration)
    available_days = get_event_slots(event_id, schedule_range_in_days, duration, timezone, after_hour)

    chosen_slots_by_events: t.List[t.List[dict]] = []
    output = ""

    for _ in range(number_of_events_to_schedule):
        slots_for_event = []

        for day in available_days:
            slots_left = min(slots_per_day, number_of_slots_per_event - len(slots_for_event), len(day["spots"]))

            for _ in range(slots_left):
                slots_for_event.append(day["spots"].pop())

        chosen_slots_by_events.append(slots_for_event)

    for event_slots in chosen_slots_by_events:
        # sort selected slots by time; they were randomized earlier
        for slot in sorted(event_slots, key=lambda slot: slot["start_time"]):
            # target format: "- Jan 5, 5:30pm MT"
            output += f"- {human_readable_slot(slot)}\n"

        output += "\n"

    return output
