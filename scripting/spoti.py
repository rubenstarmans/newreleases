from requests.exceptions import ConnectionError
from json.decoder import JSONDecodeError
from datetime import datetime, timedelta
from spotipy import Spotify
import spotipy.util
import configparser
from scripting import tweeti
import urllib.request

# Specify path to project folder here
path = "/dummy/path/"


# Function to get the date precision format.
def get_date_precision_format(depth):
    if depth == "day":
        return "%Y-%m-%d"
    elif depth == 'month':
        return "%Y-%m"
    elif depth == 'year':
        return "%Y"
    else:
        return "%Y-%m-%d"


# Mark time script is run and last run.
t0 = datetime.strptime(str(datetime.now().year) + "-" + str(datetime.now().month) + "-" + str(datetime.now().day), "%Y-%m-%d")
f = open(path + "newreleases/resources/last_run.txt", 'r')
t_minus_1 = datetime.strptime(f.read().split(" ")[0], "%Y-%m-%d")
f.close()

# Open configuration.
config = configparser.ConfigParser()
config.read(path + "newreleases/resources/config.cfg")

# Build the token. Replace user_id with your user-id
user_id = 'user-id'
token = spotipy.util.prompt_for_user_token(
    user_id,
    scope='user-follow-read playlist-modify-private playlist-modify-public',
    client_id=config.get("SPOTIFY", "SPOTIFY_CLIENT_ID"),
    client_secret=config.get("SPOTIFY", "SPOTIFY_CLIENT_SECRET"),
    redirect_uri=config.get("SPOTIFY", "SPOTIFY_REDIRECT_URI")
)

# Connect to Spotify
spotify = Spotify(auth=token)


# Get tracks from playlist.
playlist_tracks = []
more_tracks = True
last_track = 0
playlistid = 
while more_tracks:
    new_playlist_tracks = spotify.user_playlist_tracks(user=user_id, playlist_id=playlistid, limit=100, offset=last_track)
    playlist_tracks.extend(new_playlist_tracks['items'])
    last_track = last_track + len(playlist_tracks)
    if last_track % 100 > 0:
        more_tracks = False
playlist_track_ids = [x['track']['id'] for x in playlist_tracks]

# Remove tracks from playlist that are older than a month.
tracks_to_remove = []
tracks_removed = False
for track in playlist_tracks:
    release_date = datetime.strptime(track['track']['album']['release_date'], get_date_precision_format(track['track']['album']['release_date_precision']))
    if release_date <= (t0-timedelta(days=30)):
        tracks_removed = True
        tracks_to_remove.append(track['track']['id'])
spotify.user_playlist_remove_all_occurrences_of_tracks(user='ruben-17', playlist_id='5T1V0go9JERZJKcPiv3aJO', tracks=tracks_to_remove)

# Get followed artists
followed_artists = []
last_artist_id = None
artist_result = spotify.current_user_followed_artists(50, last_artist_id)
artists = artist_result['artists']['items']
while artists:
    artist_result = spotify.current_user_followed_artists(50, last_artist_id)
    artists = artist_result['artists']['items']

    for artist in artists:
        last_artist_id = artist['id']
        followed_artists.append(artist)

# Get 5 newest albums and singles from artists.
releases = []
for artist in followed_artists:
    try:
        # Albums
        result_albums = spotify.artist_albums(
            artist_id=artist['id'],
            album_type='Album',
            country='NL',
            limit=5
        )
        releases.extend(result_albums['items'])
        # Singles
        result_singles = spotify.artist_albums(
            artist_id=artist['id'],
            album_type='Single',
            country='NL',
            limit=5
        )
        releases.extend(result_singles['items'])
    except ConnectionError:
        print(("Could not establish connection while "
               "fetching releases for artist {0} with id {1}. "
               "Skipping.").format(artist['name'], artist['id']))
    except JSONDecodeError:
        print(("Could not decode JSON response "
               "of artist {0} with id {}. Skipping.").format(artist['name'], artist['id']))

# Filter releases to be newer than x. Where x currently is today.
filtered_releases = []
for release in releases:
    release_date = datetime.strptime(release['release_date'].split(' ')[0], get_date_precision_format(release['release_date_precision']))
    if release_date >= (t0-timedelta(days=1)):
        filtered_releases.append(release)

# Extract track ids from releases and add them if they are not already in the playlist. This can happen when multiple
# followed artists work on the same track.
# If a track is selected to be added to the playlist, also save the artists.
track_ids = []
artists = dict()
followed_artists_names = [x['name'] for x in followed_artists]
for release in filtered_releases:
    tracks = spotify.album_tracks(release['id'])
    for x in tracks['items']:
        if x['id'] not in track_ids and x['id'] not in playlist_track_ids:
            track_ids.append(x['id'])

            for artist in x['artists']:
                if artist['name'] in followed_artists_names:
                    if artist['name'] not in artists:
                        artists[artist['name']] = 1
                    else:
                        artists[artist['name']] += 1

# Add tracks to playlist.
n = 100
added = False
for i in range(0, len(track_ids), n):
    spotify.user_playlist_add_tracks(user=user_id, playlist_id=playlistid, tracks=track_ids[i:i + n])
    added = True

if added:
    print("Tracks added!")


# Save when the script was run for next run.
f = open(path + "newreleases/resources/last_run.txt", 'w')
f.write(str(t0).split(' ')[0])
f.close()

# Tweet about new tracks from the artists.
pop_artists = [(k, artists[k]) for k in sorted(artists, key=artists.get, reverse=True)]

artists_str = ""
for i in range(0, min(3, len(pop_artists))):
    current_artist = pop_artists[i][0]
    if i == 0:
        artists_str += current_artist
    if i == 1 and len(pop_artists) == 2:
        artists_str = artists_str + " and " + current_artist
    elif i == 1:
        artists_str = artists_str + ", " + current_artist
    if i == 2:
        artists_str = artists_str + " and " + current_artist

twitter_api = tweeti.get_auth(path)

if len(track_ids) > 0:
    playlist_url = ""ENTER_PLAYLIST_URL_HERE
    message = "Playlist updated with new tracks from " + artists_str
    if len(pop_artists) > 3:
        message = message.replace(" and", ",")
        message += " and more. " + playlist_url
    else:
        message += ". " + playlist_url
    if len(track_ids) == 1:
        message = message.replace("new tracks", "a new track")
    tweeti.tweet(message, twitter_api)
    print("Tweeted!")

# If tracks were removed, the twitter bot's profile image needs to be updated. First get the image and save it. Then upload it to twitter.
if tracks_removed:
    playlist_image = spotify.user_playlist(user=user_id, playlist_id=playlistid, fields='images')

    biggest_size = 0
    url = ''
    for image in playlist_image['images']:
        if image['height'] > biggest_size:
            biggest_size = image['height']
            url = image['url']
    urllib.request.urlretrieve(url, path + 'newreleases/resources/profile_image.jpeg')

    tweeti.update_profile_image(path + 'newreleases/resources/profile_image.jpeg', twitter_api)
    print("Profile image updated!")
