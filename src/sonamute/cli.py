# STL
import os
import sys
from typing import Any, TypedDict, cast
from datetime import UTC, date, tzinfo, datetime

# PDM
import yaml
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.console import Console

# LOCAL
from sonamute.sources.poki import PokiLapoFetcher
from sonamute.sources.forum import ForumFetcher
from sonamute.sources.reddit import RedditFetcher
from sonamute.sources.discord import DiscordFetcher
from sonamute.sources.generic import PlatformFetcher
from sonamute.sources.youtube import YouTubeFetcher
from sonamute.sources.telegram import TelegramFetcher

CONSOLE = Console()

SOURCES: dict[str, type[PlatformFetcher]] = {
    "discord": DiscordFetcher,
    "telegram": TelegramFetcher,
    "reddit": RedditFetcher,
    "youtube": YouTubeFetcher,
    "forum": ForumFetcher,
    "poki": PokiLapoFetcher,
}


class SourceAction(TypedDict):
    source: str
    root: str
    to_db: bool
    output: str | None


class Actions(TypedDict):
    sources: list[SourceAction]
    frequency: bool


ACTIONS: Actions = {"sources": [], "frequency": False}


def today_str():
    return date.today().strftime("%Y-%m-%d")


def get_directory(
    prompt: str,
    *args: Any,
    must_exist: bool = False,
    **kwargs: Any,
) -> str:
    while True:
        dir = Prompt.ask(prompt, *args, **kwargs)
        if not must_exist and dir:
            return dir
        if must_exist and os.path.isdir(dir):
            return dir
        CONSOLE.print(f"[red]Error: {dir} is not a valid directory.[/red]")


def get_filename(
    prompt: str,
    *args: Any,
    must_exist: bool = False,
    **kwargs: Any,
) -> str:
    while True:
        filename = Prompt.ask(prompt, *args, **kwargs)
        if not must_exist and filename:
            return filename
        if must_exist and os.path.isfile(filename):
            return filename
        CONSOLE.print(f"[red]Error: {filename} is not an existing file.[/red]")


def get_date(
    prompt: str,
    *args: Any,
    format: str = "%Y-%m-%d",
    **kwargs: any,
) -> datetime:
    while True:
        date_str = Prompt.ask(prompt, *args, **kwargs)
        try:
            date = datetime.strptime(date_str, format)
            date = date.replace(tzinfo=UTC)

            return date
        except ValueError:
            # Handle invalid date format
            CONSOLE.print(
                f"[red]Error: {date_str} is not a valid date. Please use the format {format}.[/red]"
            )


def add_source(source_action: SourceAction):
    source = source_action["source"]
    dir = source_action["root"]
    to_db = source_action["to_db"]
    dest = source_action["output"]
    if to_db:
        dest = "db"

    ACTIONS["sources"].append(source_action)
    CONSOLE.print(f"Will fetch {source} data from {dir} and output to {dest}")


def setup_source_from_config():
    output = get_filename("Provide config", default="./sources.yml", must_exist=True)
    with open(output) as f:
        configs = cast(list[SourceAction], yaml.safe_load(f))

    for config in configs:
        result = SourceAction(**config)
        add_source(result)


def setup_one_source():
    source = Prompt.ask("What source?", choices=list(SOURCES.keys()))
    dir = get_directory("Where from?", default=os.getcwd())
    to_db = Confirm.ask("Send to database?")

    output = None
    if not to_db:
        output = get_filename("Output where?", default=f"./{source}_{today_str()}.json")
    result = SourceAction(
        {
            "source": source,
            "root": dir,
            "to_db": to_db,
            "output": output,
        }
    )
    add_source(result)


def setup_sources():
    from_config = Confirm.ask("From config?")
    if from_config:
        setup_source_from_config()
    else:
        setup_one_source()


def setup_frequency():
    ACTIONS["frequency"] = True
    CONSOLE.print("Will regenerate frequency data on next run")


def display_choices():
    if sources := ACTIONS["sources"]:
        for source in sources:
            dest = "db"
            if not source["to_db"]:
                dest = source["output"]
            CONSOLE.print(
                f"Sending {source['source']} data from {source['root']} to {dest}"
            )

    if ACTIONS["frequency"]:
        CONSOLE.print("Regenerating frequency data from database")


def main_menu():
    display_choices()
    CONSOLE.print(Panel("Main Menu", expand=False))
    options = [
        "Fetch new data",
        "Calculate Frequencies",
        "Start executing actions",
        "Cancel",
    ]
    for i, option in enumerate(options, start=1):
        CONSOLE.print(f"{i}. {option}")

    choice = IntPrompt.ask(
        "\nChoose an option", choices=[str(i + 1) for i in range(len(options))]
    )
    choice = int(choice)

    if choice == 1:
        setup_sources()
    elif choice == 2:
        setup_frequency()
    elif choice == 3:
        return True
    elif choice == 4:
        CONSOLE.print("Shutting down!")
        sys.exit()
    return False


def menu_handler():
    while not main_menu():
        pass
    return ACTIONS


if __name__ == "__main__":
    while True:
        if main_menu():
            break
        if not Confirm.ask("\nDo you want to perform another action?"):
            break
    CONSOLE.print("[bold green]Goodbye![/bold green]")
