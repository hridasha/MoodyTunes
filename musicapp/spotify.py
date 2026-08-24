import urllib.parse
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

from .models import SpotifyAccount

AUTHORIZE_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE = 'https://api.spotify.com/v1'
SCOPES = (
    'streaming user-read-email user-read-private '
    'user-modify-playback-state user-read-playback-state '
    'user-library-read playlist-read-private playlist-read-collaborative '
    'playlist-modify-private playlist-modify-public'
)

# Spotify killed Recommendations/Audio Features for any app created after
# 2024-11-27 (https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api).
# There's no access path for new apps, so mood matching here is done with
# curated search queries instead of audio-feature targets.
MOOD_SEARCH_QUERIES = {
    'Happy': ['feel good hits', 'genre:"pop" happy', 'upbeat dance'],
    'Sad': ['sad songs', 'genre:"acoustic" heartbreak', 'melancholy piano'],
    'Angry': ['rage workout', 'genre:"metal" angry', 'aggressive rock'],
    'Fear': ['dark ambient', 'tense soundtrack', 'genre:"industrial" unsettling'],
    'Neutral': ['chill lofi', 'genre:"ambient" calm', 'easy listening'],
}


def get_authorize_url(state):
    params = {
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
        'scope': SCOPES,
        'state': state,
    }
    return f'{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}'


def exchange_code_for_token(user, code):
    resp = requests.post(TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'client_secret': settings.SPOTIFY_CLIENT_SECRET,
    }, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    expires_at = timezone.now() + timedelta(seconds=payload['expires_in'])
    account, _ = SpotifyAccount.objects.update_or_create(
        user=user,
        defaults={
            'access_token': payload['access_token'],
            'refresh_token': payload['refresh_token'],
            'expires_at': expires_at,
        },
    )
    return account


def refresh_access_token(account):
    resp = requests.post(TOKEN_URL, data={
        'grant_type': 'refresh_token',
        'refresh_token': account.refresh_token,
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'client_secret': settings.SPOTIFY_CLIENT_SECRET,
    }, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    account.access_token = payload['access_token']
    if 'refresh_token' in payload:
        account.refresh_token = payload['refresh_token']
    account.expires_at = timezone.now() + timedelta(seconds=payload['expires_in'])
    account.save()
    return account


def get_valid_token(user):
    account = SpotifyAccount.objects.filter(user=user).first()
    if not account:
        return None
    if account.expires_at <= timezone.now() + timedelta(seconds=60):
        account = refresh_access_token(account)
    return account.access_token


def api_get(user, path, params=None):
    token = get_valid_token(user)
    if not token:
        return None
    resp = requests.get(
        f'{API_BASE}{path}',
        headers={'Authorization': f'Bearer {token}'},
        params=params or {},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def api_post(user, path, json_body=None):
    token = get_valid_token(user)
    if not token:
        return None
    resp = requests.post(
        f'{API_BASE}{path}',
        headers={'Authorization': f'Bearer {token}'},
        json=json_body or {},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _track_summary(t):
    return {
        'uri': t['uri'],
        'name': t['name'],
        'artist': ', '.join(a['name'] for a in t['artists']),
        'album': t['album']['name'],
        'image': (t['album']['images'][0]['url'] if t['album']['images'] else ''),
        'external_url': t['external_urls'].get('spotify', ''),
    }


def search_tracks(user, query, limit=20):
    data = api_get(user, '/search', {'q': query, 'type': 'track', 'limit': limit})
    if data is None:
        return None
    return [_track_summary(t) for t in data.get('tracks', {}).get('items', [])]


def search_mood_tracks(user, mood, limit=20):
    queries = MOOD_SEARCH_QUERIES.get(mood, MOOD_SEARCH_QUERIES['Neutral'])
    seen = set()
    tracks = []
    per_query = max(1, limit // len(queries) + 1)
    for query in queries:
        data = api_get(user, '/search', {'q': query, 'type': 'track', 'limit': per_query})
        if not data:
            continue
        for t in data.get('tracks', {}).get('items', []):
            if t['uri'] in seen:
                continue
            seen.add(t['uri'])
            tracks.append(_track_summary(t))
            if len(tracks) >= limit:
                return tracks
    return tracks


def get_liked_songs(user, cap=200):
    tracks = []
    url_path = '/me/tracks'
    params = {'limit': 50}
    while url_path and len(tracks) < cap:
        if url_path.startswith('http'):
            data = _api_get_absolute(user, url_path)
        else:
            data = api_get(user, url_path, params)
        if not data:
            break
        for item in data.get('items', []):
            track = item.get('track')
            if track:
                tracks.append(_track_summary(track))
        next_url = data.get('next')
        if not next_url:
            break
        url_path = next_url
        params = None
    return tracks[:cap]


def _api_get_absolute(user, url):
    token = get_valid_token(user)
    if not token:
        return None
    resp = requests.get(url, headers={'Authorization': f'Bearer {token}'}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_user_playlists(user):
    data = api_get(user, '/me/playlists', {'limit': 50})
    if data is None:
        return None
    return [
        {'id': p['id'], 'name': p['name'], 'track_count': p['tracks']['total'], 'image': (
            p['images'][0]['url'] if p.get('images') else '')}
        for p in data.get('items', [])
    ]


def get_playlist_tracks(user, playlist_id, cap=300):
    tracks = []
    url_path = f'/playlists/{playlist_id}/tracks'
    params = {'limit': 100}
    while url_path and len(tracks) < cap:
        if url_path.startswith('http'):
            data = _api_get_absolute(user, url_path)
        else:
            data = api_get(user, url_path, params)
        if not data:
            break
        for item in data.get('items', []):
            track = item.get('track')
            if track:
                tracks.append(_track_summary(track))
        next_url = data.get('next')
        if not next_url:
            break
        url_path = next_url
        params = None
    return tracks[:cap]


def get_current_spotify_user_id(user):
    me = api_get(user, '/me')
    return me.get('id') if me else None


def create_playlist(user, name, description='', public=False):
    spotify_user_id = get_current_spotify_user_id(user)
    if not spotify_user_id:
        return None
    return api_post(user, f'/users/{spotify_user_id}/playlists', {
        'name': name,
        'description': description,
        'public': public,
    })


def add_tracks_to_playlist(user, playlist_id, uris):
    for i in range(0, len(uris), 100):
        chunk = uris[i:i + 100]
        api_post(user, f'/playlists/{playlist_id}/tracks', {'uris': chunk})
