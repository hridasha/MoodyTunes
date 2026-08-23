from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from musicapp.models import Song, PlaylistGroup, Playlist, Favourite, Rating, MoodLog
from musicapp.views import next_playlist_position, song_queue_json
from musicapp.text_mood import classify_text_mood

from .permissions import IsPlaylistOwnerOrCollaborator
from .serializers import (
    SongSerializer, PlaylistGroupSerializer, FavouriteSerializer,
    RatingSerializer, MoodLogSerializer,
)


class SongViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SongSerializer

    def get_queryset(self):
        songs = Song.objects.filter(status='Approved')
        mood = self.request.query_params.get('mood')
        language = self.request.query_params.get('language')
        q = self.request.query_params.get('q')
        if mood:
            songs = songs.filter(mood=mood)
        if language:
            songs = songs.filter(language=language)
        if q:
            songs = songs.filter(Q(name__icontains=q) | Q(artist__icontains=q))
        return songs


class PlaylistViewSet(viewsets.ModelViewSet):
    serializer_class = PlaylistGroupSerializer
    permission_classes = [IsPlaylistOwnerOrCollaborator]

    def get_queryset(self):
        return PlaylistGroup.objects.filter(
            Q(owner=self.request.user) | Q(collaborators=self.request.user)).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def add_song(self, request, pk=None):
        group = self.get_object()
        song = Song.objects.filter(pk=request.data.get('song_id')).first()
        if not song:
            return Response({'error': 'song not found'}, status=status.HTTP_404_NOT_FOUND)
        Playlist.objects.create(
            user=request.user, song=song, playlist_name=group.name,
            group=group, position=next_playlist_position(group))
        return Response(PlaylistGroupSerializer(group).data)

    @action(detail=True, methods=['post'])
    def remove_song(self, request, pk=None):
        group = self.get_object()
        Playlist.objects.filter(group=group, song_id=request.data.get('song_id')).delete()
        return Response(PlaylistGroupSerializer(group).data)

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        group = self.get_object()
        try:
            song_id = int(request.data.get('song_id'))
        except (TypeError, ValueError):
            return Response({'error': 'song_id must be an integer'},
                             status=status.HTTP_400_BAD_REQUEST)
        direction = request.data.get('direction')
        entries = list(Playlist.objects.filter(group=group).order_by('position', 'id'))
        index = next((i for i, e in enumerate(entries) if e.song_id == song_id), None)
        if index is not None:
            swap_index = index - 1 if direction == 'up' else index + 1
            if 0 <= swap_index < len(entries):
                entries[index].position, entries[swap_index].position = (
                    entries[swap_index].position, entries[index].position)
                entries[index].save()
                entries[swap_index].save()
        return Response(PlaylistGroupSerializer(group).data)


class FavouriteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FavouriteSerializer

    def get_queryset(self):
        return Favourite.objects.filter(user=self.request.user, is_fav=True)

    @action(detail=False, methods=['post'])
    def toggle(self, request):
        song = Song.objects.filter(pk=request.data.get('song_id')).first()
        if not song:
            return Response({'error': 'song not found'}, status=status.HTTP_404_NOT_FOUND)
        existing = Favourite.objects.filter(user=request.user, song=song, is_fav=True)
        if existing.exists():
            existing.delete()
            return Response({'is_favourite': False})
        Favourite.objects.create(user=request.user, song=song, is_fav=True)
        return Response({'is_favourite': True})


class RatingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RatingSerializer

    def get_queryset(self):
        return Rating.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def rate(self, request):
        song_id = request.data.get('song_id')
        value = request.data.get('value')
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = 0
        if not (1 <= value <= 5) or not Song.objects.filter(pk=song_id).exists():
            return Response({'error': 'invalid song_id or value (1-5)'},
                             status=status.HTTP_400_BAD_REQUEST)
        rating, _ = Rating.objects.update_or_create(
            user=request.user, song_id=song_id, defaults={'value': value})
        return Response(RatingSerializer(rating).data)


class MoodLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MoodLogSerializer

    def get_queryset(self):
        return MoodLog.objects.filter(user=self.request.user).order_by('-detected_at')


class TextMoodAPIView(APIView):
    def post(self, request):
        text = (request.data.get('text') or '').strip()
        if not text:
            return Response({'error': 'text is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            mood = classify_text_mood(text)
        except Exception:
            return Response({'error': 'could not analyze that text'},
                             status=status.HTTP_502_BAD_GATEWAY)
        MoodLog.objects.create(user=request.user, mood=mood, source='text')
        songs = Song.objects.filter(mood=mood, status='Approved')
        return Response({'mood': mood, 'songs': song_queue_json(songs)})
