from rest_framework import serializers

from musicapp.models import Song, PlaylistGroup, Playlist, Favourite, Rating, MoodLog


class SongSerializer(serializers.ModelSerializer):
    class Meta:
        model = Song
        fields = ['song_id', 'name', 'artist', 'mood', 'language', 'tags',
                  'image', 'song_file', 'status']


class PlaylistSongSerializer(serializers.ModelSerializer):
    song = SongSerializer(read_only=True)

    class Meta:
        model = Playlist
        fields = ['id', 'song', 'position']


class PlaylistGroupSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    collaborators = serializers.SlugRelatedField(
        slug_field='username', many=True, read_only=True)
    songs = serializers.SerializerMethodField()

    class Meta:
        model = PlaylistGroup
        fields = ['id', 'name', 'owner', 'collaborators', 'created_at', 'songs']

    def get_songs(self, obj):
        items = Playlist.objects.filter(group=obj).order_by('position', 'id')
        return PlaylistSongSerializer(items, many=True).data


class FavouriteSerializer(serializers.ModelSerializer):
    song = SongSerializer(read_only=True)

    class Meta:
        model = Favourite
        fields = ['id', 'song', 'is_fav']


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'song', 'value']


class MoodLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoodLog
        fields = ['id', 'mood', 'source', 'detected_at']
