import secrets

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.html import format_html

from . import spotify
from .models import Playlist, PlaylistGroup, Song, SpotifyAccount, SpotifyTrack


def _handle_spotify_error(request, exc, redirect_name='spotify_hub'):
    if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code in (401, 403):
        messages.error(
            request, 'Your Spotify permissions are out of date. Disconnect and reconnect your account.')
    else:
        messages.error(request, 'Spotify request failed. Try again in a moment.')
    return redirect(redirect_name)


def _get_or_create_spotify_track(track):
    obj, _ = SpotifyTrack.objects.update_or_create(
        uri=track['uri'],
        defaults={
            'name': track['name'],
            'artist': track['artist'],
            'album': track.get('album', ''),
            'image': track.get('image', ''),
            'external_url': track.get('external_url', ''),
        },
    )
    return obj


@login_required(login_url='login')
def spotify_hub(request):
    account = SpotifyAccount.objects.filter(user=request.user).first()
    product = None
    if account:
        try:
            me = spotify.api_get(request.user, '/me')
            product = me.get('product') if me else None
        except Exception:
            product = None

    context = {
        'connected': account is not None,
        'is_premium': product == 'premium',
        'product': product,
        'configured': bool(settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET),
    }
    return render(request, 'musicapp/spotify.html', context)


@login_required(login_url='login')
def spotify_connect(request):
    if not settings.SPOTIFY_CLIENT_ID:
        messages.error(request, 'Spotify integration is not configured on this server.')
        return redirect('spotify_hub')
    state = secrets.token_urlsafe(24)
    request.session['spotify_oauth_state'] = state
    return redirect(spotify.get_authorize_url(state))


@login_required(login_url='login')
def spotify_callback(request):
    error = request.GET.get('error')
    if error:
        messages.error(request, f'Spotify authorization failed: {error}')
        return redirect('spotify_hub')

    state = request.GET.get('state')
    expected_state = request.session.pop('spotify_oauth_state', None)
    if not state or state != expected_state:
        messages.error(request, 'Spotify login could not be verified. Try connecting again.')
        return redirect('spotify_hub')

    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Spotify did not return an authorization code.')
        return redirect('spotify_hub')

    try:
        spotify.exchange_code_for_token(request.user, code)
        messages.success(request, 'Spotify account connected!')
    except Exception:
        messages.error(request, 'Could not complete Spotify authorization. Try again.')
    return redirect('spotify_hub')


@login_required(login_url='login')
def spotify_disconnect(request):
    if request.method == 'POST':
        SpotifyAccount.objects.filter(user=request.user).delete()
        messages.success(request, 'Spotify account disconnected.')
    return redirect('spotify_hub')


@login_required(login_url='login')
def spotify_token(request):
    token = spotify.get_valid_token(request.user)
    if not token:
        return JsonResponse({'error': 'Spotify account not connected'}, status=404)
    return JsonResponse({'access_token': token})


@login_required(login_url='login')
def spotify_search(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'tracks': []})
    try:
        tracks = spotify.search_tracks(request.user, query, limit=20)
    except Exception:
        return JsonResponse({'error': 'Spotify search failed'}, status=502)
    if tracks is None:
        return JsonResponse({'error': 'Spotify account not connected'}, status=404)
    return JsonResponse({'tracks': tracks})


@login_required(login_url='login')
def spotify_import_hub(request):
    if not spotify.get_valid_token(request.user):
        messages.error(request, 'Connect your Spotify account first.')
        return redirect('spotify_hub')
    try:
        playlists = spotify.get_user_playlists(request.user)
    except Exception as exc:
        return _handle_spotify_error(request, exc)
    return render(request, 'musicapp/spotify_import.html', {'playlists': playlists or []})


@login_required(login_url='login')
def spotify_import_liked(request):
    if request.method != 'POST':
        return redirect('spotify_import_hub')
    try:
        tracks = spotify.get_liked_songs(request.user)
    except Exception as exc:
        return _handle_spotify_error(request, exc, 'spotify_import_hub')

    if not tracks:
        messages.error(request, 'No liked songs found on Spotify.')
        return redirect('spotify_import_hub')

    group = PlaylistGroup.objects.create(name='Spotify Liked Songs', owner=request.user)
    for position, track in enumerate(tracks):
        spotify_track = _get_or_create_spotify_track(track)
        Playlist.objects.create(
            user=request.user, playlist_name=group.name, group=group,
            spotify_track=spotify_track, position=position)
    messages.success(request, f'Imported {len(tracks)} liked songs into "{group.name}".')
    return redirect('playlist_songs', group_id=group.id)


