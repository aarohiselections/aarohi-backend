from django.db import models
from decimal import Decimal
from colorfield.fields import ColorField
import uuid
from django.utils import timezone

class FlashSale(models.Model):
    title = models.CharField(max_length=200, default="Flash Sale Ends In")
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class FabricType(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Color(models.Model):
    name = models.CharField(max_length=100)
    hex_value = ColorField(default='#FFFFFF')  # Adds color picker in admin automatically

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    fabric_type = models.ForeignKey(FabricType, on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.IntegerField(default=0)
    in_stock = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    colors = models.ManyToManyField(Color)

    @property
    def discount_price(self):
        discount_fraction = Decimal(self.discount_percent) / Decimal('100')
        return self.price * (Decimal('1') - discount_fraction)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')

class Announcement(models.Model):
    message = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.message


class Banner(models.Model):
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=500, blank=True, null=True)
    image = models.ImageField(upload_to='banners/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    

class PromoCode(models.Model):
    DISCOUNT_TYPE_PERCENTAGE = "percentage"
    DISCOUNT_TYPE_FIXED = "fixed"

    DISCOUNT_TYPE_CHOICES = [
        (DISCOUNT_TYPE_PERCENTAGE, "Percentage"),
        (DISCOUNT_TYPE_FIXED, "Fixed Amount"),
    ]

    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True)
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default=DISCOUNT_TYPE_PERCENTAGE,
    )
    # percentage: 10 means 10%
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Minimum cart total required to apply this code",
    )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional cap on discount amount",
    )
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Max number of uses across all customers (leave blank for unlimited)",
    )
    times_used = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.code

    def can_be_used(self, cart_total: Decimal) -> bool:
        """
        Basic checks: active, within date range, min order total, usage limit.
        """
        from django.utils import timezone

        if not self.is_active:
            return False

        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False

        if cart_total < self.min_order_total:
            return False

        if self.usage_limit is not None and self.times_used >= self.usage_limit:
            return False

        return True

    def get_discount_amount(self, cart_total: Decimal) -> Decimal:
        """
        Compute the discount amount for a given cart_total,
        respecting discount type and max_discount_amount.
        """
        if not self.can_be_used(cart_total):
            return Decimal("0.00")

        if self.discount_type == self.DISCOUNT_TYPE_PERCENTAGE:
            discount = (cart_total * self.discount_value) / Decimal("100")
        else:
            discount = self.discount_value

        if self.max_discount_amount is not None:
            discount = min(discount, self.max_discount_amount)

        # Never exceed cart total
        return max(Decimal("0.00"), min(discount, cart_total))



class Order(models.Model):
    STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
    ]

    order_number = models.CharField(
        max_length=20, unique=True, editable=False
    )
    # customer + address from checkout form
    customer_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=20)

    # totals
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)

    # promo
    promo_code = models.CharField(max_length=50, blank=True)
    promo_details = models.CharField(max_length=255, blank=True)

    # status / tracking
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="unpaid"
    )
    PAYMENT_METHOD_CHOICES = (
        ("upi", "UPI"),
        ("card", "Credit Card"),
        ("debit_card", "Debit Card"),
        ("wallet", "Wallet"),
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="upi",
    )
    payment_surcharge_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    payment_surcharge_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    tracking_number = models.CharField(
        max_length=50, blank=True, help_text="Internal tracking reference"
    )
    tracking_link = models.URLField(
        max_length=500, blank=True, help_text="External tracking URL for customer"
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def _generate_order_number(self):
        """
        Simple unique order number like AS202512120001.
        Adjust prefix/format as needed.
        """
        prefix = "AS"
        today = timezone.now().strftime("%Y%m%d")
        rand = uuid.uuid4().hex[:4].upper()
        return f"{prefix}{today}{rand}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Ensure uniqueness
            while True:
                candidate = self._generate_order_number()
                if not Order.objects.filter(order_number=candidate).exists():
                    self.order_number = candidate
                    break
        if not self.tracking_number:
            self.tracking_number = self.order_number
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, related_name="items", on_delete=models.CASCADE
    )
    product_id = models.CharField(max_length=50)
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    category_name = models.CharField(max_length=255, blank=True)
    fabric_type_name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
