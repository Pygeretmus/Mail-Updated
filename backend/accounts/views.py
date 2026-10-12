from django.contrib.auth import get_user_model
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from .serializers import (
    AccountCreateSerializer,
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
