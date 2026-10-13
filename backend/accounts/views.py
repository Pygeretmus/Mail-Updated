from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.generics import CreateAPIView, GenericAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    AccountCreateSerializer,
    AccountPasswordChangeSerializer,
    AccountSerializer,
    AccountUpdateSerializer,
)

User = get_user_model()


class AccountCreateView(CreateAPIView):
    serializer_class = AccountCreateSerializer
    permission_classes = (AllowAny,)


class CurrentAccountView(RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        return AccountUpdateSerializer if self.request.method != 'GET' else AccountSerializer


class AccountPasswordChangeView(GenericAPIView):
    """
    View for changing account password.
    """

    serializer_class = AccountPasswordChangeSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.request.user, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'detail': 'Password successfully changed'}, status=status.HTTP_200_OK)
