import requests, base64, json
from misc import *
from dotenv import load_dotenv, find_dotenv
from daylist_scraper import get_daylist_data

load_dotenv(find_dotenv())

REFRESH_TOKEN = get_env("REFRESH_TOKEN")
CLIENT_ID = get_env("CLIENT_ID")
CLIENT_SECRET = get_env("CLIENT_SECRET")
PLAYLISTS_CONFIG = get_env("PLAYLISTS_CONFIG")
DAYLIST_EMBED_ID = get_env("DAYLIST_EMBED_ID")  # User's Daylist embed ID

OAUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"

DEBUG_WEEKDAYS = False # skips weekday recognition for easier testing

def refresh_access_token():
    payload = {
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
    }
    encoded_client = base64.b64encode((CLIENT_ID + ":" + CLIENT_SECRET).encode('ascii'))
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic %s" % encoded_client.decode('ascii')
    }
    response = requests.post(OAUTH_TOKEN_URL, data=payload, headers=headers)
    return response.json()

def find_daylist_id(access_token):
    """
    Dynamically find the Daylist playlist ID from user's library.
    Daylist IDs change frequently, so we search for it by name pattern.

    Daylist names follow the pattern: [descriptors] [day] [time_period]
    Example: "soft country coastal cowgirl saturday evening"
    """
    headers = {
        "Authorization": "Bearer %s" % access_token
    }

    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    time_periods = ['morning', 'afternoon', 'evening', 'night', 'late night']

    # Search through user's playlists
    offset = 0
    candidates = []

    while offset < 200:  # Limit search to first 200 playlists
        url = "https://api.spotify.com/v1/me/playlists?limit=50&offset=%d" % offset
        response = requests.get(url, headers=headers)
        data = response.json()

        if not data.get('items'):
            break

        for playlist in data['items']:
            name = playlist.get('name', '').lower()
            owner_id = playlist.get('owner', {}).get('id', '')
            tracks_count = playlist.get('tracks', {}).get('total', 0)

            # Daylist criteria:
            # 1. Has a day name and time period in the title
            # 2. Has exactly 50 tracks (Daylist signature)
            # 3. Could be owned by spotify OR by user (when followed)

            has_day = any(day in name for day in days)
            has_time = any(period in name for period in time_periods)

            if has_day and has_time and tracks_count == 50:
                # Exclude our own archive playlists
                if 'daylist archive' not in name:
                    candidates.append({
                        'name': playlist.get('name'),
                        'id': playlist.get('id'),
                        'owner': owner_id
                    })

        offset += 50

    # If we found candidates, return the first one (most likely to be current)
    if candidates:
        daylist = candidates[0]
        print("Found potential Daylist:", daylist['name'], "| ID:", daylist['id'], "| Owner:", daylist['owner'])
        return daylist['id']

    return None

def get_playlist(access_token, playlist_id):
    url = "https://api.spotify.com/v1/playlists/%s" % playlist_id
    headers = {
       "Content-Type": "application/json",
       "Authorization": "Bearer %s" % access_token
    }
    response = requests.get(url, headers=headers)
    return response.json()

def add_to_playlist(access_token, tracklist, playlist_id):
    url = "https://api.spotify.com/v1/playlists/%s/tracks" % playlist_id
    payload = {
        "uris" : tracklist
    }
    headers = {
       "Content-Type": "application/json",
       "Authorization": "Bearer %s" % access_token
    }
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response.json()

def replace_playlist_tracks(access_token, tracklist, playlist_id):
    """Replace all tracks in a playlist (used for snapshots like Daylist)"""
    url = "https://api.spotify.com/v1/playlists/%s/tracks" % playlist_id
    payload = {
        "uris" : tracklist
    }
    headers = {
       "Content-Type": "application/json",
       "Authorization": "Bearer %s" % access_token
    }
    response = requests.put(url, data=json.dumps(payload), headers=headers)
    return response.json()

def create_playlist(access_token, name, description="", public=False):
    """Create a new playlist in the user's library"""
    # Get current user ID
    user_url = "https://api.spotify.com/v1/me"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % access_token
    }
    user_response = requests.get(user_url, headers=headers)
    user_id = user_response.json()['id']

    # Create playlist
    url = "https://api.spotify.com/v1/users/%s/playlists" % user_id
    payload = {
        "name": name,
        "description": description,
        "public": public
    }
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response.json()

