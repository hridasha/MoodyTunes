import base64
import json
import logging
from collections import Counter
from datetime import timedelta

from django.shortcuts import render, redirect
from .models import *
from .forms import SongUploadForm
from .text_mood import classify_text_mood
from django.db.models import Q, Avg, Count
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
import cv2
from deepface import DeepFace
import numpy as np


def next_playlist_position(group):
    last = Playlist.objects.filter(group=group).order_by('-position').first()
    return last.position + 1 if last else 0


def song_queue_json(songs):
    return [
        {
            'id': song.song_id,
            'name': song.name,
            'artist': song.artist,
            'image': song.image.url,
            'url': song.song_file.url,
            'mood': song.mood,
        }
        for song in songs
    ]


def index(request):
    if not request.user.is_anonymous:
        recent = list(Recent.objects.filter(
            user=request.user).values('song_id').order_by('song_id'))
        recent_id = [each['song_id'] for each in recent][:7]
        recent_songs_unsorted = Song.objects.filter(
            song_id__in=recent_id, recent__user=request.user)
        recent_songs = list()
        for song_id in recent_id:
            recent_songs.append(recent_songs_unsorted.get(song_id=song_id))
    else:
        recent = None
        recent_songs = None

    first_time = False

    if not request.user.is_anonymous:
        last_played_list = list(Recent.objects.filter(
            user=request.user).values('song_id').order_by('song_id'))
        if last_played_list:
            last_played_id = last_played_list[0]['song_id']
            last_played_song = Song.objects.get(song_id=last_played_id)
        else:
            first_time = True
            last_played_song = Song.objects.get(song_id=7)

    else:
        first_time = True
        last_played_song = Song.objects.get(song_id=7)

    song = Song.objects.filter(status='Approved')

    songs_english = list(Song.objects.filter(
        language='English', status='Approved').values('song_id'))
    sliced_ids = [each['song_id'] for each in songs_english][:6]
    indexpage_english_songs = Song.objects.filter(song_id__in=sliced_ids)

    songs_hindi = list(Song.objects.filter(language='Hindi', status='Approved').values('song_id'))
    sliced_ids = [each['song_id'] for each in songs_hindi][:6]
    indexpage_hindi_songs = Song.objects.filter(song_id__in=sliced_ids)

    songs_all = list(Song.objects.filter(status='Approved').values('song_id').order_by('?'))
    sliced_ids = [each['song_id'] for each in songs_all][:6]
    indexpage_songs = Song.objects.filter(song_id__in=sliced_ids)

    context = {'all_songs': indexpage_songs,
               'recent_songs': recent_songs,
               'hindi_songs': indexpage_hindi_songs,
               'english_songs': indexpage_english_songs,
               'last_played': last_played_song,
               'first_time': first_time,
               }
    return render(request, 'musicapp/index.html', context=context)


def english_songs(request):

    english_songs = Song.objects.filter(language='English', status='Approved')
    last_played_list = list(Recent.objects.values(
        'song_id').order_by('song_id'))
    if last_played_list:
        last_played_id = last_played_list[0]['song_id']
        last_played_song = Song.objects.get(song_id=last_played_id)
    else:
        last_played_song = Song.objects.get(song_id=7)

    query = request.GET.get('q')

    if query:
        english_songs = Song.objects.filter(
            Q(name__icontains=query), status='Approved').distinct()
        context = {'english_songs': english_songs}
        return render(request, 'musicapp/english_songs.html', context)

    context = {'english_songs': english_songs, 'last_played': last_played_song}
    return render(request, 'musicapp/english_songs.html', context=context)


def happy_song(request):

    happy_song = Song.objects.filter(mood='Happy', status='Approved')
    context = {'happy_song': happy_song, 'songs_json': song_queue_json(happy_song)}
    return render(request, 'musicapp/happy_song.html', context)


def sad_song(request):
    sad_song = Song.objects.filter(mood='Sad', status='Approved')
    context = {'sad_song': sad_song, 'songs_json': song_queue_json(sad_song)}
    return render(request, 'musicapp/sad_song.html', context)


