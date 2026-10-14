from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import LabelViewSet, MailboxViewSet, MessageComposeView, MessageReplyView, ThreadMessagesView

app_name = 'mail'

router = DefaultRouter()
router.register('labels', LabelViewSet, basename='label')
router.register('mailbox', MailboxViewSet, basename='mailbox')

urlpatterns = router.urls + [
    path('messages/compose/', MessageComposeView.as_view(), name='message-compose'),
    path('messages/<int:pk>/reply/', MessageReplyView.as_view(), name='message-reply'),
    path('messages/thread/<int:thread_id>/', ThreadMessagesView.as_view(), name='message-thread'),
]
