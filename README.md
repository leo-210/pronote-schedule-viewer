# Pronote Schedule Viewer

This program prints the current lesson, the next lesson of the day or pause,
and is directly connected to pronote thanks to 
[PronotePy](https://github.com/bain3/pronotepy).

This was inspired by [Gilles Castel's](https://castel.dev/) workflow 
(on [this post]([https://castel.dev/post/lecture-notes-3/](https://castel.dev/post/lecture-notes-3/#automatically-changing-the-active-course))). I highly recommend
that you check his blog if you are interested by writing in 
[LaTeX](https://en.wikipedia.org/wiki/LaTeX).

This can be used with [Polybar](https://github.com/polybar/polybar) for example.

### Examples :

Here are some possible outputs :
- **FRANÇAIS**. Fin dans **25 min**.
- **PHYSIQUE-CHIMIE**. Fin dans **8 min**. Suivant : **MATHEMATIQUES** après **30 min** de pause.
- **PHILOSOPHIE** dans **1 h 43 min**.

## Installation

First, make sure [Python 3](https://www.python.org/downloads/) is installed
on your system. Then clone this repository, and run on Linux or MacOS :
```
python3 -m pip install -r requirements.txt
```
Or on Windows :
```
py -m pip install -r requirements.txt
```


## Usage

Check out the `--help` command to list all the possible arguments :
```
python3 ./pronote_schedule_viewer --help
```

### Basics

Run the command :
```
python3 ./pronote_schedule_viewer --username <username> --password <password> --link <link>
```
Where `<username>` is your Pronote username and `<password>`is 
your Pronote password. `<link>` is the link of the website you 
use to connect to Pronote 
(e.g. `https://0000000x.index-education.net/pronote/eleve.html?login=true`)

If you don't pass one of these 3 arguments, the program will check for the 
environment variables `PRONOTE_LOGIN`, `PRONOTE_PASSWORD` and `PRONOTE_LINK`, 
which can be defined in a `.env` file. 


### Other arguments

Here are the most useful arguments.

#### Academy

You can specify the academy you're in with :
``` 
--academy <academy>
```

This will take into account the academy you're in for holidays (if the program 
is run during holidays, it will not use the Pronote "API").

*([List of all possible academies](https://www.education.gouv.fr/les-regions-academiques-academies-et-services-departementaux-de-l-education-nationale-6557))*

If you don't pass this arguments, the program will check for the 
environment variable `ACADEMY`, 
which can be defined in a `.env` file. 

#### Login every

By default, the program will only use the pronote API every 5 calls, 
because there's no need to refresh very frequently (usually the schedule 
does not change in the day). You can change this value with :
``` 
--login-every <amount>
```
When not using the pronote API, it will use the cache. To prevent that,
either pass `0` to `--login-every` (this will still save to cache), or
disable the cache completely with `--no-cache`.

#### Date

For testing purposes, you can make the program think today is another day and time with :
``` 
--date <date>
```
The `<date>` must respect the [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601)
date format.
