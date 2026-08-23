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
    'user-modify-playback-state user-read-playback-state'
)


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
