from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import LabelViewSet, MessageComposeView

app_name = 'mail'

router = DefaultRouter()
router.register('labels', LabelViewSet, basename='label')

urlpatterns = router.urls + [
    path('messages/compose/', MessageComposeView.as_view(), name='message-compose'),
]