def neutral_song(request):
    neutral_song = Song.objects.filter(mood='Neutral', status='Approved')
    last_played_list = list(Recent.objects.values(
        'song_id').order_by('song_id'))
    if last_played_list:
        last_played_id = last_played_list[0]['song_id']
        last_played_song = Song.objects.get(song_id=last_played_id)
    else:
        last_played_song = Song.objects.get(song_id=7)
    context = {'neutral_song': neutral_song,  'last_played': last_played_song,
               'songs_json': song_queue_json(neutral_song)}
    return render(request, 'musicapp/neutral_song.html', context)


def angry_song(request):
    angry_song = Song.objects.filter(mood='Angry', status='Approved')
    last_played_list = list(Recent.objects.values(
        'song_id').order_by('song_id'))
    if last_played_list:
        last_played_id = last_played_list[0]['song_id']
        last_played_song = Song.objects.get(song_id=last_played_id)
    else:
        last_played_song = Song.objects.get(song_id=7)
    context = {'angry_song': angry_song,  'last_played': last_played_song,
               'songs_json': song_queue_json(angry_song)}
    return render(request, 'musicapp/angry_song.html', context)


def fear_song(request):
    fear_song = Song.objects.filter(mood='Fear', status='Approved')
    last_played_list = list(Recent.objects.values(
        'song_id').order_by('song_id'))
    if last_played_list:
        last_played_id = last_played_list[0]['song_id']
        last_played_song = Song.objects.get(song_id=last_played_id)
    else:
        last_played_song = Song.objects.get(song_id=7)
    context = {'fear_song': fear_song,  'last_played': last_played_song,
               'songs_json': song_queue_json(fear_song)}
    return render(request, 'musicapp/fear_song.html', context)


def hindi_songs(request):

    hindi_songs = Song.objects.filter(language='Hindi', status='Approved')
    last_played_list = list(Recent.objects.values(
        'song_id').order_by('song_id'))
    if last_played_list:
        last_played_id = last_played_list[0]['song_id']
        last_played_song = Song.objects.get(song_id=last_played_id)
    else:
        last_played_song = Song.objects.get(song_id=7)

    query = request.GET.get('q')

    if query:
        hindi_songs = Song.objects.filter(
            Q(name__icontains=query), status='Approved').distinct()
        context = {'hindi_songs': hindi_songs}
        return render(request, 'musicapp/hindi_songs.html', context)

    context = {'hindi_songs': hindi_songs, 'last_played': last_played_song}
    return render(request, 'musicapp/hindi_songs.html', context=context)


@login_required(login_url='login')
def play_song(request, id):
    songs = Song.objects.filter(song_id=id).first()
    if list(Recent.objects.filter(song=songs, user=request.user).values()):
        data = Recent.objects.filter(song=songs, user=request.user)
        data.delete()
    data = Recent(song=songs, user=request.user)
    data.save()
    return redirect('all_songs')


@login_required(login_url='login')
def play_song_index(request, id):
    songs = Song.objects.filter(song_id=id).first()
    if list(Recent.objects.filter(song=songs, user=request.user).values()):
        data = Recent.objects.filter(song=songs, user=request.user)
        data.delete()
    data = Recent(song=songs, user=request.user)
    data.save()
    return redirect('index')


@login_required(login_url='login')
def play_recent_song(request, id):
    songs = Song.objects.filter(song_id=id).first()
    # Add data to recent database
    if list(Recent.objects.filter(song=songs, user=request.user).values()):
        data = Recent.objects.filter(song=songs, user=request.user)
        data.delete()
    data = Recent(song=songs, user=request.user)
    data.save()
    return redirect('recent')


