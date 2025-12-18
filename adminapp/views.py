from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.filters import SearchFilter
from django.db.models import Q
from .models import Product
from .serializers import ProductSerializer
from rest_framework import viewsets
from .models import Announcement
from .serializers import AnnouncementSerializer
from .models import FlashSale
from .serializers import FlashSaleSerializer
from rest_framework import viewsets
from .models import Category, FabricType, Color
from .serializers import CategorySerializer, FabricTypeSerializer, ColorSerializer
from .models import Banner
from .serializers import BannerSerializer
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import PromoCode, Order
from .serializers import PromoCodeSerializer, ApplyPromoCodeSerializer
from .serializers import OrderSerializer
from django.shortcuts import render, get_object_or_404
from .models import Product

# ----------------------------
# CATEGORY VIEWSET
# ----------------------------
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    # Optional: allow search by name
    filterset_fields = ['name']
    search_fields = ['name']


# ----------------------------
# FABRIC TYPE VIEWSET
# ----------------------------
class FabricTypeViewSet(viewsets.ModelViewSet):
    queryset = FabricType.objects.all()
    serializer_class = FabricTypeSerializer
    filterset_fields = ['name']
    search_fields = ['name']


# ----------------------------
# COLOR VIEWSET
# ----------------------------
class ColorViewSet(viewsets.ModelViewSet):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    filterset_fields = ['name', 'hex_value']
    search_fields = ['name', 'hex_value']

class FlashSaleViewSet(viewsets.ModelViewSet):
    queryset = FlashSale.objects.all()
    serializer_class = FlashSaleSerializer

class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer

class ProductListView(ListAPIView):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()
    filter_backends = [SearchFilter]
    search_fields = ["name", "description"]

    def get_queryset(self):
        qs = Product.objects.all()

        request = self.request
        params = request.query_params

        # Filters
        category = params.get("category")
        fabric = params.get("fabric")
        color = params.get("color")
        in_stock = params.get("in_stock")
        discount = params.get("discount")
        min_price = params.get("min_price")
        max_price = params.get("max_price")
        sort = params.get("sort")

        if category and category != "All":
            qs = qs.filter(category__name=category)

        if fabric and fabric != "All":
            qs = qs.filter(fabric_type__name=fabric)

        if color:
            qs = qs.filter(colors__name=color)

        if in_stock == "true":
            qs = qs.filter(in_stock=True)

        if discount == "true":
            qs = qs.filter(discount_percent__gt=0)

        if min_price:
            qs = qs.filter(price__gte=min_price)

        if max_price:
            qs = qs.filter(price__lte=max_price)

        # Sort options
        if sort == "price_low":
            qs = qs.order_by("price")
        elif sort == "price_high":
            qs = qs.order_by("-price")
        elif sort == "discount":
            qs = qs.order_by("-discount_percent")
        elif sort == "name_az":
            qs = qs.order_by("name")
        elif sort == "name_za":
            qs = qs.order_by("-name")

        return qs.distinct()


class ProductDetailView(RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = "id"


class BannerListView(generics.ListAPIView):
    queryset = Banner.objects.filter(is_active=True)
    serializer_class = BannerSerializer


class LatestProductsView(APIView):
    """
    API to get latest added products.
    Optionally can provide `?limit=4` as query param.
    """
    def get(self, request):
        limit = int(request.query_params.get("limit", 4))
        latest_products = Product.objects.all().order_by('-created_at')[:limit]
        
        # FIX: Pass context={'request': request} so image URLs become absolute
        serializer = ProductSerializer(
            latest_products, 
            many=True, 
            context={'request': request} 
        )
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    

# ... your existing views ...


class PromoCodeViewSet(viewsets.ModelViewSet):
    """
    Optional: CRUD for promo codes (admin use via API).
    """
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    filterset_fields = ["code", "discount_type", "is_active"]
    search_fields = ["code", "description"]


class ApplyPromoCodeView(APIView):
    """
    POST /api/promocodes/apply/
    Body: { "code": "DIWALI10", "cart_total": "2500.00" }

    Returns:
    {
      "code": "DIWALI10",
      "description": "...",
      "discount_type": "percentage",
      "discount_value": "10.00",
      "min_order_total": "2000.00",
      "discount_amount": "250.00",
      "final_total": "2250.00"
    }
    """

    def post(self, request, *args, **kwargs):
        serializer = ApplyPromoCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        promo = serializer.validated_data["promo"]
        discount_amount = serializer.validated_data["discount_amount"]
        cart_total = serializer.validated_data["cart_total"]

        final_total = cart_total - discount_amount

        # Optionally increase usage count here (only when you really apply at checkout):
        # promo.times_used += 1
        # promo.save(update_fields=["times_used"])

        data = {
            "code": promo.code,
            "description": promo.description,
            "discount_type": promo.discount_type,
            "discount_value": str(promo.discount_value),
            "min_order_total": str(promo.min_order_total),
            "max_discount_amount": (
                str(promo.max_discount_amount)
                if promo.max_discount_amount is not None
                else None
            ),
            "discount_amount": str(discount_amount),
            "final_total": str(final_total),
        }
        return Response(data, status=status.HTTP_200_OK)

class CreateOrderView(APIView):
    """
    POST /api/orders/create/
    Body contains: customer info, totals, promo info, and items.
    """

    def post(self, request, *args, **kwargs):
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()  # order.status defaults to 'unpaid'
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
class TrackOrderView(RetrieveAPIView):
    """
    GET /api/orders/track/<order_number>/
    Returns order details by order_number.
    """
    serializer_class = OrderSerializer
    lookup_field = "order_number"
    queryset = Order.objects.all()

def product_meta_view(request, id):
    product = get_object_or_404(Product, id=id)
    # Adjust image selection as needed
    first_image = product.productimage_set.first()
    image_url = request.build_absolute_uri(first_image.image.url) if first_image else ""

    context = {
        "product": product,
        "og_image": image_url,
        "full_url": request.build_absolute_uri(request.path),
    }
    return render(request, "product_meta.html", context)
