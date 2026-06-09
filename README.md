# 🎵 Music Time Machine

A Python CLI tool that generates a Spotify playlist of the top 50 songs from any week since October 1976. Enter a date, and the app scrapes the charts, finds each track on Spotify, and creates a ready-to-play playlist in your account — automatically.

---

## How It Works

1. **You enter a date** (e.g. `1994-11-05`)
2. The app scrapes [musicchartsarchive.com](https://www.musicchartsarchive.com) for the top 50 singles chart of that week
3. Each song is searched on the Spotify API by artist and title
4. A new playlist is created in your Spotify account and all found tracks are added
5. The playlist ID is saved to a local catalog (`playlists_catalog.json`) for future reference

---

## Features

- **Manual OAuth 2.0 Authorization Code Flow** — implemented from scratch without third-party Spotify wrappers ([see flow diagram](https://alecmtz.github.io/spotify-time-machine/spotify-oauth-flow.html))
- **Automatic token refresh** — persists access and refresh tokens to disk; refreshes silently when expired
- **Retry logic** — handles transient API errors (429, 502, 503, 504) with configurable retries and sleep delay
- **Date normalization** — adjusts any input date to the nearest Saturday (how weekly charts are indexed)
- **Input validation** — rejects future dates and dates before the chart archive's earliest records (October 1976)
- **Local playlist catalog** — saves playlist name → Spotify ID mappings to `playlists_catalog.json`

---

## Setup

### Prerequisites

- Python 3.12+
- A [Spotify Developer](https://developer.spotify.com/dashboard) account with an app created

### 1. Clone the repo

```bash
git clone https://github.com/your-username/music-time-machine.git
cd spotify-time-machine
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your Spotify credentials

Create a `.env` file in the project root:

```
SPOTIFY_CLIENT=your_client_id_here
SPOTIFY_SECRET=your_client_secret_here
```

In your Spotify Developer Dashboard, add the following **Redirect URI** to your app settings:

```
http://127.0.0.1:8888/callback
```

### 5. Run it

```bash
python main.py
```

On first run, a browser window will open asking you to log in to Spotify and grant permission. After that, your token is saved locally and reused automatically.

---

## Usage

```
Which year do you want to travel to? Type the date in this format YYYY-MM-DD: 1985-07-13
```

- Dates must be in `YYYY-MM-DD` format
- Earliest supported date: **October 1976**
- Future dates are rejected
- Type `X` at the prompt to exit

---

## Notes

- Dates must be in `YYYY-MM-DD` format, between October 1976 and today. Type `X` to exit.
- Songs not available on Spotify are skipped with a log message.
---

## Example Output

```
Access Token Loaded
1.  ('Every Breath You Take', 'The Police')
2.  ('Billie Jean', 'Michael Jackson')
...
Get song URI from spotify: 1/50
Get song URI from spotify: 2/50
...
Total songs URI: 47
Playlist added to the catalog!
Songs added!
```
