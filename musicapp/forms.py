from django import forms
from django.core.validators import FileExtensionValidator

from .models import Song

MAX_AUDIO_SIZE = 15 * 1024 * 1024
MAX_IMAGE_SIZE = 5 * 1024 * 1024

AUDIO_EXTENSIONS = ['mp3', 'wav', 'm4a', 'ogg']
IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']


class SongUploadForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = ['name', 'artist', 'mood', 'language', 'tags', 'image', 'song_file']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'mt-input'}),
            'artist': forms.TextInput(attrs={'class': 'mt-input'}),
            'mood': forms.Select(attrs={'class': 'mt-select'}),
            'language': forms.Select(attrs={'class': 'mt-select'}),
            'tags': forms.TextInput(attrs={'class': 'mt-input', 'placeholder': 'e.g. bollywood, romantic'}),
        }

    def clean_song_file(self):
        song_file = self.cleaned_data['song_file']
        FileExtensionValidator(allowed_extensions=AUDIO_EXTENSIONS)(song_file)
        if song_file.size > MAX_AUDIO_SIZE:
            raise forms.ValidationError('Audio file must be 15MB or smaller.')
        return song_file

    def clean_image(self):
        image = self.cleaned_data['image']
        FileExtensionValidator(allowed_extensions=IMAGE_EXTENSIONS)(image)
        if image.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError('Image must be 5MB or smaller.')
        return image
