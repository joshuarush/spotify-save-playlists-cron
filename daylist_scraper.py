"""
Extract Daylist information from Spotify's embed endpoint.
Since the Spotify Web API doesn't expose Daylist, we scrape the embed HTML.
"""

import requests
import re
import html as html_module

# Known Daylist ID pattern - this seems to be user-specific but stable
# Users can update this in their .env as DAYLIST_EMBED_ID
DEFAULT_DAYLIST_ID = "37i9dQZF1FbHVBqS3pFJrQ"

def get_daylist_data(daylist_embed_id=None):
    """
    Extract Daylist data from Spotify's embed endpoint.

    The embed endpoint (https://open.spotify.com/embed/playlist/ID) returns HTML
    that contains JSON data with the playlist name, description, and track URIs.

    Args:
        daylist_embed_id: The Daylist playlist ID (user-specific)

    Returns:
        dict with 'name', 'description', 'track_uris', and 'playlist_id' or None if failed
    """
    if not daylist_embed_id:
        daylist_embed_id = DEFAULT_DAYLIST_ID

    try:
        print(f"Fetching Daylist from embed endpoint: {daylist_embed_id}")
        embed_url = f'https://open.spotify.com/embed/playlist/{daylist_embed_id}'

        response = requests.get(embed_url, timeout=10)

        if response.status_code != 200:
            print(f"ERROR: Embed endpoint returned {response.status_code}")
            return None

        html_content = response.text

        # Extract playlist name
        name_match = re.search(r'\"name\":\"([^\"]+)\"', html_content)
        if not name_match:
            print("ERROR: Could not find playlist name in embed HTML")
            return None

        playlist_name = html_module.unescape(name_match.group(1))
        print(f"Found Daylist: {playlist_name}")

        # Extract description
        desc_match = re.search(r'\"description\":\"([^\"]+)\"', html_content)
        description = html_module.unescape(desc_match.group(1)) if desc_match else ""

        # Extract all track URIs
        track_uri_pattern = r'spotify:track:([a-zA-Z0-9]{22})'
        track_ids = re.findall(track_uri_pattern, html_content)

        # Remove duplicates while preserving order
        unique_track_ids = list(dict.fromkeys(track_ids))
        track_uris = [f"spotify:track:{tid}" for tid in unique_track_ids]

        print(f"Extracted {len(track_uris)} tracks")

        if len(track_uris) == 0:
            print("ERROR: No tracks found in embed HTML")
            return None

        return {
            'name': playlist_name,
            'description': description,
            'track_uris': track_uris,
            'playlist_id': daylist_embed_id
        }

    except requests.RequestException as e:
        print(f"ERROR: Network error fetching embed: {e}")
        return None
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Test the scraper
    from dotenv import load_dotenv
    import os

    load_dotenv()

    daylist_id = os.getenv('DAYLIST_EMBED_ID', DEFAULT_DAYLIST_ID)

    print("Testing Daylist scraper...")
    print(f"Daylist ID: {daylist_id}\n")

    data = get_daylist_data(daylist_id)

    if data:
        print("\n=== DAYLIST DATA ===")
        print(f"Name: {data['name']}")
        print(f"Description: {data['description']}")
        print(f"Tracks: {len(data['track_uris'])}")
        print(f"First 5 tracks: {data['track_uris'][:5]}")
    else:
        print("\nFailed to extract Daylist data")
