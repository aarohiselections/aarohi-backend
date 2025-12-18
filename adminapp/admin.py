from django.contrib import admin
from .models import (
    FlashSale,
    Category,
    FabricType,
    Color,
    Product,
    ProductImage,
    Announcement,
    Banner,
    PromoCode,
)
import webcolors
# ----------------------------
# FLASH SALE ADMIN
# ----------------------------
@admin.register(FlashSale)
class FlashSaleAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "end_date", "is_active", "created_at")
    list_editable = ("is_active",)
    search_fields = ("title",)
    list_filter = ("is_active", "end_date", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    fieldsets = (
        ("Flash Sale Info", {"fields": ("title", "end_date", "is_active")}),
        ("Meta", {"fields": ("created_at",), "classes": ("collapse",)}),
    )


# ----------------------------
# CATEGORY ADMIN
# ----------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)


# ----------------------------
# FABRIC TYPE ADMIN
# ----------------------------
@admin.register(FabricType)
class FabricTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)


# ----------------------------
# COLOR ADMIN
# ----------------------------
@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "hex_value")
    search_fields = ("name", "hex_value")

    def save_model(self, request, obj, form, change):
        if not obj.hex_value:
            try:
                obj.hex_value = webcolors.name_to_hex(obj.name.lower())
            except ValueError:
                obj.hex_value = '#FFFFFF'  # fallback if color name invalid
        super().save_model(request, obj, form, change)

# ----------------------------
# INLINE PRODUCT IMAGES
# ----------------------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


# ----------------------------
# PRODUCT ADMIN
# ----------------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "category", "fabric_type", "price", "discount_percent",
        "in_stock",
    )
    list_editable = ("discount_percent", "in_stock")
    list_filter = ("category", "fabric_type", "in_stock")
    search_fields = ("name", "description")
    ordering = ("name",)

    filter_horizontal = ("colors",)  # M2M field: better UX

    inlines = [ProductImageInline]

    fieldsets = (
        ("Basic Info", {
            "fields": ("name", "description", "category", "fabric_type")
        }),
        ("Pricing", {
            "fields": ("price", "discount_percent")
        }),
        ("Stock & Colors", {
            "fields": ("in_stock", "colors")
        }),
    )


# ----------------------------
# PRODUCT IMAGE ADMIN
# ----------------------------
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("id", "product")
    search_fields = ("product__name",)


# ----------------------------
# ANNOUNCEMENT ADMIN
# ----------------------------
@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "is_active", "created_at")
    list_editable = ("is_active",)
    search_fields = ("message",)
    list_filter = ("is_active", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    fieldsets = (
        ("Announcement", {"fields": ("message", "is_active")}),
        ("Meta", {"fields": ("created_at",), "classes": ("collapse",)}),
    )


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'subtitle', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'subtitle')

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code",
        "discount_type",
        "discount_value",
        "min_order_total",
        "is_active",
        "valid_from",
        "valid_to",
        "usage_limit",
        "times_used",
        "created_at",
    )
    list_filter = ("discount_type", "is_active", "valid_from", "valid_to")
    search_fields = ("code", "description")
    ordering = ("-created_at",)
    readonly_fields = ("times_used", "created_at", "updated_at")

from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_id", "product_name", "quantity", "unit_price", "subtotal")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer_name", "phone", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order_number", "customer_name", "phone", "promo_code")
    inlines = [OrderItemInline]
    readonly_fields = ("order_number", "tracking_number", "created_at", "updated_at")
    fieldsets = (
        (None, {
            "fields": ("order_number", "status", "tracking_number", "tracking_link")
        }),
        ("Customer", {
            "fields": ("customer_name", "email", "phone")
        }),
        ("Address", {
            "fields": ("address", "city", "state", "pincode")
        }),
        ("Totals & Promo", {
            "fields": ("subtotal", "discount_amount", "total", "promo_code", "promo_details")
        }),
        ("Other", {"fields": ("notes",)}),
    )

