from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from adminapp.models import Product  # adjust import to your app

class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return ["home", "collections"]  # use your named URL patterns

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Product.objects.filter(is_active=True)  # or your filter

    def lastmod(self, obj):
        return obj.updated_at  # adjust to your field

    def location(self, obj):
        # If frontend product URL is /product/<id>
        return f"/product/{obj.id}"
