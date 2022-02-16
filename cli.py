import os

import click
from dotenv import load_dotenv

import main

load_dotenv()


@click.command(short_help="Generate time options based off of a calendly account")
@click.option("--duration", default=30, help="Number of minutes to schedule", show_default=True, type=int)
@click.option("--days", default=30, help="Number of days in advance to pick from", show_default=True, type=int)
@click.option("--timezone", default="America/Denver", help="Default timezone to pick times from", show_default=True, type=str)
@click.option("--after-hour", default=None, help="Only pick events after this hour (24hr format)", show_default=True, type=int)
@click.option("--total", default=5, help="Number of slots per event", show_default=True, type=int)
@click.option("--events", default=3, help="Number of events to schedule", show_default=True, type=int)
@click.option("--slots-per-day", default=3, help="Number of slots per day", show_default=True, type=int)
@click.option("--api-key", default=None, help="API key. Sourced from CALENDLY_API_KEY as well")
def cli(**kwargs):
    if not kwargs["api_key"]:
        kwargs["api_key"] = os.getenv("CALENDLY_API_KEY")

    print(main.calendly_times(**kwargs))


if __name__ == "__main__":
    cli()
