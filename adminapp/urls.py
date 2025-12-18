from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductListView,
    ProductDetailView,
    CategoryViewSet,
    FabricTypeViewSet,
    ColorViewSet,
    FlashSaleViewSet,
    AnnouncementViewSet,
    BannerListView,
    LatestProductsView,
    PromoCodeViewSet,
    ApplyPromoCodeView,
    CreateOrderView,
    TrackOrderView,
    product_meta_view
)

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"fabrics", FabricTypeViewSet, basename="fabric")
router.register(r"colors", ColorViewSet, basename="color")
router.register(r"flash-sales", FlashSaleViewSet, basename="flashsale")
router.register(r"announcements", AnnouncementViewSet, basename="announcement")
router.register(r"promocodes", PromoCodeViewSet, basename="promocode")  # NEW

urlpatterns = [
    path("", include(router.urls)),
    path("banners/", BannerListView.as_view(), name="banner-list"),

    path("products/list/", ProductListView.as_view(), name="product-list"),
    path("products/<int:id>/detail/", ProductDetailView.as_view(), name="product-detail"),
    path("products/latest/", LatestProductsView.as_view(), name="latest-products"),

    path("promo/apply/", ApplyPromoCodeView.as_view(), name="apply-promocode"),
    path("orders/create/", CreateOrderView.as_view(), name="order-create"),
    path(
        "orders/track/<str:order_number>/",
        TrackOrderView.as_view(),
        name="order-track",
    ),
    path("product/<int:id>/", product_meta_view, name="product-meta"),
]
