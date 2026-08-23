from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

from . import views

router = DefaultRouter()
router.register('songs', views.SongViewSet, basename='api-song')
router.register('playlists', views.PlaylistViewSet, basename='api-playlist')
router.register('favourites', views.FavouriteViewSet, basename='api-favourite')
router.register('ratings', views.RatingViewSet, basename='api-rating')
router.register('mood-log', views.MoodLogViewSet, basename='api-mood-log')

urlpatterns = [
    path('auth/token/', obtain_auth_token, name='api-token'),
    path('mood/text/', views.TextMoodAPIView.as_view(), name='api-mood-text'),
    path('', include(router.urls)),
]