def capture_daylist_snapshot():
    """
    Capture the current Daylist by:
    1. Scraping embed endpoint for name and tracks
    2. Creating a new playlist with that name
    3. Adding all tracks to the new playlist
    Returns True if successful, False otherwise
    """
    access_token = refresh_access_token()['access_token']

    # Get Daylist data from embed scraper
    print("Fetching Daylist data...")
    daylist_data = get_daylist_data(DAYLIST_EMBED_ID)

    if not daylist_data:
        print("ERROR: Could not fetch Daylist data")
        return False

    playlist_name = daylist_data['name']
    track_uris = daylist_data['track_uris']

    print(f"Creating new playlist: '{playlist_name}' with {len(track_uris)} tracks")

    # Create new playlist with Daylist's name
    description = f"Daylist snapshot captured on {get_timestamp()}"
    new_playlist = create_playlist(access_token, playlist_name, description, public=False)

    if 'id' not in new_playlist:
        print(f"ERROR creating playlist: {new_playlist}")
        return False

    new_playlist_id = new_playlist['id']
    print(f"Created playlist ID: {new_playlist_id}")

    # Add tracks to new playlist
    response = add_to_playlist(access_token, track_uris, new_playlist_id)

    if "snapshot_id" in response:
        print(f"✅ Successfully captured Daylist snapshot: '{playlist_name}'")
        return True
    else:
        print(f"ERROR adding tracks: {response}")
        return False

def copy_playlist(source, target, replace_mode=False):
    access_token = refresh_access_token()['access_token']

    # If source is "daylist", dynamically find the current Daylist ID
    if source.lower() == "daylist":
        daylist_id = find_daylist_id(access_token)
        if not daylist_id:
            raise ValueError('Daylist not found in your library. Make sure you have added Daylist to your Spotify library.')
        source = daylist_id

    playlist = get_playlist(access_token, source)

    try:
        tracks = playlist['tracks']
    except Exception as e:
        raise ValueError('No tracks found, check the source')

    tracklist = []
    for item in tracks['items']:
        if item['track']:  # Skip None tracks
            tracklist.append(item['track']['uri'])

    if replace_mode:
        response = replace_playlist_tracks(access_token, tracklist, target)
        action = "replaced"
    else:
        response = add_to_playlist(access_token, tracklist, target)
        action = "added"

    if "snapshot_id" in response:
        print("Successfully", action, len(tracklist),"songs from", playlist['name'])
        return True
    else:
        print(response)
        return False

def process_multiple_playlists(config):
    current_week_day = get_weekday()
    current_time_period = get_time_period()
    handled_playlist_count = 0

    try:
        multi_playlist_info = json.loads(config)
    except Exception as e:
        print("Malformed JSON:", e)
        return handled_playlist_count

    for playlist_info in multi_playlist_info:
        should_handle = False
        try:
            required_week_day = playlist_info.get('day')
            time_period = playlist_info.get('time_period')
            source = playlist_info.get('source')
            target = playlist_info.get('target')
            replace_mode = playlist_info.get('replace_mode', False)

            if not source or not target:
                raise ValueError('Source or Target not defined')

            # Time period-based scheduling (for Daylist)
            if time_period:
                if time_period == current_time_period:
                    should_handle = True
                    print("Time period match:", time_period, "== current:", current_time_period)
            # Legacy: If debugging or there isn't a day set
            elif DEBUG_WEEKDAYS or required_week_day == None:
                should_handle = True
            # Legacy: If there is a day set
            elif isinstance(required_week_day, int) and required_week_day == current_week_day:
                should_handle = True

            if should_handle:
                # Check if this is a Daylist capture (source="daylist")
                if source.lower() == "daylist":
                    print("Capturing Daylist snapshot...")
                    if capture_daylist_snapshot():
                        handled_playlist_count += 1
                else:
                    # Legacy: Standard playlist copy
                    if copy_playlist(source, target, replace_mode):
                        handled_playlist_count += 1

        except Exception as e:
            print("Error:", e, "in", playlist_info)

    return handled_playlist_count

def main():
    print("Day index is", get_weekday(), "| Time period:", get_time_period(), "| Timestamp:", get_timestamp())
    if REFRESH_TOKEN == None or CLIENT_ID == None or CLIENT_SECRET == None:
        print("Auth token variables have not been loaded!")
        return

    if DEBUG_WEEKDAYS == True:
        print("Debug mode enabled")

    handled_playlist_count = process_multiple_playlists(PLAYLISTS_CONFIG)
    if handled_playlist_count == 0:
        print("No playlists handled. Check your playlist config and time period.")
    else:
        print("Handled", handled_playlist_count, "playlist(s)")

main()