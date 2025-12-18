# payments/urls.py
from rest_framework.routers import DefaultRouter
from .views import PaymentMethodConfigViewSet

router = DefaultRouter()
router.register("payment-method-config", PaymentMethodConfigViewSet, basename="payment-method-config")

urlpatterns = router.urls
