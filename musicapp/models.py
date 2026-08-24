from django.contrib.auth.models import User
from django.db import models

# Create your models here.

class Song(models.Model):
    Language_Choice = (
        ('Hindi', 'Hindi'),
        ('English', 'English'),
    )
    Mood_Choice = (
        ('Happy', 'Happy'),
        ('Sad', 'Sad'),
        ('Fear', 'Fear'),
        ('Angry', 'Angry'),
        ('Neutral', 'Neutral'),
        ('Non', 'Non'),
    )
    Status_Choice = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )
    song_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=2000)
    artist = models.CharField(max_length=2000)
    mood = models.CharField(max_length=20, choices=Mood_Choice, default='Non')
    language = models.CharField(max_length=20, choices=Language_Choice, default='Hindi')
    tags = models.CharField(max_length=100)
    image = models.ImageField()
    song_file = models.FileField()
    status = models.CharField(max_length=20, choices=Status_Choice, default='Approved')
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_songs')

    def __str__(self):
        return self.name


class PlaylistGroup(models.Model):
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_playlists')
    collaborators = models.ManyToManyField(User, related_name='shared_playlists', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def can_edit(self, user):
        return user.pk == self.owner_id or self.collaborators.filter(pk=user.pk).exists()

    def __str__(self):
        return self.name


class SpotifyTrack(models.Model):
    uri = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=500)
    artist = models.CharField(max_length=500)
    album = models.CharField(max_length=500, blank=True)
    image = models.URLField(max_length=1000, blank=True)
    external_url = models.URLField(max_length=1000, blank=True)

    def __str__(self):
        return f'{self.name} — {self.artist}'


class Playlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    playlist_name = models.CharField(max_length=200)
    song = models.ForeignKey(Song, on_delete=models.CASCADE, null=True, blank=True)
    spotify_track = models.ForeignKey(
        SpotifyTrack, on_delete=models.CASCADE, null=True, blank=True)
    position = models.PositiveIntegerField(default=0)
    group = models.ForeignKey(
        PlaylistGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='items')



class Favourite(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    is_fav = models.BooleanField(default=False)


class Recent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    value = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ('user', 'song')


class MoodLog(models.Model):
    Source_Choice = (
        ('camera', 'Camera'),
        ('text', 'Text'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mood = models.CharField(max_length=20, choices=Song.Mood_Choice)
    source = models.CharField(max_length=10, choices=Source_Choice, default='camera')
    detected_at = models.DateTimeField(auto_now_add=True)


class SpotifyAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='spotify_account')
    access_token = models.CharField(max_length=500)
    refresh_token = models.CharField(max_length=500)
    expires_at = models.DateTimeField()

