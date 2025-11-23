# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **modified fork** of `RegsonDR/spotify-save-playlists-cron` that has been customized to automatically capture Spotify's **Daylist** playlist snapshots throughout the day. The original project saves auto-generated playlists like "Discover Weekly" on a weekly schedule. This fork extends it to capture Daylist updates 4 times daily (morning/afternoon/evening/night) and organize them into time-period-specific archive playlists.

## The Daylist Problem

### CRITICAL ISSUE: Daylist is NOT Accessible via Standard Spotify Web API

**THE USER DOES HAVE DAYLIST IN THEIR LIBRARY. IT IS EVEN PINNED. THE ISSUE IS NOT ABOUT ADDING IT TO THE LIBRARY.**

The fundamental problem is that Spotify's Daylist feature, despite being visible in the user's Spotify app and library, **cannot be accessed through the standard Spotify Web API endpoints**. This has been extensively tested:

- ✗ Direct playlist ID access returns 404 (tried multiple IDs)
- ✗ Searching user's playlists via `/me/playlists` doesn't return Daylist
- ✗ Searching globally via `/search?type=playlist` doesn't find it
- ✗ Featured playlists endpoint returns 404 (API restricted as of Nov 2024)
- ✗ Even hardcoded "universal" Daylist IDs from other projects return 404

**Key findings:**
1. Daylist IDs change frequently and are user-specific
2. Even when pinned/saved, Daylist doesn't appear in API responses
3. Other Daylist archiving projects (like `jaasonw/daylist-rewind`) likely have special API access or use undocumented endpoints
4. The Spotify Web API changes in November 2024 may have further restricted access

### Current Workaround

The code uses **pattern matching** to find playlists that match the Daylist naming convention:
- Must contain a day name (monday-sunday)
- Must contain a time period (morning/afternoon/evening/night)
- Must have exactly 50 tracks (Daylist signature)
- Cannot contain "daylist archive" in the name

This finds old saved Daylists in the user's library, but **not the live, updating Daylist**.

## Architecture Changes from Original

### Modified Files

1. **`misc.py`**
   - Added `get_time_period()` function that returns current time period based on hour
   - Time mappings: 6-11=morning, 12-16=afternoon, 17-20=evening, 21-5=night

2. **`main.py`**
   - Added `find_daylist_id()` - attempts to dynamically locate Daylist by name pattern
   - Added `replace_playlist_tracks()` - PUT endpoint for snapshot mode (vs append)
   - Modified `copy_playlist()` - supports both append and replace modes, auto-detects "daylist" source
   - Modified `process_multiple_playlists()` - added time-period based scheduling alongside legacy day-based
   - Updated `main()` - displays current time period in logs

3. **`.github/workflows/save.yaml`**
   - Changed schedule from `30 6 * * *` (daily at 6:30am) to `0 7,13,18,23 * * *` (4x daily)
   - Renamed workflow to "Save Daylist Snapshots"

### New Playlist Configuration Format

The `PLAYLISTS_CONFIG` now supports:
```json
{
  "time_period": "morning|afternoon|evening|night",
  "source": "daylist",  // Special keyword triggers dynamic discovery
  "target": "playlist_id",
  "replace_mode": true  // Use PUT instead of POST (snapshot vs append)
}
```

Legacy format (day-based) still supported for backward compatibility.

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set up .env file with credentials
# See README.md step 3 for obtaining Spotify API credentials

# Run OAuth setup to get refresh token
python3 setup/authorization.py

# Test the script
python3 main.py
```

## GitHub Actions Deployment

The script is designed to run via GitHub Actions on a schedule. Required secrets:
- `CLIENT_ID` - Spotify app client ID
- `CLIENT_SECRET` - Spotify app client secret
- `REFRESH_TOKEN` - OAuth refresh token from setup
- `PLAYLISTS_CONFIG` - JSON array of playlist configurations

## Key Limitations

1. **Cannot access live Daylist** - This is the core unsolved problem
2. **Pattern matching is imperfect** - May match old saved Daylists instead of current
3. **No deduplication across runs** - Replace mode overwrites entire playlist each time
4. **Timezone assumptions** - Time period detection uses server time (UTC in GitHub Actions)

## Next Steps / TODOs

To make this fully automatic, we need to solve the Daylist access problem. Potential approaches:
1. Research if Spotify has a special API access program for Daylist
2. Investigate mobile app API endpoints (may use different authentication)
3. Consider web scraping Spotify web player (fragile, against TOS)
4. Use IFTTT/Zapier as intermediary (has limits, costs)
5. Contact Spotify developer support for guidance