@login_required(login_url='login')
def allsong(request):
    songs = Song.objects.filter(status='Approved')

    first_time = False
    if not request.user.is_anonymous:
        last_played_list = list(Recent.objects.filter(
            user=request.user).values('song_id').order_by('song_id'))
        if last_played_list:
            last_played_id = last_played_list[0]['song_id']
            last_played_song = Song.objects.get(song_id=last_played_id)
    else:
        first_time = True
        last_played_song = Song.objects.get(song_id=7)

    qs_artists = Song.objects.values_list('artist').all()
    a_list = [a.split(',') for artist in qs_artists for a in artist]
    all_artist = sorted(
        list(set([a.strip() for artist in a_list for a in artist])))
    qs_languages = Song.objects.values_list('language').all()
    all_languages = sorted(
        list(set([l.strip() for lang in qs_languages for l in lang])))
    all_moods = [choice[0] for choice in Song.Mood_Choice if choice[0] != 'Non']

    if len(request.GET) > 0:
        search_query = request.GET.get('q') or ''
        search_artist = request.GET.get('artists') or ''
        search_language = request.GET.get('languages') or ''
        search_mood = request.GET.get('mood') or ''
        filtered_songs = songs.filter(Q(name__icontains=search_query)).filter(
            Q(language__icontains=search_language)).filter(
            Q(artist__icontains=search_artist)).filter(
            Q(mood__icontains=search_mood)).distinct()
        context = {
            'songs': filtered_songs,
            'last_played': last_played_song,
            'all_artist': all_artist,
            'all_languages': all_languages,
            'all_moods': all_moods,
            'query_search': True,
            'songs_json': song_queue_json(filtered_songs),
        }
        return render(request, 'musicapp/all_songs.html', context)

    context = {
        'songs': songs,
        'last_played': last_played_song,
        'first_time': first_time,
        'all_artist': all_artist,
        'all_languages': all_languages,
        'all_moods': all_moods,
        'query_search': False,
        'songs_json': song_queue_json(songs),
    }
    return render(request, 'musicapp/all_songs.html', context=context)


def recent(request):
    last_played_list = list(Recent.objects.values(
        'song_id').order_by('song_id'))
    if last_played_list:
        last_played_id = last_played_list[0]['song_id']
        last_played_song = Song.objects.get(song_id=last_played_id)
    else:
        last_played_song = Song.objects.get(song_id=7)
    recent = list(Recent.objects.filter(
        user=request.user).values('song_id').order_by('song_id'))
    recent_id = [each['song_id'] for each in recent][:6]
    recent_songs_unsorted = Song.objects.filter(
        song_id__in=recent_id, recent__user=request.user)
    recent_songs = list()
    for song_id in recent_id:
        recent_songs.append(recent_songs_unsorted.get(song_id=song_id))
    else:
        recent = None
        recent_songs = None

    context = {'recent_songs': recent_songs, 'last_played': last_played_song, }
    return render(request, 'musicapp/recent.html', context=context)


@login_required(login_url='login')
def player(request, id):
    songs = Song.objects.filter(song_id=id).first()
    if list(Recent.objects.filter(song=songs, user=request.user).values()):
        data = Recent.objects.filter(song=songs, user=request.user)
        data.delete()
    data = Recent(song=songs, user=request.user)
    data.save()
    last_played_list = list(Recent.objects.values(
        'song_id').order_by('song_id'))
    if last_played_list:
        last_played_id = last_played_list[0]['song_id']
        last_played_song = Song.objects.get(song_id=last_played_id)
    else:
        last_played_song = Song.objects.get(song_id=7)

    playlists = PlaylistGroup.objects.filter(
        Q(owner=request.user) | Q(collaborators=request.user)).distinct()
    is_favourite = Favourite.objects.filter(
        user=request.user).filter(song=id).values('is_fav')

    if request.method == "POST":
        if 'add_to_group' in request.POST:
            group = playlists.filter(pk=request.POST['add_to_group']).first()
            if group:
                Playlist.objects.create(
                    user=request.user, song=songs, playlist_name=group.name,
                    group=group, position=next_playlist_position(group))
                messages.success(request, "Song added to playlist!")
        elif 'new_playlist_name' in request.POST:
            name = request.POST['new_playlist_name'].strip()
            if name:
                group = PlaylistGroup.objects.create(name=name, owner=request.user)
                Playlist.objects.create(
                    user=request.user, song=songs, playlist_name=name, group=group, position=0)
                messages.success(request, "Playlist created and song added!")
        elif 'add-fav' in request.POST:
            is_fav = True
            query = Favourite(user=request.user, song=songs, is_fav=is_fav)
            print(f'query: {query}')
            query.save()
            messages.success(request, "Added to favorite!")
            return redirect('player', id=id)
        elif 'rm-fav' in request.POST:
            is_fav = True
            query = Favourite.objects.filter(
                user=request.user, song=songs, is_fav=is_fav)
            print(f'user: {request.user}')
            print(f'song: {songs.song_id} - {songs}')
            print(f'query: {query}')
            query.delete()
            messages.success(request, "Removed from favorite!")
            return redirect('player', id=id)

    context = {'songs': songs, 'playlists': playlists,
               'is_favourite': is_favourite, 'last_played': last_played_song,
               'song_json': song_queue_json([songs])[0]}
    return render(request, 'musicapp/player.html', context=context)


