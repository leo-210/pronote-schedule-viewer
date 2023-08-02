import argparse
import datetime
import os
import pickle
from typing import List

import pronotepy
from requests import get

# If the pronote start and end of each lesson is off
# start of lesson (in minutes): offset
OFFSETS = {
    "start": {},
    "end": {
        9 * 60: -5,
        11 * 60: 10,
        12 * 60: 10,
        13 * 60: 10,
        14 * 60: 10,
        15 * 60: 10,
        17 * 60: 15,
        18 * 60: 15
    }
}


class CacheEntry:
    def __init__(self, date: datetime.date, l: List[pronotepy.Lesson]):
        self.date = date
        self.lessons = l
        self.count: int = 0

    def format_date(self) -> str:
        return self.date.strftime("%Y%m%d")

    def count_increment(self) -> None:
        self.count += 1

    def count_reset(self) -> None:
        self.count = 0

    def __repr__(self) -> str:
        return f"{self.format_date()} : {self.lessons}"


def bold(text: str) -> str:
    return "\033[1m" + text + "\033[0m"


def time_left(delta: datetime.timedelta) -> str:
    if delta.seconds >= 3600:
        s = f"{delta.seconds // 3600} h {delta.seconds // 60 % 60} min"
    else:
        s = f"{delta.seconds // 60 % 60} min"

    return s


def get_classroom(l: pronotepy.Lesson) -> str:
    if l.classroom:
        return f" en {bold(l.classroom)}"
    return ""


now = datetime.datetime.utcnow()

parser = argparse.ArgumentParser(
    prog="Pronote Schedule Viewer",
    description="Shows next lesson directly from pronote")

parser.add_argument("--username", "--login", "-u", dest="login",
                    help="your pronote username. Overwrites the env var 'PRONOTE_LOGIN'.")
parser.add_argument("--password", "-p", dest="password",
                    help="your pronote password. Overwrites the env var 'PRONOTE_PASSWORD'.")
parser.add_argument("--link", "-l", dest="link",
                    help="the link to the pronote login web page. Overwrites the env var 'PRONOTE_LINK'.")
parser.add_argument("--date", "-d",
                    help="sets the date, defaults to today. Must respect the ISO 8601 format.")
parser.add_argument("--login-every", type=int, default=5, dest="login_every",
                    help="only login to pronote every x times your run the program, "
                         "instead it looks in the cache if it exists. Defaults to 5.")
parser.add_argument("--verbose", "-v", action="store_true")
parser.add_argument("--no-cache", action="store_true", dest="no_cache",
                    help="prevents the program from using the cache.")
parser.add_argument("--purge-to", default=now.strftime("%Y-%m-%d"), dest="purge",
                    help="to which date (not included) the program should delete cache, defaults to today. "
                         "Must respect the ISO 8601 format.")
parser.add_argument("--no-purge", action="store_true", dest="no_purge",
                    help="prevents the program from purging the cache.")
parser.add_argument("--academy",
                    help="The academy your in (to check if you're currently in vacation). Must respect case.")
parser.add_argument("--ignore-vacation", action="store_true", dest="ignore_vacation")

args = parser.parse_args()

verbose = args.verbose
if args.date:
    now = datetime.datetime.fromisoformat(args.date)


cache_dir = os.path.join(__file__, "..", "cache")
if not args.no_purge:
    purge_to = datetime.datetime.fromisoformat(args.purge).date()

    try:
        cache_files = os.listdir(cache_dir)

        for file in cache_files:
            if not (file.isnumeric() and len(file) == 8):
                continue
            if datetime.date.fromisoformat(file) < purge_to:
                try:
                    os.remove(os.path.join(cache_dir, file))
                    if verbose:
                        print(f"purge : removed {file}.")
                except OSError:
                    if verbose:
                        print(f"purge : could not remove {file}.")
    except OSError:
        # The cache directory (probably) doesn't exist
        pass

if now.hour >= 19:
    if verbose:
        print("hour greater than 18 : not doing anything.")
    exit(0)
if now.hour < 7:
    if verbose:
        print("hour lower than 7 : not doing anything.")
    exit(0)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    if verbose:
        print("module 'python-dotenv' not found.")

if not args.ignore_vacation:
    academy = None
    if args.academy:
        academy = args.academy
    elif "ACADEMY" in os.environ:
        academy = os.environ["ACADEMY"]
    else:
        parser.error(
            "academy was not specified and 'ACADEMY' environment variable is not defined (.env files are "
            "supported).")

    results = None
    try:
        r = get("https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-calendrier-scolaire/facets?"
                f"where=%22{academy}%22&"
                "facet=location")

        if len(r.json()["facets"][0]["facets"]) == 0:
            if verbose:
                print("invalid academy name.")
        else:
            academy = (r.json()["facets"][0]["facets"][0]["name"]).lower()

            with open(os.path.join(cache_dir, str(now.year) + academy), "rb") as f:
                results = pickle.load(f)
    except IOError:
        if verbose:
            print(f"could not read cache file '{str(now.year) + academy}' or it doesn't exist. Creating it...")

        r = get("https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-calendrier-scolaire/records?"
                f"select=start_date%2C%20end_date&"
                f"where=%22{academy}%22AND%22{str(now.year)}%22AND%20NOT%22Enseignants%22&"
                "limit=20")
        results = r.json()["results"]
        os.makedirs(cache_dir, exist_ok=True)
        try:
            with open(os.path.join(cache_dir, str(now.year) + academy), "wb") as f:
                pickle.dump(results, f)
        except IOError:
            if verbose:
                print("could not create cache file for vacations")
            pass

    if results is not None:
        for vacation in results:
            vacation_start = datetime.datetime.fromisoformat(vacation["start_date"])
            vacation_end = datetime.datetime.fromisoformat(vacation["end_date"])

            if vacation_start.date() < now.date() <= vacation_end.date():
                if verbose:
                    print("currently in vacation : not doing anything.")
                exit(0)


