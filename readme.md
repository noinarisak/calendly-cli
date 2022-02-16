# Calendly on the Command Line

## Why?

I had a specific problem I wanted to solve:

* Lots of scheduling emails each day
* Scheduling emails between more than one party. Normally, I'd just send my calendly link, but that doesn't work well with groups of people.
* I *hate* finding open times in my calendar, especially if I'm sending multiple time options to multiple people. It's weirdly time consuming for me, mainly because I have complex "rules" for calendaring to coordinate between family life, day-job, personal committments, and side projects.

The solution? A CLI tool to spit out a bunch of open times in my calendar.

## Implementation Details

There are some specific features I wanted:

*

## Usage

```
Usage: cli.py [OPTIONS]

  Generate time options based off of a calendly account

Options:
  --duration INTEGER       Number of minutes to schedule  [default: 30]
  --days INTEGER           Number of days in advance to pick from  [default:
                           30]
  --timezone TEXT          Default timezone to pick times from  [default:
                           America/Denver]
  --after-hour INTEGER     Only pick events after this hour (24hr format)
  --total INTEGER          Number of slots per event  [default: 5]
  --events INTEGER         Number of events to schedule  [default: 3]
  --slots-per-day INTEGER  Number of slots per day  [default: 3]
  --api-key TEXT           API key. Sourced from CALENDLY_API_KEY as well
  --help                   Show this message and exit.
```

## Development

```shell
poetry install
poetry shell

# either use ipython with `run main.py` to play around with the code
ipython

# or run the command directly and start tinkering
```

#### API Hacking

You can play with the calendly API using [httpie](https://httpie.io) really easily.

```shell
source .env

http GET https://api.calendly.com/users/me Authorization:"Bearer $CALENDLY_KEY" Content-Type:application/json
```

The `"current_organization"` key contains the org URL which doesn't seem to be exposed in the UI at all (at least on basic accounts).
