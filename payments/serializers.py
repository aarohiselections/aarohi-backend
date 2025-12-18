# payments/serializers.py
from rest_framework import serializers
from .models import PaymentMethodConfig


class PaymentMethodConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethodConfig
        fields = ["method", "surcharge_percent"]
