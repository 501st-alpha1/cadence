# cadence

A plain-text, git-native job search tracker.

## Design principles

- **Plain text first** — all data is TOML files, human-readable and diffable
- **Local first** — everything lives on your machine; git is the sync layer
- **No general task system** — only job-search-specific workflows
- **Three repos** — code (`cadence`), public data (`cadence-data`), private data (`cadence-private`)

## Installation

```sh
git clone https://github.com/501st-alpha1/cadence.git
cd cadence
pip install -e .
cadence init   # creates ~/.config/cadence/config.toml
```

Edit `~/.config/cadence/config.toml` to point at your data repos:

```toml
[repos]
public  = "~/jobs/cadence-data"
private = "~/jobs/cadence-private"
```

## Data repos

```sh
mkdir -p ~/jobs/cadence-data ~/jobs/cadence-private
cd ~/jobs/cadence-data   && git init
cd ~/jobs/cadence-private && git init
```

The public repo holds companies and job descriptions — no personal information.
The private repo holds everything else: applications, people, messages, offers, take-homes, references.

## Daily workflow

```sh
cadence next          # see what needs attention today
```

## Command reference

### Companies (public repo)
```sh
cadence company add [--name] [--domain] [--tags] [--notes]
cadence company show <name-prefix-or-id>
cadence company list [--tag <tag>]
```

### Job descriptions (public repo)
```sh
cadence jd add [--company] [--title] [--url] [--source] [--closes]
cadence jd show <id>
cadence jd list [--company] [--open]
```

### Applications (private)
```sh
cadence app add [--company] [--jd] [--role] [--source] [--resume] [--status]
cadence app show <id>
cadence app list [--status] [--company] [--active]
cadence app status <id> <new-status>
cadence app submit <id> [--notes]    # started → applied
cadence app cancel <id> [--notes]    # started → canceled (abandoned before submitting)
cadence app note <id>        # opens $EDITOR
cadence app cover <id>       # compose/edit cover letter in $EDITOR
```

Valid statuses: `saved` `started` `applied` `phone_screen` `interview` `offer`
`accepted` `withdrawn` `rejected` `ghosted` `declined_offer` `position_filled` `paused` `canceled`

### People (private)
```sh
cadence person add [--name] [--company] [--role] [--email] [--linkedin] [--notes]
cadence person show <name-prefix-or-id>
cadence person list [--company]
```

### Messages (private)
```sh
cadence msg add [--app] [--person] [--direction] [--channel] [--subject] [--body] [--request-doc]
cadence msg list [--app] [--person]
```

### Interviews
```sh
cadence interview add <app-id> [--round] [--scheduled] [--notes]
cadence interview session <app-id> <interview-id> [--interviewer] [--format] [--notes]
cadence interview complete <app-id> <interview-id> [--notes]
cadence interview thankyou <app-id> <interview-id>
```

### Offers
```sh
cadence offer add <app-id> [--compensation] [--expires] [--notes]
cadence offer revise <app-id> [--compensation] [--notes]
cadence offer show <app-id>
cadence offer accept <app-id>
cadence offer decline <app-id> [--notes]
```

### References
```sh
cadence ref add <person-name-or-id> [--relationship] [--known-for] [--notes]
cadence ref list
cadence ref use <app-id> <ref-id> [--notes]
```

### Stats & maintenance
```sh
cadence stats [--by-source] [--by-month]
cadence validate        # cross-repo FK integrity check
```

## Configuration

```toml
[repos]
public  = "~/jobs/cadence-data"
private = "~/jobs/cadence-private"

[thresholds]
message_followup_days     = 5
application_followup_days = 14
ghosted_days              = 30
interview_thankyou_hours  = 48
interview_prep_days       = 2

[resume]
default_version = "v1"
```

## Running tests

```sh
python -m unittest tests.test_core -v
```
