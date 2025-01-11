# TODO: replace the behavior of main (and gen_sqlite) with some prompts here that
# - let you fetch from various configured sources, specifying a dir
# - let you transform to frequency in the db
# - let you generate a sqlite file
# all as consecutive options you can pick, or
# - separately, let you postprocess pluralkit data, when that's implemented

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


class SqliteAction(TypedDict):
    filename: str
    filename_trimmed: str
    min_date: datetime
    max_date: datetime
    root: str


class Actions(TypedDict):
    sources: list[SourceAction]
    frequency: bool
    sqlite: SqliteAction | None


ACTIONS: Actions = {"sources": [], "frequency": False, "sqlite": None}


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


def setup_sqlite():
    filename = get_filename("Base name for SQLite DB?", default=f"{today_str()}")
    location = get_directory("Save to where?", default=".")
    min_date = get_date("Minimum date? YYYY-MM", format="%Y-%m", default="2001-08")
    max_date = get_date("Maximum date? YYYY-MM", format="%Y-%m", default="2024-08")

    full_filename = filename + "-full.sqlite"
    trimmed_filename = filename + "-trimmed.sqlite"

    ACTIONS["sqlite"] = SqliteAction(
        {
            "filename": full_filename,
            "filename_trimmed": trimmed_filename,
            "min_date": min_date,
            "max_date": max_date,
            "root": location,
        }
    )
    CONSOLE.print(
        f"Will generate SQLite db at {location}/{full_filename} and {location}/{trimmed_filename} with data from {min_date} to {max_date}"
    )


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

    if sqlite := ACTIONS["sqlite"]:
        path = os.path.join(sqlite["root"], sqlite["filename"])
        CONSOLE.print(f"Building SQLite database {path}")


def main_menu():
    display_choices()
    CONSOLE.print(Panel("Main Menu", expand=False))
    options = [
        "Fetch new data",
        "Calculate Frequencies",
        "Output to SQLite",
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
        setup_sqlite()
    elif choice == 4:
        return True
    elif choice == 5:
        CONSOLE.print("Shutting down!")
        sys.exit()
    return False


def menu_handler():
    while True:
        if main_menu():
            break
        if not Confirm.ask("\nDo you want to perform another action?"):
            break
    return ACTIONS


if __name__ == "__main__":
    while True:
        if main_menu():
            break
        if not Confirm.ask("\nDo you want to perform another action?"):
            break
    CONSOLE.print("[bold green]Goodbye![/bold green]")