@login_required(login_url='login')
def detail(request, id):
    songs = Song.objects.filter(song_id=id).first()

    if list(Recent.objects.filter(song=songs, user=request.user).values()):
        data = Recent.objects.filter(song=songs, user=request.user)
        data.delete()
    data = Recent(song=songs, user=request.user)
    data.save()
    last_played_list = list(Recent.objects.values(
        'song_id').order_by('song_id'))
    if last_played_list:
        last_played_id = last_played_list[0]['song_id']
        last_played_song = Song.objects.get(song_id=last_played_id)
    else:
        last_played_song = Song.objects.get(song_id=7)

    playlists = PlaylistGroup.objects.filter(
        Q(owner=request.user) | Q(collaborators=request.user)).distinct()
    is_favourite = Favourite.objects.filter(
        user=request.user).filter(song=id).values('is_fav')

    if request.method == "POST":

        if 'add_to_group' in request.POST:
            group = playlists.filter(pk=request.POST['add_to_group']).first()
            if group:
                Playlist.objects.create(
                    user=request.user, song=songs, playlist_name=group.name,
                    group=group, position=next_playlist_position(group))
                messages.success(request, "Song added to playlist!")
        elif 'new_playlist_name' in request.POST:
            name = request.POST['new_playlist_name'].strip()
            if name:
                group = PlaylistGroup.objects.create(name=name, owner=request.user)
                Playlist.objects.create(
                    user=request.user, song=songs, playlist_name=name, group=group, position=0)
                messages.success(request, "Playlist created and song added!")
        elif 'add-fav' in request.POST:
            is_fav = True
            query = Favourite(user=request.user, song=songs, is_fav=is_fav)
            print(f'query: {query}')
            query.save()
            messages.success(request, "Added to favorite!")
            return redirect('detail', id=id)
        elif 'rm-fav' in request.POST:
            is_fav = True
            query = Favourite.objects.filter(
                user=request.user, song=songs, is_fav=is_fav)
            print(f'user: {request.user}')
            print(f'song: {songs.song_id} - {songs}')
            print(f'query: {query}')
            query.delete()
            messages.success(request, "Removed from favorite!")
            return redirect('detail', id=id)

    rating_stats = Rating.objects.filter(song=songs).aggregate(
        avg=Avg('value'), count=Count('id'))
    user_rating = Rating.objects.filter(
        user=request.user, song=songs).values_list('value', flat=True).first()

    context = {'songs': songs, 'playlists': playlists,
               'is_favourite': is_favourite, 'last_played': last_played_song,
               'song_json': song_queue_json([songs])[0],
               'avg_rating': rating_stats['avg'], 'rating_count': rating_stats['count'],
               'user_rating': user_rating or 0}
    return render(request, 'musicapp/detail.html', context=context)


@login_required(login_url='login')
def search(request):
    songs = Song.objects.filter(status='Approved')
    if len(request.GET) > 0:
        search_query = request.GET.get('q')
        filtered_songs = songs.filter(Q(name__icontains=search_query))
        context = {
            'songs': filtered_songs,
            'query_search': True,
        }
        return render(request, 'musicapp/search.html', context)

    context = {
        'songs': songs,
        'query_search': False,
    }
    return render(request, 'musicapp/search.html', context=context)


@login_required(login_url='login')
def playlist(request):
    playlists = PlaylistGroup.objects.filter(
        Q(owner=request.user) | Q(collaborators=request.user)).distinct()

    context = {'playlists': playlists}
    return render(request, 'musicapp/playlist.html', context=context)


