from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import Label
from .serializers import (
    LabelSerializer,
)


class LabelViewSet(ModelViewSet):
    serializer_class = LabelSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        # Turn off swagger warning
        if getattr(self, 'swagger_fake_view', False):
            return Label.objects.none()
        return Label.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.is_system:
            raise PermissionDenied("System labels can't be changed")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.is_system:
            raise PermissionDenied("System labels can't be changed")
        instance.delete()
