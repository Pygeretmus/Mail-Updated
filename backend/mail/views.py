from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import Label, MailboxEntry
from .pagination import StandardPagination
from .serializers import (
    LabelSerializer,
    MailboxEntryDetailSerializer,
    MailboxEntryListSerializer,
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


@extend_schema_view(
    list=extend_schema(
        description='Filter by label name (`?label=inbox`) or view trash (`?deleted=true`).',
        parameters=[
            OpenApiParameter(
                name='label',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Label name, case-insensitive (e.g. "inbox").',
            ),
            OpenApiParameter(
                name='deleted',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Set to "true" to view trash instead of the mailbox.',
            ),
        ],
        responses=MailboxEntryListSerializer(many=True),
    ),
    retrieve=extend_schema(
        responses=MailboxEntryDetailSerializer,
    ),
)
class MailboxViewSet(ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)
    pagination_class = StandardPagination

    def get_queryset(self):
        # Turn off swagger warning
        if getattr(self, 'swagger_fake_view', False):
            return MailboxEntry.objects.none()
        qs = (
            MailboxEntry.objects.filter(user=self.request.user)
            .select_related('message', 'message__sender')
            .prefetch_related('labels')
            .order_by('-message__created_at')
        )

        if self.action == 'list':
            if self.request.query_params.get('deleted') == 'true':
                return qs.filter(deleted_at__isnull=False)
            qs = qs.filter(deleted_at__isnull=True)
            if label := self.request.query_params.get('label'):
                qs = qs.filter(labels__name__iexact=label)
            return qs

        return qs.with_recipients()

    def get_serializer_class(self):
        if self.action == 'list':
            return MailboxEntryListSerializer
        return MailboxEntryDetailSerializer
