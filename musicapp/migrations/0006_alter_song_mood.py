# Generated by Django 4.0 on 2022-03-29 19:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('musicapp', '0005_alter_song_mood'),
    ]

    operations = [
        migrations.AlterField(
            model_name='song',
            name='mood',
            field=models.CharField(choices=[('Happy', 'Happy'), ('Sad', 'Sad'), ('Fear', 'Fear'), ('Angry', 'Angry'), ('Neutral', 'Neutral'), ('Non', 'Non')], default='Non', max_length=20),
        ),
    ]
