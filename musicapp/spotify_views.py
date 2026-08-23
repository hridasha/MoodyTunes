import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from . import spotify
from .models import SpotifyAccount


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
        data = spotify.api_get(request.user, '/search', {'q': query, 'type': 'track', 'limit': 20})
    except Exception:
        return JsonResponse({'error': 'Spotify search failed'}, status=502)
    if data is None:
        return JsonResponse({'error': 'Spotify account not connected'}, status=404)

    tracks = [
        {
            'uri': t['uri'],
            'name': t['name'],
            'artist': ', '.join(a['name'] for a in t['artists']),
            'album': t['album']['name'],
            'image': (t['album']['images'][0]['url'] if t['album']['images'] else ''),
            'external_url': t['external_urls'].get('spotify', ''),
        }
        for t in data.get('tracks', {}).get('items', [])
    ]
    return JsonResponse({'tracks': tracks})
