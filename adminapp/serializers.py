from rest_framework import serializers
from .models import Product, ProductImage, Category, FabricType, Color
from rest_framework import serializers
from .models import Announcement
from rest_framework import serializers
from .models import FlashSale, Banner, PromoCode
from decimal import Decimal

class FlashSaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlashSale
        fields = "__all__"
class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = "__all__"

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["image"]


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ["name", "hex_value"]


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True)
    colors = ColorSerializer(many=True)
    discountPrice = serializers.SerializerMethodField()
    discountPercent = serializers.IntegerField(source="discount_percent")
    category_name = serializers.CharField(source="category.name", read_only=True)
    fabric_type_name = serializers.CharField(source="fabric_type.name", read_only=True)
    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "price",
            "discountPrice",
            "discountPercent",
            "in_stock",
            "category",
            "fabric_type",
            "category_name",     # NEW
            "fabric_type_name",  # NEW
            "created_at",
            "colors",
            "images"
        ]

    def get_discountPrice(self, obj):
        return Decimal(obj.discount_price)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class FabricTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FabricType
        fields = '__all__'


class BannerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = ('id', 'title', 'subtitle', 'image_url')

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


class PromoCodeSerializer(serializers.ModelSerializer):
  class Meta:
      model = PromoCode
      fields = [
          "id",
          "code",
          "description",
          "discount_type",
          "discount_value",
          "min_order_total",
          "max_discount_amount",
          "is_active",
          "valid_from",
          "valid_to",
          "usage_limit",
          "times_used",
      ]


class ApplyPromoCodeSerializer(serializers.Serializer):
    code = serializers.CharField()
    cart_total = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate(self, attrs):
        from django.utils import timezone

        code = attrs["code"].strip().upper()
        cart_total = attrs["cart_total"]

        try:
            promo = PromoCode.objects.get(code__iexact=code)
        except PromoCode.DoesNotExist:
            raise serializers.ValidationError(
                {"code": "Invalid promo code."}
            )

        if not promo.can_be_used(cart_total):
            # You can add more granular error messages if desired
            raise serializers.ValidationError(
                {"code": "Promo code cannot be applied to this order."}
            )

        discount_amount = promo.get_discount_amount(cart_total)
        attrs["promo"] = promo
        attrs["discount_amount"] = discount_amount
        return attrs

from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "product_id",
            "product_name",
            "quantity",
            "unit_price",
            "subtotal",
            "category_name",
            "fabric_type_name",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "customer_name",
            "email",
            "phone",
            "address",
            "city",
            "state",
            "pincode",
            "subtotal",
            "discount_amount",
            "total",
            "promo_code",
            "promo_details",
            "status",
            "tracking_number",
            "tracking_link", 
            "notes",
            "items",
            "created_at",
        ]
        read_only_fields = ["order_number", "status", "tracking_number", "created_at"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        order = Order.objects.create(**validated_data)
        for item in items_data:
          OrderItem.objects.create(order=order, **item)
        return order
