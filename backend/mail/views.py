from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle
from rest_framework.viewsets import ModelViewSet

from .models import Label
from .serializers import (
    LabelSerializer,
    MailboxEntryDetailSerializer,
    MessageComposeSerializer,
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


class MessageComposeView(GenericAPIView):
    throttle_classes = (UserRateThrottle, ScopedRateThrottle)
    throttle_scope = 'compose'
    serializer_class = MessageComposeSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        entry = message.entries.get(user=request.user)
        return Response(
            MailboxEntryDetailSerializer(entry, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )
