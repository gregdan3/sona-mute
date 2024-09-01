# TODO: replace the behavior of main (and gen_sqlite) with some prompts here that
# - let you fetch from various configured sources, specifying a dir
# - let you transform to frequency in the db
# - let you generate a sqlite file
# all as consecutive options you can pick, or
# - separately, let you postprocess pluralkit data, when that's implemented

# STL
import os
import sys
from typing import Any, TypedDict
from datetime import date

# PDM
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.console import Console

# LOCAL
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
}


class SourceAction(TypedDict):
    source: str
    root: str
    to_db: bool
    output: str | None


class SqliteAction(TypedDict):
    filename: str
    root: str


class Actions(TypedDict):
    sources: list[SourceAction]
    frequency: bool
    sqlite: SqliteAction | None


ACTIONS: Actions = {"sources": [], "frequency": False, "sqlite": None}


def today_str():
    return date.today().strftime("%Y-%m-%d")


def get_directory(prompt: str, *args: Any, **kwargs: Any) -> str:
    while True:
        dir = Prompt.ask("Provide a directory: ", *args, **kwargs)
        if os.path.isdir(dir):
            return dir
        CONSOLE.print(f"[red]Error: {dir} is not a valid directory.[/red]")


def get_filename(prompt: str, *args: Any, **kwargs: Any) -> str:
    filename = Prompt.ask("Provide a filename: ", *args, **kwargs)
    return filename


def setup_source():
    source = Prompt.ask("What source?", choices=list(SOURCES.keys()))
    dir = get_directory("Where from?", default=os.getcwd())
    to_db = Confirm.ask("Send to database?")

    output = None
    dest = "db"  # just for presentatoin
    if not to_db:
        output = get_filename("Output where?", default=f"./{source}_{today_str()}.json")
        dest = output

    result = SourceAction(
        {
            "source": source,
            "root": dir,
            "to_db": to_db,
            "output": output,
        }
    )

    ACTIONS["sources"].append(result)
    CONSOLE.print(f"Will fetch {source} data from {dir} and output to {dest}")


def setup_frequency():
    ACTIONS["frequency"] = True
    CONSOLE.print("Will regenerate frequency data on next run")


def setup_sqlite():
    filename = get_filename("Name for SQLite DB?", default=f"{today_str()}.sqlite")
    location = get_directory("Save to where?", default=".")

    ACTIONS["sqlite"] = SqliteAction({"filename": filename, "root": location})
    CONSOLE.print(f"Will generate a SQLite database {filename} at {location}")


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
        setup_source()
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
