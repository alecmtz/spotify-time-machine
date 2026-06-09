import json
import time
import requests
import os
import base64
import webbrowser
from datetime import datetime, timedelta
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode

load_dotenv()


class Spotify:
    """
        Client for the Spotify Web API.

        Handles OAuth 2.0 Authorization Code flow, token storage and refresh,
        and provides methods for creating playlists, searching songs, and adding
        tracks to playlists. All API requests include retry logic for transient errors.
    """

    client = os.getenv("SPOTIFY_CLIENT")
    secret = os.getenv("SPOTIFY_SECRET")

    # Auth urls
    token_url = "https://accounts.spotify.com/api/token"
    authorize_url = "https://accounts.spotify.com/authorize?"
    redirect_url = "http://127.0.0.1:8888/callback"

    # Spotify endpoints
    create_playlist_url = "https://api.spotify.com/v1/me/playlists"
    search_song_url = "https://api.spotify.com/v1/search?"

    TOKEN_PATH = os.path.join(os.path.dirname(__file__), "token.json")
    SLEEP = 5
    TIMEOUT = 10

    def __init__(self):
        """Initializes the Spotify client by loading or retrieving a valid access token."""
        self.access_token = self.get_access_token()

    def get_access_token(self) -> str:
        """
            Loads or retrieves a valid Spotify access token.

            Attempts to load a saved token first. If none exists, prompts the user
            to log in via the browser to complete the OAuth 2.0 Authorization Code flow,
            then exchanges the authorization code for an access token and saves it.

            Returns:
                A valid Spotify access token string.
        """
        # Load token
        token = self._load_access_token()

        # If it exists return it
        if token:
            print("Access Token Loaded")
            return token

        # Otherwise prompt the user to log in, so we can get the auth code
        print("Prompting user to log in")
        auth_code = self._login()
        print("Log in successful. Authorization code retrieved.")

        # Exchange auth code for an access token
        json_response = self._exchange_auth_code(auth_code)
        print("Access token retrieved")

        # Save json response into a file
        self._save_tokens(json_response)
        return json_response.get("access_token")

    def create_playlist(self, name: str) -> dict:
        """
           Creates a new public playlist for the authenticated Spotify user.

           Args:
               name: The name of the playlist to create.

           Returns:
               A dict containing the Spotify API response with playlist details,
               including the playlist ID and URI.
        """
        body = {
            "name": name,
        }

        res = self._request_with_retry(
            method="POST",
            url=Spotify.create_playlist_url,
            json=body
        )
        return res.json()

    def search_song(self, artist: str, song: str) -> dict | None:
        """
            Searches for a track on Spotify by artist and song name.

            Args:
                artist: The name of the artist.
                song: The name of the track.

            Returns:
                A dict containing the Spotify API response with track results,
                or None if no matching track was found.
        """
        params = {
            "q": f"artist:{artist} track:{song}",
            "type": "track",
        }

        res = self._request_with_retry(
            method="GET",
            url=Spotify.search_song_url,
            params=params
        )

        data = res.json()
        items = data.get("tracks").get("items")

        # Check if song was not found
        if len(items) == 0:
            print(f"Song not found for: {artist} - {song}. Skipping ...")
            return None

        return data

    def add_song_to_playlist(self, playlist_id: str, spotify_uri: str | list):
        """
            Adds one or more tracks to a Spotify playlist.

            Args:
                playlist_id: The Spotify playlist ID to add tracks to.
                spotify_uri: A single Spotify track URI string or a list of URIs.
        """
        add_items_endpoint = f"https://api.spotify.com/v1/playlists/{playlist_id}/items"

        # If it's a single song convert it into list
        if isinstance(spotify_uri, str):
            spotify_uri = [spotify_uri]

        body = {
            "uris": spotify_uri
        }

        res = self._request_with_retry(method="POST", url=add_items_endpoint, json=body)
        print("Songs added!")

    def _request_with_retry(self, method: str, url: str, retries: int = 3, **kwargs):
        """
            Makes an HTTP request with retry logic for transient errors.

            Retries up to `retries` times on 429, 502, 503, 504 responses,
            waiting SLEEP seconds between attempts.

            Args:
                method: HTTP method, either "GET" or "POST".
                url: The endpoint URL.
                retries: Maximum number of retry attempts. Defaults to 3.
                **kwargs: Additional arguments passed to requests (headers, params, json, etc).

            Returns:
                The requests.Response object if successful.

            Raises:
                requests.RequestException: If the request fails and retries are exhausted.
        """
        # Temporary errors
        TRANSIENT_ERRORS = {429, 502, 503, 504}

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        try:
            res = requests.request(method, url, timeout=Spotify.TIMEOUT, headers=headers, **kwargs)
            res.raise_for_status()
            return res
        except requests.RequestException as error:
            # None is a safeguard because error.response can be None in some cases
            # such as connection timeout, DNS failure, connection refused, etc
            if error.response is not None and error.response.status_code in TRANSIENT_ERRORS:
                if retries == 0:
                    print(f"Max retries reached for {method} {url}")
                    raise  # re-raise the 429/502/503/504

                print(f"Transient error {error.response.status_code}. Retrying... ({retries} left")
                time.sleep(Spotify.SLEEP)
                return self._request_with_retry(method, url, retries - 1, **kwargs)

            print(f"Whoops! Error {error.response.status_code}.'{error.response.json()}'")
            raise  # immediately re-raise 400/401/404

    @staticmethod
    def _login() -> str:
        """
            Opens the Spotify authorization page in the browser and captures the
            authorization code returned via the OAuth 2.0 redirect callback.

            Starts a temporary local HTTP server on port 8888 to intercept the
            redirect from Spotify after the user logs in and grants permission.

            Returns:
                The authorization code string from the Spotify redirect URL.
        """
        params = {
            "client_id": Spotify.client,
            "response_type": "code",
            "redirect_uri": Spotify.redirect_url,
            "scope": "playlist-modify-public"
        }

        # Encode query parameters safely into a URL string
        url = Spotify.authorize_url + urlencode(params)

        # Open url in the browser
        webbrowser.open(url)

        # Wait for Spotify to redirect back with the code
        # Create variable, so we can get the code from the url
        code = ""

        class CallbackHandler(BaseHTTPRequestHandler):

            # Override do_GET method
            def do_GET(self):

                # Tell Python to find the variable code in the nearest enclosing function scope
                nonlocal code

                # Break url into components, get the query and convert it to a dictionary (parse_qs)
                query = parse_qs(urlparse(self.path).query)
                code = query.get("code", [None])[0]

                # Build the HTTP response to send back to the browser
                self.send_response(200)

                # Write a blank line to signal that headers are done and body is coming
                self.end_headers()

                # Stream connected directly to the browser - this is what the browser displays
                # b"" prefix makes it a bytes object instead of a string because HTTP sends raw bytes over the network
                self.wfile.write(b"Got it! You can close this tab.")

        # Create the server and listen to this machine, pass the handler class, so it knows what to do with requests
        server = HTTPServer(("127.0.0.1", 8888), CallbackHandler)

        # Catch one redirect no need for serve_forever()
        # When spotify's redirect hits port 8888, wake up and handle it using CallbackHandler
        server.handle_request()
        return code

    @staticmethod
    def _exchange_auth_code(code: str) -> dict:
        """
           Exchanges an OAuth 2.0 authorization code for an access token.

           Args:
               code: The authorization code received from Spotify's redirect callback.

           Returns:
               A dict containing the token response from Spotify, including
               access_token, refresh_token, and an added expiry_time timestamp.
        """
        # Get spotify access
        credentials = f"{Spotify.client}:{Spotify.secret}"

        # Encode credentials to base64 (decode back to str since the transformation is in bytes)
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded}"
        }

        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": Spotify.redirect_url
        }

        res = requests.post(url=Spotify.token_url, data=payload, headers=headers)
        res.raise_for_status()
        data = res.json()
        data = Spotify._add_token_expiry_timestamp(data)
        return data

    @staticmethod
    def _add_token_expiry_timestamp(data: dict):
        """
            Adds an expiry_time key to the token data dict, set to one hour from now.

            Args:
                data: The token response dict from Spotify.

            Returns:
                The same dict with an added expiry_time string timestamp.
        """
        current_time = datetime.now()
        data["expiry_time"] = str(current_time + timedelta(hours=1))  # Convert to string for json
        return data

    @staticmethod
    def _load_access_token() -> str | None:
        """
        Loads a saved access token from disk, refreshing it if expired.

        Returns:
            A valid access token string, or None if no token file exists.
        """
        # Check if token file exists
        if not os.path.exists(Spotify.TOKEN_PATH):
            return None

        # If it exists open the file and return the access token
        with open(Spotify.TOKEN_PATH, "r") as f:
            data = json.load(f)

        # Get the access token
        access_token = data.get("access_token")

        # Check if token has expired
        refresh_access_token = Spotify._refresh_token(data)
        if refresh_access_token:
            print("TOKEN REFRESHED")
            access_token = refresh_access_token

        return access_token

    @staticmethod
    def _refresh_token(data: dict) -> dict | None:
        """
            Refreshes the Spotify access token if it has expired.

            Args:
                data: The saved token dict containing expiry_time and refresh_token.

            Returns:
                A new access token string if the token was refreshed, or None if
                the current token is still valid.
        """
        current_time = datetime.now()

        # Convert str timestamp to datetime object
        expiry_time = datetime.strptime(data.get("expiry_time"), "%Y-%m-%d %H:%M:%S.%f")

        # Check if token is still available
        if current_time < expiry_time:
            return None

        print("------------ REFRESHING TOKEN ------------")
        # Refresh token
        refresh_token = data.get("refresh_token")

        # Get spotify access
        credentials = f"{Spotify.client}:{Spotify.secret}"

        # Encode credentials to base64 (decode back to str since the transformation is in bytes)
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded}"
        }

        body = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }

        res = requests.post(url=Spotify.token_url, headers=headers, data=body)
        res.raise_for_status()
        response_data = res.json()

        # Add timestamp to new token
        response_data = Spotify._add_token_expiry_timestamp(response_data)

        # Add refresh token
        response_data["refresh_token"] = refresh_token

        # Save new access_token into file
        Spotify._save_tokens(json_response=response_data)

        return response_data.get("access_token")

    @staticmethod
    def _save_tokens(json_response: dict):
        """
            Saves the token response dict to disk as a JSON file.

            Args:
                json_response: The token response dict to persist.
        """
        try:
            with open(Spotify.TOKEN_PATH, "w") as f:
                json.dump(obj=json_response, fp=f, indent=2)
        except FileNotFoundError:
            print("File not found. Creating a new token file.")
            with open(Spotify.TOKEN_PATH, "x") as f:
                json.dump(obj=json_response, fp=f, indent=2)


