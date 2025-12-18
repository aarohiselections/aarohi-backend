"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include
from .sitemaps import StaticViewSitemap, ProductSitemap
from django.contrib.sitemaps.views import sitemap
from django.urls import path
from payments.views import PhonePeInitiateView, PhonePeStatusView

sitemaps = {
    "static": StaticViewSitemap,
    "products": ProductSitemap,
}
urlpatterns = [
    
    path("admin/", admin.site.urls),
    path("api/", include("adminapp.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django-sitemap"),
    path("phonepe/initiate/", PhonePeInitiateView.as_view(), name="phonepe-initiate"),
    path("phonepe/status/", PhonePeStatusView.as_view(), name="phonepe-status"),
    path("payments/", include("payments.urls")),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)