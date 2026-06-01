import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta


def time_machine(date: str) -> list[tuple[str, str]]:
    """
        Fetches the top 50 singles chart for a given date from musicchartsarchive.com.

        If the date is not a Saturday, it is adjusted to the nearest Saturday of
        that week before making the request.

        Args:
            date: A date string in YYYY-MM-DD format.

        Returns:
            A list of 50 (song, artist) tuples in chart order.

        Raises:
            requests.HTTPError: If the request returns an unsuccessful status code.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/146.0.0.0 Safari/537.36"
    }

    # Checks if it's a Saturday
    date = is_saturday(date)

    res = requests.get(url=f"https://www.musicchartsarchive.com/singles-chart/{date}", headers=headers)
    res.raise_for_status()
    web_data = res.text
    clean_web_data = _clean_html_data(web_data=web_data)
    return clean_web_data


def _clean_html_data(web_data: str) -> list[tuple[str, str]]:
    """
    Parses raw HTML chart data and extracts the top 50 songs and artists.

    Cleans artist names by removing featuring credits ('ft.' and 'feat.').

    Args:
        web_data: Raw HTML string returned from time_machine().

    Returns:
        A list of 50 (song, artist) tuples in chart order.
    """
    soup = BeautifulSoup(web_data, "html.parser")

    songs = soup.select("table td:nth-child(2)")  # Get literally the second kid
    artists = soup.select("table td:nth-child(3)")  # Get the 3rd kid

    # Get songs and clean the list
    songs = [
        s.getText().strip() for s in songs
    ]

    # Get artists and clean the list
    artists = [
        a.getText().strip().replace("ft.", "").replace("feat.", "") for a in artists
    ]

    return [(songs[i], artists[i]) for i in range(50)]


def is_saturday(date: str) -> str:
    """
        Adjusts a date to the nearest Saturday of the same week if it is not already a Saturday.

        Args:
            date: A date string in YYYY-MM-DD format.

        Returns:
            A date string in YYYY-MM-DD format representing the Saturday of that week.
    """
    # Convert to datetime obj
    date = datetime.strptime(date, "%Y-%m-%d")

    # Get the week day
    day_of_week = datetime.weekday(date)

    # Get the saturday of that week
    if day_of_week != 5:
        if day_of_week > 5:
            date -= timedelta(days=1)
        else:
            day_difference = abs(day_of_week - 5)
            date += timedelta(days=day_difference)
    return str(date.date())

