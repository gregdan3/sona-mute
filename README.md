# sona-mute

<div align="center">

<!-- ![Test workflow for this library](https://github.com/gregdan3/sona-mute/workflows/Tests/badge.svg) -->

</div>

## What is sona mute?

This tool, "Many-knowledge," takes in messages in various formats and filters/scores them with [my library "sona toki"](https://github.com/gregdan3/sona-toki). Then the result is inserted to [EdgeDB](https://www.edgedb.com/). From there, you can count the frequency of [n-grams](https://en.wikipedia.org/wiki/N-gram) up to length 6, then export that info to a SQLite database... [for reasons](https://github.com/phiresky/sql.js-httpvfs).

## What platforms are supported?

- Discord, via the [DiscordChatExporter by Tyrrrz](https://github.com/Tyrrrz/DiscordChatExporter).
- Telegram, via its desktop-native export functionality.
- Reddit, via [the work of /u/Watchful1](https://www.reddit.com/r/pushshift/comments/1akrhg3/separate_dump_files_for_the_top_40k_subreddits/)

## Quick Start

Assuming you have the above data,

Install your dependencies:

```sh
pdm install
```

Run the main script:

```sh
pdm run python ./src/sonamute/__main__.py
```

Then follow the prompts:

### Fetch New Data

Specify the format of your data, then where it is on your filesystem.

### Calculate Frequencies

If you've already fetched data, or previously specified to fetch data, this will calculate frequencies from your data.

### Output to SQLite

Provide a filename for your SQLite file, then a path for it.

### Start executing actions

This, or answering "no" to "Do you want to perform another action?" will run the specified actions.

## Future Work

### Tests

"hey why doesn't this code have tests" i had more excitement than foresight when i wrote this code

### More platforms

This is in order of how important the platform is to include!

#### forums.tokipona.org

To an outsider, it may seem odd to want to include a specific singular forum in this data- but [this forum](http://forums.tokipona.org) is important because it was active from 1 Oct 2009 to, mostly, mid-2020. This period is virtually unrepresented in the data I currently have to, and this space is one of only a handful that were in use during this time. As such, this forum is highly important to the history of Toki Pona.

I do already have a backup of this data, but actually adding it to the database is difficult. I lack user IDs, post IDs, and properly formatted quotes. That's because I used [this backup tool](https://github.com/Dascienz/phpBB-forum-scraper), and frankly, it's not very good. I have thus far not needed to make my own scrapers for any of the data I've collected, but this one may be different. If you have a better phpBB scraper, or otherwise a cleaner capture of this data, please reach out!

#### tokipona@yahoogroups.com

From some time in 2002 until Oct 1 2009, the Toki Pona yahoo group was one of very few spaces where Toki Pona was regularly spoken, and it appears to have been the most popular- the IRC channel could have been more popular, but it wasn't preserved that I'm aware of. Fortunately, the entire yahoo group is backed up on the forum above. Unfortunately, its formatting is mangled badly because its newlines are missing. If that weren't enough, its formatting is already highly inconsistent due to the unstable nature of email from provider to provider. Including it in the database as-is would be messy, at best; it needs some pre-processing effort.

#### Facebook

There are several Toki Pona communities on Facebook, [here](https://www.facebook.com/groups/sitelen), [here](https://www.facebook.com/groups/1590434267942176/), [here](https://www.facebook.com/groups/543153192468898/), and [here](https://www.facebook.com/groups/2424398856/). The majority of their activity is in a period similar to that of Discord- that is, from 2020 onward- but they have much more pre-2020 activity than most other communities that existed around this time.

#### LiveJournal

There are at least two livejournal blogs that focused on Toki Pona, [here](https://tokipona.livejournal.com/) and [here](https://ru-tp.livejournal.com/), which were active in a similar time period to the forum.

#### kulupu.pona.la

[kulupu.pona.la](https://archive.org/details/kulupu.pona.la) was a forum hosted by [mazziechai](https://github.com/mazziechai/) which closed abruptly in November 2023 due to challenging circumstances. The forum was archived fully by Mazzie before the shutdown, but the format is pure HTML, making it a bit obnoxious to get the necessary data out of it.

#### Reddit (subreddits other than /r/tokipona)

### Better detection of bots (in Discord)

In Discord, detecting bot messages is normally easy. Discord delivers a field that tells you whether the message is from a bot, and whether the message is from a webhook- and if the message is from a webhook, it is also considered to be from a bot.

Here's the trouble: [PluralKit](https://pluralkit.me/) sends messages via webhooks, and so do many other tools such as those that copy Github notifications into Discord.

Currently, I count all user messages and all webhook messages so that I don't miss pluralkit messages, but this means

I'd like to take all my webhook message IDs and ask the PluralKit API if they're from PluralKit.

### Weekly (or 4-weekly) resolution instead of monthly

Currently, I use a monthly resolution for all my data. This is fine for graphs that consider an n-gram's occurrences against the total number of same-length n-grams in a period, but can introduce bias against shorter months or months with fewer active periods (e.g. weekends) if viewing the data in an absolute way i.e. seeing the raw numbers. This bias can be corrected by choosing a time resolution which is equally sized.

### Inserting "start of sentence" and "end of sentence" markers

While preparing for presentation during [suno pi toki pona](https://suno.pona.la/2024/), I realized I could insert `^` and `$` as sentence start and end markers while counting frequency data, since they cannot appear in a processed sentence. This would change the relationship between minimum sentence length and phrase length, but allow for useful searches like `anu seme $, anu seme - anu seme $`- comparing occurrences of "anu seme" at the end of the sentence with occurrences of it anywhere else.

### Faster writing to SQLite

There are two places to save time with the data I'm writing to SQLite:

1. If I switch from the SQLAlchemy ORM to Core, I reportedly can get as much as a 10x speedup. What.
2. I'm currently writing all frequency information to the SQLite database then, in post-processing, filtering down to words/phrases with at least 40 occurrences. I can save as much as 86% of my effort (estimating by disk space, we go from ~3.1GB to ~420MB) if I instead make queries to EdgeDB which don't include information I don't intend to deliver. This will make the queries themselves slower, but that's probably fine.
