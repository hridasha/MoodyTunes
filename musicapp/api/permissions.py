from rest_framework import permissions


class IsPlaylistOwnerOrCollaborator(permissions.BasePermission):
    """Read/edit if owner or collaborator; rename/delete owner-only.

    Mirrors the same rules already enforced in musicapp/views.py
    (playlist_songs / rename_playlist / delete_playlist).
    """

    def has_object_permission(self, request, view, obj):
        if request.method in ('PUT', 'PATCH', 'DELETE'):
            return request.user == obj.owner
        return obj.can_edit(request.user)
