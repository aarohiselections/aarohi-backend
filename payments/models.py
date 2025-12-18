# payments/models.py
from django.db import models
from adminapp.models import Order

class PaymentMethodConfig(models.Model):
    METHOD_CHOICES = [
        ("upi", "UPI"),
        ("card", "Credit Card"),
        ("debit_card", "Debit Card"),
        ("wallet", "Wallet"),
    ]

    method = models.CharField(max_length=20, choices=METHOD_CHOICES, unique=True)
    surcharge_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.get_method_display()} ({self.surcharge_percent}%)"


class PaymentTransaction(models.Model):
    """
    Stores each interaction/attempt with PhonePe for a particular order.
    """

    STATUS_CHOICES = (
        ("initiated", "Initiated"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("pending", "Pending"),
    )

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="transactions"
    )

    # Merchant side
    merchant_transaction_id = models.CharField(max_length=64, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # PhonePe side
    phonepe_transaction_id = models.CharField(
      max_length=128, blank=True, help_text="PhonePe providerReferenceId or transactionId"
    )
    raw_initiate_response = models.JSONField(blank=True, null=True)
    raw_status_response = models.JSONField(blank=True, null=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="initiated"
    )
    payment_state = models.CharField(
        max_length=50, blank=True, help_text="PhonePe data.state or paymentState"
    )
    message = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.merchant_transaction_id} ({self.status})"