@login_required(login_url='login')
def playlist_songs(request, group_id):
    group = PlaylistGroup.objects.filter(pk=group_id).first()
    if not group or not group.can_edit(request.user):
        messages.error(request, "You don't have access to that playlist.")
        return redirect('playlist')

    entries = Playlist.objects.filter(group=group).order_by('position', 'id')
    local_songs = [entry.song for entry in entries if entry.song]

    if request.method == "POST":
        if 'remove_entry' in request.POST:
            entry_id = request.POST['remove_entry']
            Playlist.objects.filter(group=group, pk=entry_id).delete()
            messages.success(request, "Song removed from playlist!")
            return redirect('playlist_songs', group_id=group.id)
        elif 'add_collaborator' in request.POST and request.user == group.owner:
            username = request.POST['add_collaborator'].strip()
            collaborator = User.objects.filter(username=username).exclude(pk=group.owner_id).first()
            if collaborator:
                group.collaborators.add(collaborator)
                messages.success(request, f"Added {collaborator.username} as a collaborator!")
            else:
                messages.error(request, "No such user to add.")
            return redirect('playlist_songs', group_id=group.id)
        elif 'remove_collaborator' in request.POST and request.user == group.owner:
            group.collaborators.remove(request.POST['remove_collaborator'])
            messages.success(request, "Collaborator removed.")
            return redirect('playlist_songs', group_id=group.id)
        elif 'leave_playlist' in request.POST and request.user != group.owner:
            group.collaborators.remove(request.user)
            messages.success(request, "You left the playlist.")
            return redirect('playlist')

    context = {'group': group, 'entries': entries,
               'songs_json': song_queue_json(local_songs),
               'is_owner': request.user == group.owner,
               'spotify_connected': SpotifyAccount.objects.filter(user=request.user).exists()}

    return render(request, 'musicapp/playlist_songs.html', context=context)


@login_required(login_url='login')
def rename_playlist(request, group_id):
    group = PlaylistGroup.objects.filter(pk=group_id, owner=request.user).first()
    if not group:
        messages.error(request, "Only the owner can rename this playlist.")
        return redirect('playlist')
    if request.method == "POST":
        new_name = request.POST.get('new_name', '').strip()
        if new_name:
            group.name = new_name
            group.save()
            messages.success(request, "Playlist renamed!")
    return redirect('playlist_songs', group_id=group.id)


@login_required(login_url='login')
def delete_playlist(request, group_id):
    group = PlaylistGroup.objects.filter(pk=group_id, owner=request.user).first()
    if not group:
        messages.error(request, "Only the owner can delete this playlist.")
        return redirect('playlist')
    if request.method == "POST":
        group.delete()
        messages.success(request, "Playlist deleted!")
    return redirect('playlist')


@login_required(login_url='login')
def move_playlist_song(request, group_id, entry_id, direction):
    group = PlaylistGroup.objects.filter(pk=group_id).first()
    if not group or not group.can_edit(request.user):
        messages.error(request, "You don't have access to that playlist.")
        return redirect('playlist')

    entries = list(Playlist.objects.filter(group=group).order_by('position', 'id'))
    index = next((i for i, e in enumerate(entries) if e.id == entry_id), None)
    if index is not None:
        swap_index = index - 1 if direction == 'up' else index + 1
        if 0 <= swap_index < len(entries):
            entries[index].position, entries[swap_index].position = (
                entries[swap_index].position, entries[index].position)
            entries[index].save()
            entries[swap_index].save()
    return redirect('playlist_songs', group_id=group.id)


def favourite(request):
    songs = Song.objects.filter(
        favourite__user=request.user, favourite__is_fav=True).distinct()
    print(f'songs: {songs}')

    if request.method == "POST" and 'remove_song' in request.POST:
        song_id = request.POST['remove_song']
        Favourite.objects.filter(
            user=request.user, song_id=song_id, is_fav=True).delete()
        messages.success(request, "Removed from favourite!")
        return redirect('favourite')
    context = {'songs': songs}
    return render(request, 'musicapp/fav.html', context=context)


@login_required(login_url='login')
def rate_song(request, id):
    if request.method == "POST":
        try:
            value = int(request.POST.get('value', 0))
        except ValueError:
            value = 0
        if 1 <= value <= 5:
            Rating.objects.update_or_create(
                user=request.user, song_id=id, defaults={'value': value})
            messages.success(request, "Thanks for rating!")
    return redirect('detail', id=id)


@login_required(login_url='login')
def popular_songs(request):
    songs = Song.objects.filter(status='Approved').annotate(
        avg_rating=Avg('rating__value'), rating_count=Count('rating')
    ).filter(rating_count__gt=0).order_by('-avg_rating')

    context = {'songs': songs, 'songs_json': song_queue_json(songs)}
    return render(request, 'musicapp/popular_songs.html', context=context)


@login_required(login_url='login')
def mymusic(request):
    return render(request, 'musicapp/mymusic.html')