login = None
if args.login:
    login = args.login
elif "PRONOTE_LOGIN" in os.environ:
    login = os.environ["PRONOTE_LOGIN"]
elif "PRONOTE_USERNAME" in os.environ:
    login = os.environ["PRONOTE_USERNAME"]
else:
    parser.error("login was not specified and 'PRONOTE_LOGIN' environment variable is not defined (.env files are "
                 "supported).")

password = None
if args.password:
    password = args.password
elif "PRONOTE_PASSWORD" in os.environ:
    password = os.environ["PRONOTE_PASSWORD"]
else:
    parser.error(
        "password was not specified and 'PRONOTE_PASSWORD' environment variable is not defined (.env files are "
        "supported).")

link = None
if args.link:
    link = args.link
elif "PRONOTE_LINK" in os.environ:
    link = os.environ["PRONOTE_LINK"]
else:
    parser.error("link was not specified and 'PRONOTE_LINK' environment variable is not defined (.env files are "
                 "supported).")

if not args.no_cache:
    lessons = None
    cache_entry = None
    cache_path = os.path.join(cache_dir, now.date().strftime("%Y%m%d"))

    if args.login_every > 1:
        try:
            with open(cache_path, "rb") as f:
                cache_entry = pickle.load(f)

            lessons = cache_entry.lessons
        except IOError:
            if verbose:
                print(f"cache file '{now.date().strftime('%Y%m%d')}' doesn't exist.")

    if lessons is None or \
            (cache_entry is not None and cache_entry.count >= args.login_every):
        if verbose:
            if lessons is not None:
                print(f"counter exceeded {args.login_every}.")
            print(f"connecting to pronote...")

        client = pronotepy.Client(link, username=login, password=password)
        if not client.logged_in:
            if verbose:
                print("could not connect to pronote.")
            exit(1)

        if verbose and lessons is None:
            print(f"creating file '{now.date().strftime('%Y%m%d')}'...")

        lessons = client.lessons(now.date())
        cache_entry = CacheEntry(now, lessons)

    cache_entry.count_increment()

    os.makedirs(cache_dir, exist_ok=True)
    try:
        with open(cache_path, "wb") as f:
            pickle.dump(cache_entry, f)
    except IOError:
        if verbose:
            print("could not create lessons cache file")

else:
    if verbose:
        print(f"connecting to pronote...")
    client = pronotepy.Client(link, username=login, password=password)
    if not client.logged_in:
        if verbose:
            print("could not connect to pronote.")
        exit(1)
    lessons = client.lessons(now.date())

for i, lesson in enumerate(lessons):
    if (lesson.start.hour * 60 + lesson.start.minute) in OFFSETS["start"]:
        lessons[i].start += datetime.timedelta(
            minutes=OFFSETS["start"][lesson.start.hour * 60 + lesson.start.minute])
    if (lesson.end.hour * 60 + lesson.end.minute) in OFFSETS["end"]:
        lessons[i].end += datetime.timedelta(
            minutes=OFFSETS["end"][lesson.end.hour * 60 + lesson.end.minute])

lessons.sort(key=lambda x: x.start, reverse=True)

if len(lessons) == 0:
    if verbose:
        print("no lessons today.")
    exit(0)


lesson = lessons.pop()
end_of_day = False
while lesson.end < now or lesson.canceled:
    if len(lessons) == 0:
        end_of_day = True
        break
    lesson = lessons.pop()

if end_of_day:
    if verbose:
        print("no more lessons")
    exit(0)

if lesson.start > now:
    print(f"{bold(lesson.subject.name)} dans {bold(time_left(lesson.start - now))}{get_classroom(lesson)}.")
    exit(0)

ends_in = ""
next_lesson_str = ""

if (lesson.end - now).seconds <= 30 * 60:
    ends_in = "Fin dans " + bold(time_left(lesson.end - now))

    if len(lessons) != 0 and (lesson.end - now).seconds <= 10 * 60:
        next_lesson = lessons.pop()

        if next_lesson.canceled:
            next_lesson_str = f"Suivant : {bold(time_left(next_lesson.end - next_lesson.start))} de pause " \
                              f"({bold(next_lesson.subject.name)} annulé)"
        else:
            next_lesson_str = f"Suivant : {bold(next_lesson.subject.name)}{get_classroom(next_lesson)}"
            if (next_lesson.start - now).seconds >= 6 * 60:
                next_lesson_str += f" après {bold(time_left(next_lesson.start - lesson.end))} de pause"

result = f"{bold(lesson.subject.name)}"
if ends_in:
    result += f" : {ends_in}."
    if next_lesson_str:
        result += f" {next_lesson_str}."
print(result)