@login_required(login_url='login')
def spotify_import_playlist(request, playlist_id):
    if request.method != 'POST':
        return redirect('spotify_import_hub')
    playlist_name = request.POST.get('playlist_name', 'Imported Spotify Playlist').strip()
    try:
        tracks = spotify.get_playlist_tracks(request.user, playlist_id)
    except Exception as exc:
        return _handle_spotify_error(request, exc, 'spotify_import_hub')

    if not tracks:
        messages.error(request, 'That playlist has no tracks to import.')
        return redirect('spotify_import_hub')

    group = PlaylistGroup.objects.create(name=playlist_name, owner=request.user)
    for position, track in enumerate(tracks):
        spotify_track = _get_or_create_spotify_track(track)
        Playlist.objects.create(
            user=request.user, playlist_name=group.name, group=group,
            spotify_track=spotify_track, position=position)
    messages.success(request, f'Imported {len(tracks)} songs into "{group.name}".')
    return redirect('playlist_songs', group_id=group.id)


@login_required(login_url='login')
def spotify_export_group(request, group_id):
    if request.method != 'POST':
        return redirect('playlist_songs', group_id=group_id)

    group = PlaylistGroup.objects.filter(pk=group_id).first()
    if not group or not group.can_edit(request.user):
        messages.error(request, "You don't have access to that playlist.")
        return redirect('playlist')

    if not spotify.get_valid_token(request.user):
        messages.error(request, 'Connect your Spotify account first.')
        return redirect('spotify_hub')

    entries = Playlist.objects.filter(group=group).order_by('position', 'id')
    uris = []
    skipped = 0
    try:
        for entry in entries:
            if entry.spotify_track:
                uris.append(entry.spotify_track.uri)
            elif entry.song:
                matches = spotify.search_tracks(
                    request.user, f'{entry.song.name} {entry.song.artist}', limit=1)
                if matches:
                    uris.append(matches[0]['uri'])
                else:
                    skipped += 1

        if not uris:
            messages.error(request, 'None of these songs could be matched on Spotify.')
            return redirect('playlist_songs', group_id=group.id)

        created = spotify.create_playlist(
            request.user, group.name, description='Exported from MoodyTunes')
        if not created:
            messages.error(request, 'Could not create the Spotify playlist.')
            return redirect('playlist_songs', group_id=group.id)

        spotify.add_tracks_to_playlist(request.user, created['id'], uris)
    except Exception as exc:
        return _handle_spotify_error(request, exc, 'playlist_songs')

    external_url = created.get('external_urls', {}).get('spotify', '')
    note = f' ({skipped} song(s) could not be matched.)' if skipped else ''
    base_text = f'Exported "{group.name}" to Spotify with {len(uris)} track(s).{note}'
    if external_url:
        messages.success(request, format_html(
            '{} <a href="{}" target="_blank" rel="noopener">Open on Spotify</a>', base_text, external_url))
    else:
        messages.success(request, base_text)
    return redirect('playlist_songs', group_id=group.id)


@login_required(login_url='login')
def spotify_mood_recommendations(request):
    moods = [choice[0] for choice in Song.Mood_Choice if choice[0] != 'Non']
    mood = request.GET.get('mood', 'Happy')
    if mood not in moods:
        mood = 'Happy'

    tracks = []
    if spotify.get_valid_token(request.user):
        try:
            tracks = spotify.search_mood_tracks(request.user, mood, limit=20) or []
        except Exception as exc:
            _handle_spotify_error(request, exc, 'spotify_mood_recommendations')

    context = {
        'moods': moods,
        'mood': mood,
        'tracks': tracks,
        'connected': spotify.get_valid_token(request.user) is not None,
    }
    return render(request, 'musicapp/spotify_recommendations.html', context)


@login_required(login_url='login')
def spotify_export_tracks(request):
    if request.method != 'POST':
        return redirect('spotify_mood_recommendations')

    uris = request.POST.getlist('uris')
    mood = request.POST.get('mood', 'Mood')
    if not uris:
        messages.error(request, 'Select at least one track to export.')
        return redirect(f'/spotify/recommendations/?mood={mood}')

    try:
        created = spotify.create_playlist(
            request.user, f'MoodyTunes — {mood}', description=f'{mood} mood mix from MoodyTunes')
        if not created:
            messages.error(request, 'Could not create the Spotify playlist.')
        else:
            spotify.add_tracks_to_playlist(request.user, created['id'], uris)
            external_url = created.get('external_urls', {}).get('spotify', '')
            base_text = f'Created "MoodyTunes — {mood}" on Spotify with {len(uris)} track(s).'
            if external_url:
                messages.success(request, format_html(
                    '{} <a href="{}" target="_blank" rel="noopener">Open on Spotify</a>', base_text, external_url))
            else:
                messages.success(request, base_text)
    except Exception as exc:
        return _handle_spotify_error(request, exc, 'spotify_mood_recommendations')

    return redirect(f'/spotify/recommendations/?mood={mood}')
