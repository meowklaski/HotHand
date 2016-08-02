from typing import *
from urllib.request import urlopen
import bs4
from bs4 import BeautifulSoup

# away -> left, home -> right

"http://espn.go.com/nba/team/schedule/_/name/sa/year/2016/seasontype/2/san-antonio-spurs"


def get_game_ids(team_abbrev: str, team_name: str, end_year: Optional[Union[str, int]]=None) \
        -> Dict[str, Tuple[str, ...]]:
    """ Returns the chronologically-ordered game-IDs for the regular and post season of the specified year (>= 2003).

        Parameters
        ----------
        team_abbrev: str
        team_name: str
        end_year: Optional[str, int]


        Returns
        -------
        Dict[str, Tuple[str, ...]]
            Dictionary with keys "regular" and "post", each mapping to a tuple of game IDS

        Examples
        --------
        >>> from scraper import get_game_ids
        >>> game_ids = get_game_ids("sa", "San Antonio Spurs", 2014)  # games for the 2013-2014 season
    """
    team_name = '-'.join(i.lower() for i in team_name.split())
    url_base = "http://espn.go.com/nba/team/schedule/_/name/{}/".format(team_abbrev)
    if end_year:
        url_base += "year/{}/".format(end_year)

    out = {}

    reg_season = url_base + "seasontype/2/" + team_name
    post_season = url_base + team_name

    soup = BeautifulSoup(urlopen(reg_season).read(), 'html.parser')
    scores = soup.find_all("li", class_="score")
    out["regular"] = tuple(score_.a["href"].rsplit('/', 1)[-1] for score_ in scores)

    soup = BeautifulSoup(urlopen(post_season).read(), 'html.parser')
    scores = soup.find_all("li", class_="score")
    out["post"] = tuple(score_.a["href"].rsplit('/', 1)[-1] for score_ in scores)
    return out


def get_roster(team_abbrev: str, team_name: str) -> Tuple[str, ...]:
    """ Return team roster from latest season.

        Examples
        --------
        >>> from scraper import get_roster
        >>> spurs_roster = get_roster("sa", "San Antonio Spurs")
        """
    team_name = '-'.join(i.lower() for i in team_name.split())
    url_base = "http://espn.go.com/nba/team/stats/_/name/{}/".format(team_abbrev)
    roster = set([])

    # regular season + post season
    urls = [url_base + "seasontype/2/" + team_name, url_base + team_name]

    for url in urls:
        soup = BeautifulSoup(urlopen(url).read(), 'html.parser')
        sub_soup = soup.find("div", class_="mod-container mod-table")
        for item in sub_soup.find("table").find_all("a"):
            if "player" in item["href"]:
                roster.add(item.text)
    return tuple(roster)


def get_game_data(game_id: Union[str, int], team_abbrev: str) -> Dict[str, List[int]]:
    """ Returns a mapping of a player's name to his sequence of makes/misses in that game.

        Examples
        --------
        >>> from scraper import get_game_data
        >>> data = get_game_data(400827900, "sa") # Spurs vs OKC season opener

        Notes
        -----
        +/- 1 -> made/missed free throw
        +/- 2 -> made/missed two-point attempt
        +/- 3 -> made/missed two-point attempt

        get_game_data(id_, abbrev)["team"] -> makes/miss sequence for full team"""
    team_abbrev = team_abbrev.lower()
    game_url = 'http://espn.go.com/nba/playbyplay?gameId={}'.format(game_id)
    soup = BeautifulSoup(urlopen(game_url).read(), 'html.parser')
    playbyplay = game_log(soup)
    attempt_log = {"team": []}
    for entry in playbyplay:
        play_items = play_items_from_log_entry(entry)
        if not play_items or possession(play_items) != team_abbrev:
            continue

        text = play_text(play_items)
        make = is_make(text)
        if make is None:
            continue

        playmaker = player(text)
        value = int(point_attempt(text)) if make else -1 * int(point_attempt(text))
        try:
            attempt_log[playmaker].append(value)
        except KeyError:
            attempt_log[playmaker] = [value]
        finally:
            attempt_log["team"].append(value)
    return attempt_log


# play-by-play url http://espn.go.com/nba/playbyplay?gameId=


def game_log(playbyplay_soup: bs4.BeautifulSoup) -> bs4.element.ResultSet:
    """ Returns full gamelog from espn-go play-by-play site

        Examples
        --------
        >>> from bs4 import BeautifulSoup
        >>> response = urlopen('http://espn.go.com/nba/playbyplay?gameId=400827900') # Spurs vs Thunder
        >>> soup = BeautifulSoup(response.read(), 'html.parser')
        >>> log = game_log(soup)"""
    return playbyplay_soup.find("div", id="gamepackage-qtrs-wrap").find_all("tr")


def play_text(play_items: bs4.element.ResultSet) -> str: return play_items[2].text


def is_make(play_text_: str) -> Union[bool, None]:
    if "makes" in play_text_:
        return True
    if "misses" in play_text_:
        return False
    return None


def play_items_from_log_entry(entry: bs4.element.Tag) -> bs4.element.ResultSet: return entry.find_all("td")


def player(play_text_: str) -> str: return ' '.join(play_text_.split()[:2])


def point_attempt(play_text_: str) -> int:
    """ Returns the value of a score attempt (regardless of make or miss)

        Examples
        --------
        >>> from bs4 import BeautifulSoup
        >>> response = urlopen('http://espn.go.com/nba/playbyplay?gameId=400827900') # Spurs vs Thunder
        >>> soup = BeautifulSoup(response.read(), 'html.parser')
        >>> playbyplay = game_log(soup)
        >>>
        >>> for entry in playbyplay:
        >>>     play_items = play_items_from_log_entry(entry)
        >>>     if play_items:
        >>>         text = play_text(play_items)
        >>>         value = point_attempt(text)
        """
    if "three" in play_text_:
        return 3
    if "free" in play_text_:
        return 1
    return 2


def possession(play_items: bs4.element.ResultSet) -> str:
    """ Returns the team (abbreviated name) with possession.

        Examples
        --------
        >>> from bs4 import BeautifulSoup
        >>> response = urlopen('http://espn.go.com/nba/playbyplay?gameId=400827900') # Spurs vs Thunder
        >>> soup = BeautifulSoup(response.read(), 'html.parser')
        >>> playbyplay = game_log(soup)
        >>>
        >>> for entry in playbyplay:
        >>>     play_items = play_items_from_log_entry(entry)
        >>>     if play_items:
        >>>         team = possession(play_items)
        """
    return play_items[1].img["src"].rsplit('/', 1)[-1].split('.png')[0]


def score(play_items: bs4.element.ResultSet) -> Tuple[int, int]:
    """ Returns the score for a given log entry

        Examples
        --------
        >>> from bs4 import BeautifulSoup
        >>> response = urlopen('http://espn.go.com/nba/playbyplay?gameId=400827900') # Spurs vs Thunder
        >>> soup = BeautifulSoup(response.read(), 'html.parser')
        >>> playbyplay = game_log(soup)
        >>>
        >>> for entry in playbyplay:
        >>>     play_items = play_items_from_log_entry(entry)
        >>>     if play_items:
        >>>         entry_score = score(play_items)
        """
    return tuple(int(s) for s in play_items[3].text.split() if s.isdigit())