@login_required(login_url='login')
def upload_song(request):
    if request.method == 'POST':
        form = SongUploadForm(request.POST, request.FILES)
        if form.is_valid():
            song = form.save(commit=False)
            song.status = 'Pending'
            song.uploaded_by = request.user
            song.save()
            messages.success(
                request, 'Song submitted! An admin will review it before it appears publicly.')
            return redirect('my_uploads')
    else:
        form = SongUploadForm()
    return render(request, 'musicapp/upload_song.html', {'form': form})


@login_required(login_url='login')
def my_uploads(request):
    songs = Song.objects.filter(uploaded_by=request.user).order_by('-song_id')
    return render(request, 'musicapp/my_uploads.html', {'songs': songs})


@login_required(login_url='login')
def mood_history(request):
    logs = MoodLog.objects.filter(user=request.user).order_by('-detected_at')
    total = logs.count()
    summary = list(
        MoodLog.objects.filter(user=request.user)
        .values('mood').annotate(count=Count('id')).order_by('-count')
    )
    for row in summary:
        row['pct'] = round(100 * row['count'] / total) if total else 0

    source_summary = list(
        MoodLog.objects.filter(user=request.user)
        .values('source').annotate(count=Count('id')).order_by('-count')
    )

    today = timezone.localdate()
    days = [today - timedelta(days=i) for i in range(29, -1, -1)]
    day_logs = MoodLog.objects.filter(user=request.user, detected_at__date__gte=days[0])

    counts_by_day = {}
    for entry in day_logs.values('mood', 'detected_at'):
        day = timezone.localtime(entry['detected_at']).date()
        counts_by_day.setdefault(day, Counter())[entry['mood']] += 1

    timeline = []
    for day in days:
        day_counts = counts_by_day.get(day)
        dominant = max(day_counts, key=day_counts.get) if day_counts else None
        timeline.append({
            'date': day.strftime('%b %d'),
            'mood': dominant,
            'count': sum(day_counts.values()) if day_counts else 0,
        })

    context = {
        'logs': logs, 'summary': summary, 'total': total,
        'source_summary': source_summary, 'timeline': timeline,
    }
    return render(request, 'musicapp/mood_history.html', context)


@login_required(login_url='login')
def mood_from_text(request):
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if not text:
            messages.error(request, 'Type something about how you feel first.')
        else:
            try:
                mood = classify_text_mood(text)
                MoodLog.objects.create(user=request.user, mood=mood, source='text')
                return redirect(mood_page_urls()[mood])
            except Exception:
                logger.exception('mood_from_text failed')
                messages.error(
                    request, 'Could not analyze that text right now. Try again.')
    return render(request, 'musicapp/mood_text.html')


def mood_page_urls():
    return {
        'Happy': reverse('happy_song'),
        'Sad': reverse('sad_song'),
        'Angry': reverse('angry_song'),
        'Fear': reverse('fear_song'),
        'Neutral': reverse('neutral_song'),
    }


@login_required(login_url='login')
def cam(request):
    return render(request, 'musicapp/camera.html', {'mood_urls': mood_page_urls()})

EMOTION_TO_MOOD = {
    'happy': 'Happy',
    'sad': 'Sad',
    'angry': 'Angry',
    'fear': 'Fear',
    'neutral': 'Neutral',
    'disgust': 'Angry',
    'surprise': 'Happy',
}


logger = logging.getLogger(__name__)


@login_required(login_url='login')
def detect_mood(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        payload = json.loads(request.body)
        image_data = payload['image']
        if ',' in image_data:
            image_data = image_data.split(',', 1)[1]
        image_bytes = base64.b64decode(image_data)
        frame = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if frame is None or frame.size == 0:
            raise ValueError(
                f'Could not decode image (bytes={len(image_bytes)}, '
                f'shape={getattr(frame, "shape", None)})'
            )

        result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
        emotion = result[0]['dominant_emotion']
        mood = EMOTION_TO_MOOD.get(emotion, 'Neutral')
        MoodLog.objects.create(user=request.user, mood=mood, source='camera')
        return JsonResponse({'mood': mood})
    except Exception:
        logger.exception('detect_mood failed')
        return JsonResponse({'error': 'Could not detect a mood from that image. Try again with better lighting and your face centered.'}, status=400)
