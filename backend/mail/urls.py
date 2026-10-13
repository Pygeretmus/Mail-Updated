from rest_framework.routers import DefaultRouter

from .views import LabelViewSet

app_name = 'mail'

router = DefaultRouter()
router.register('labels', LabelViewSet, basename='label')

urlpatterns = router.urls
