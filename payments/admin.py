# payments/admin.py
from django.contrib import admin
from .models import PaymentMethodConfig, PaymentTransaction


@admin.register(PaymentMethodConfig)
class PaymentMethodConfigAdmin(admin.ModelAdmin):
    list_display = ("method", "surcharge_percent")
    list_editable = ("surcharge_percent",)
    search_fields = ("method",)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "merchant_transaction_id",
        "amount",
        "status",
        "payment_state",
        "phonepe_transaction_id",
        "created_at",
    )
    list_filter = ("status", "payment_state", "created_at")
    search_fields = (
        "merchant_transaction_id",
        "phonepe_transaction_id",
        "order__order_number",
        "order__customer_name",
        "order__phone",
    )
    readonly_fields = (
        "order",
        "merchant_transaction_id",
        "amount",
        "phonepe_transaction_id",
        "raw_initiate_response",
        "raw_status_response",
        "status",
        "payment_state",
        "message",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "order",
                    "merchant_transaction_id",
                    "phonepe_transaction_id",
                    "amount",
                    "status",
                    "payment_state",
                    "message",
                )
            },
        ),
        (
            "Raw Responses",
            {
                "classes": ("collapse",),
                "fields": ("raw_initiate_response", "raw_status_response"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
