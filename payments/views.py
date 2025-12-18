# from decimal import Decimal
# from .models import PaymentTransaction
# from decimal import Decimal
# import hashlib

# from django.conf import settings
# from django.utils import timezone
# from django.shortcuts import redirect

# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status as drf_status

# from adminapp.models import Order, OrderItem
# from .phonepe_utils import phonepe_initiate_payment, phonepe_check_status
# from .models import PaymentMethodConfig, PaymentTransaction  # make sure these exist


# PHONEPE_WEBHOOK_USER = getattr(settings, "PHONEPE_WEBHOOK_USER", "")
# PHONEPE_WEBHOOK_PASS = getattr(settings, "PHONEPE_WEBHOOK_PASS", "")


# class PhonePeInitiateView(APIView):
#     """
#     POST /phonepe/initiate/
#     Body: orderPayload from frontend (customer info, totals, promo, items[]).
#     Backend recomputes payment surcharge from config and sends final total to PhonePe.
#     """

#     def post(self, request, *args, **kwargs):
#         data = request.data
#         items = data.get("items", [])

#         try:
#             # 1) Parse numeric fields
#             subtotal = Decimal(str(data.get("subtotal", "0")))
#             discount_amount = Decimal(str(data.get("discount_amount", "0")))
#             # base_total from frontend; you may recompute from items if you prefer
#             base_total = Decimal(str(data.get("base_total", data.get("total", "0"))))

#             # 2) Payment method
#             payment_method = data.get("payment_method", "upi")

#             # 3) Get surcharge percent from backend config (source of truth)
#             try:
#                 cfg = PaymentMethodConfig.objects.get(method=payment_method)
#                 surcharge_percent = cfg.surcharge_percent
#             except PaymentMethodConfig.DoesNotExist:
#                 surcharge_percent = Decimal("0")

#             payment_surcharge_amount = (base_total * surcharge_percent) / Decimal("100")
#             final_total = (base_total + payment_surcharge_amount).quantize(
#                 Decimal("0.01")
#             )

#             # 4) Create local Order
#             merchant_txn_id = f"TXN{int(timezone.now().timestamp())}"

#             order = Order.objects.create(
#                 order_number=merchant_txn_id,
#                 customer_name=data.get("customer_name", ""),
#                 email=data.get("email", ""),
#                 phone=data.get("phone", ""),
#                 address=data.get("address", ""),
#                 city=data.get("city", ""),
#                 state=data.get("state", ""),
#                 pincode=data.get("pincode", ""),
#                 subtotal=subtotal,
#                 discount_amount=discount_amount,
#                 total=final_total,
#                 promo_code=data.get("promo_code", ""),
#                 promo_details=data.get("promo_details", ""),
#                 status="unpaid",
#                 payment_method=payment_method,
#                 payment_surcharge_percent=surcharge_percent,
#                 payment_surcharge_amount=payment_surcharge_amount,
#             )

#             for item in items:
#                 OrderItem.objects.create(
#                     order=order,
#                     product_id=item["product_id"],
#                     product_name=item["product_name"],
#                     quantity=item["quantity"],
#                     unit_price=item["unit_price"],
#                     subtotal=item["subtotal"],
#                     category_name=item.get("category_name", ""),
#                     fabric_type_name=item.get("fabric_type_name", ""),
#                 )

#             # 5) Build PhonePe payload
#             amount_paise = int(final_total * 100)
#             merchant_id = settings.PHONEPE_MERCHANT_ID

#             redirect_url = (
#                 f"{request.build_absolute_uri('/phonepe/status/')}?txn={merchant_txn_id}"
#             )

#             payload = {
#                 "merchantId": merchant_id,
#                 "merchantTransactionId": merchant_txn_id,
#                 "merchantUserId": f"USER{order.id}",
#                 "amount": amount_paise,
#                 "redirectUrl": redirect_url,
#                 "redirectMode": "POST",
#                 "callbackUrl": redirect_url,  # or a dedicated webhook URL
#                 "mobileNumber": order.phone,
#                 "paymentInstrument": {"type": "PAY_PAGE"},
#             }

#             phonepe_resp = phonepe_initiate_payment(payload)

#             # 6) Create initial PaymentTransaction record
#             PaymentTransaction.objects.create(
#                 order=order,
#                 merchant_transaction_id=merchant_txn_id,
#                 amount=final_total,
#                 raw_initiate_response=phonepe_resp,
#                 status="initiated" if phonepe_resp.get("success") else "failed",
#                 message=phonepe_resp.get("message", ""),
#             )

#             # 7) Handle PhonePe initiate failure
#             if not phonepe_resp.get("success"):
#                 order.status = "failed"
#                 order.notes = f"PhonePe initiate failed: {phonepe_resp}"
#                 order.save(update_fields=["status", "notes"])
#                 return Response(
#                     {"error": "Failed to initiate payment", "details": phonepe_resp},
#                     status=drf_status.HTTP_502_BAD_GATEWAY,
#                 )

#             redirect_info = (
#                 phonepe_resp.get("data", {})
#                 .get("instrumentResponse", {})
#                 .get("redirectInfo", {})
#             )
#             pay_page_url = redirect_info.get("url")

#             if not pay_page_url:
#                 order.status = "failed"
#                 order.notes = f"No redirect URL from PhonePe: {phonepe_resp}"
#                 order.save(update_fields=["status", "notes"])
#                 PaymentTransaction.objects.filter(
#                     merchant_transaction_id=merchant_txn_id
#                 ).update(
#                     status="failed",
#                     message="No redirect URL from PhonePe",
#                 )
#                 return Response(
#                     {"error": "Payment gateway error"},
#                     status=drf_status.HTTP_502_BAD_GATEWAY,
#                 )

#             # 8) Return URL for redirecting user to PhonePe pay page
#             return Response(
#                 {
#                     "order_number": order.order_number,
#                     "redirect_url": pay_page_url,
#                 },
#                 status=drf_status.HTTP_200_OK,
#             )

#         except Exception as e:
#             return Response(
#                 {"error": "Server error initiating payment", "detail": str(e)},
#                 status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )



# class PhonePeStatusView(APIView):
#     authentication_classes = []
#     permission_classes = []

#     def get(self, request, *args, **kwargs):
#         return self._handle(request)

#     def post(self, request, *args, **kwargs):
#         return self._handle(request)

#     def _handle(self, request):
#         merchant_txn_id = request.query_params.get("txn")
#         if not merchant_txn_id:
#             return redirect(f"{settings.FRONTEND_BASE_URL}/payment-failed")

#         try:
#             order = Order.objects.get(order_number=merchant_txn_id)
#         except Order.DoesNotExist:
#             return redirect(f"{settings.FRONTEND_BASE_URL}/payment-failed")

#         try:
#             status_resp = phonepe_check_status(merchant_txn_id)
#             success = status_resp.get("success")
#             data = status_resp.get("data", {})
#             pay_state = data.get("state") or data.get("paymentState")

#             # Try to extract provider reference / transaction id if available
#             provider_ref = (
#                 data.get("providerReferenceId")
#                 or data.get("transactionId")
#             )

#             if success and pay_state == "COMPLETED":
#                 order.status = "paid"
#                 tx_status = "completed"
#             elif pay_state in (
#                 "FAILED",
#                 "PAYMENT_ERROR",
#                 "PAYMENT_CANCELLED",
#                 "PAYMENT_DECLINED",
#             ):
#                 order.status = "failed"
#                 tx_status = "failed"
#             else:
#                 order.status = "unpaid"
#                 tx_status = "pending"

#             order.notes = f"PhonePe status: {status_resp}"
#             order.save(update_fields=["status", "notes"])

#             # Update transaction record
#             PaymentTransaction.objects.filter(
#                 merchant_transaction_id=merchant_txn_id
#             ).update(
#                 phonepe_transaction_id=provider_ref or "",
#                 raw_status_response=status_resp,
#                 status=tx_status,
#                 payment_state=pay_state or "",
#                 message=status_resp.get("message", ""),
#             )

#             if order.status == "paid":
#                 return redirect(
#                     f"{settings.FRONTEND_BASE_URL}/payment-success?order={order.order_number}"
#                 )
#             return redirect(
#                 f"{settings.FRONTEND_BASE_URL}/payment-failed?order={order.order_number}"
#             )

#         except Exception:
#             return redirect(f"{settings.FRONTEND_BASE_URL}/payment-failed")


# class PhonePeWebhookView(APIView):
#     authentication_classes = []
#     permission_classes = []

#     def post(self, request, *args, **kwargs):
#         auth_header = request.headers.get("Authorization", "")
#         expected = hashlib.sha256(
#             f"{PHONEPE_WEBHOOK_USER}:{PHONEPE_WEBHOOK_PASS}".encode("utf-8")
#         ).hexdigest()
#         if auth_header != expected:
#             return Response(
#                 {"detail": "Unauthorized"}, status=drf_status.HTTP_401_UNAUTHORIZED
#             )

#         merchant_txn_id = request.data.get("merchantTransactionId")
#         if not merchant_txn_id:
#             return Response(
#                 {"detail": "Missing transaction id"},
#                 status=drf_status.HTTP_400_BAD_REQUEST,
#             )

#         try:
#             order = Order.objects.get(order_number=merchant_txn_id)
#         except Order.DoesNotExist:
#             return Response(
#                 {"detail": "Order not found"},
#                 status=drf_status.HTTP_404_NOT_FOUND,
#             )

#         try:
#             status_resp = phonepe_check_status(merchant_txn_id)
#             success = status_resp.get("success")
#             data = status_resp.get("data", {})
#             state = data.get("state") or data.get("paymentState")
#             provider_ref = (
#                 data.get("providerReferenceId")
#                 or data.get("transactionId")
#             )

#             if success and state == "COMPLETED":
#                 order.status = "paid"
#                 tx_status = "completed"
#             elif state in (
#                 "FAILED",
#                 "PAYMENT_ERROR",
#                 "PAYMENT_CANCELLED",
#                 "PAYMENT_DECLINED",
#             ):
#                 order.status = "failed"
#                 tx_status = "failed"
#             else:
#                 order.status = "unpaid"
#                 tx_status = "pending"

#             order.notes = f"Webhook: {status_resp}"
#             order.save(update_fields=["status", "notes"])

#             PaymentTransaction.objects.filter(
#                 merchant_transaction_id=merchant_txn_id
#             ).update(
#                 phonepe_transaction_id=provider_ref or "",
#                 raw_status_response=status_resp,
#                 status=tx_status,
#                 payment_state=state or "",
#                 message=status_resp.get("message", ""),
#             )

#             return Response({"detail": "OK"}, status=drf_status.HTTP_200_OK)

#         except Exception as e:
#             order.notes = f"Webhook error: {e}"
#             order.save(update_fields=["notes"])
#             return Response(
#                 {"detail": "Server error"},
#                 status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )
from decimal import Decimal, InvalidOperation
import hashlib
import logging
from typing import Any, Dict, List, Tuple

from django.conf import settings
from django.utils import timezone
from django.shortcuts import redirect
from rest_framework import viewsets, permissions
from .models import PaymentMethodConfig
from .serializers import PaymentMethodConfigSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status

from adminapp.models import Order, OrderItem
from .phonepe_utils import phonepe_initiate_payment, phonepe_check_status, PhonePeError, PhonePeAPIError
from .models import PaymentMethodConfig, PaymentTransaction


logger = logging.getLogger(__name__)

PHONEPE_WEBHOOK_USER = getattr(settings, "PHONEPE_WEBHOOK_USER", "")
PHONEPE_WEBHOOK_PASS = getattr(settings, "PHONEPE_WEBHOOK_PASS", "")

FRONTEND_BASE_URL = settings.FRONTEND_BASE_URL.rstrip("/")


def _safe_decimal(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal(default)


def _build_frontend_url(path: str, query: str = "") -> str:
    path = path.lstrip("/")
    if query:
        return f"{FRONTEND_BASE_URL}/{path}?{query}"
    return f"{FRONTEND_BASE_URL}/{path}"


def _normalize_phonepe_state(success: bool, state: str) -> Tuple[str, str]:
    """
    Normalize PhonePe status/state to internal order/payment transaction status.

    PhonePe docs: state is typically COMPLETED, FAILED, or PENDING for gateway flows.[web:10][web:26]
    """
    state = (state or "").upper()

    if success and state in ("COMPLETED", "SUCCESS"):
        return "paid", "completed"
    if state in ("FAILED", "PAYMENT_ERROR", "PAYMENT_CANCELLED", "PAYMENT_DECLINED", "CANCELLED"):
        return "failed", "failed"
    if state in ("PENDING", "INITIATED", ""):
        return "unpaid", "pending"

    # Fallback for unexpected states
    logger.warning("Unexpected PhonePe state: success=%s, state=%s", success, state)
    return "unpaid", "pending"


class PhonePeInitiateView(APIView):
    """
    POST /phonepe/initiate/
    Body: orderPayload from frontend (customer info, totals, promo, items[]).
    Backend recomputes payment surcharge from config and sends final total to PhonePe.[web:5]
    """

    def post(self, request, *args, **kwargs):
        data = request.data or {}
        items: List[Dict[str, Any]] = data.get("items", []) or []

        # Basic validation
        if not items:
            return Response(
                {"error": "No items in order"},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        try:
            # 1) Parse numeric fields safely
            subtotal = _safe_decimal(data.get("subtotal"))
            discount_amount = _safe_decimal(data.get("discount_amount"))
            base_total = _safe_decimal(data.get("base_total", data.get("total")))
            if base_total <= 0:
                return Response(
                    {"error": "Invalid order total"},
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )

            # 2) Payment method
            payment_method = (data.get("payment_method") or "upi").lower()

            # 3) Get surcharge percent from backend config (source of truth)
            try:
                cfg = PaymentMethodConfig.objects.get(method=payment_method)
                surcharge_percent = cfg.surcharge_percent
            except PaymentMethodConfig.DoesNotExist:
                surcharge_percent = Decimal("0")

            payment_surcharge_amount = (base_total * surcharge_percent) / Decimal("100")
            final_total = (base_total + payment_surcharge_amount).quantize(
                Decimal("0.01")
            )

            if final_total <= 0:
                return Response(
                    {"error": "Invalid final total"},
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )

            # 4) Create local Order (use more collision‑safe txn id in real systems)
            merchant_txn_id = f"TXN{int(timezone.now().timestamp())}"

            order = Order.objects.create(
                order_number=merchant_txn_id,
                customer_name=data.get("customer_name", "")[:255],
                email=data.get("email", "")[:255],
                phone=(data.get("phone") or "")[:32],
                address=data.get("address", "")[:512],
                city=data.get("city", "")[:128],
                state=data.get("state", "")[:128],
                pincode=(data.get("pincode") or "")[:16],
                subtotal=subtotal,
                discount_amount=discount_amount,
                total=final_total,
                promo_code=(data.get("promo_code") or "")[:64],
                promo_details=data.get("promo_details", ""),
                status="unpaid",
                payment_method=payment_method,
                payment_surcharge_percent=surcharge_percent,
                payment_surcharge_amount=payment_surcharge_amount,
            )

            for item in items:
                try:
                    OrderItem.objects.create(
                        order=order,
                        product_id=item["product_id"],
                        product_name=item.get("product_name", "")[:255],
                        quantity=_safe_decimal(item.get("quantity", 1)),
                        unit_price=_safe_decimal(item.get("unit_price")),
                        subtotal=_safe_decimal(item.get("subtotal")),
                        category_name=item.get("category_name", "")[:128],
                        fabric_type_name=item.get("fabric_type_name", "")[:128],
                    )
                except KeyError as exc:
                    logger.error("Invalid item payload for order %s: %s", order.id, exc)
                    order.status = "failed"
                    order.notes = "Invalid item payload"
                    order.save(update_fields=["status", "notes"])
                    return Response(
                        {"error": "Invalid item payload"},
                        status=drf_status.HTTP_400_BAD_REQUEST,
                    )

            # 5) Build PhonePe payload
            amount_paise = int(final_total * 100)
            merchant_id = settings.PHONEPE_MERCHANT_ID

            redirect_url = (
                 f"{request.build_absolute_uri('/phonepe/status/')}?txn={merchant_txn_id}"
            )

            payload = {
                "merchantId": merchant_id,
                "merchantTransactionId": merchant_txn_id,
                "merchantUserId": f"USER{order.id}",
                "amount": amount_paise,
                "redirectUrl": redirect_url,
                "redirectMode": "POST",  # PhonePe supports REDIRECT or POST[web:5]
                "callbackUrl": settings.PHONEPE_CALLBACK_URL,  # dedicated webhook/callback URL
                "mobileNumber": order.phone,
                "paymentInstrument": {"type": "PAY_PAGE"},
            }

            try:
                phonepe_resp = phonepe_initiate_payment(payload)
            except (PhonePeError, PhonePeAPIError) as exc:
                logger.exception("PhonePe initiate error for order %s", order.id)
                order.status = "failed"
                order.notes = f"PhonePe initiate exception: {exc}"
                order.save(update_fields=["status", "notes"])
                PaymentTransaction.objects.create(
                    order=order,
                    merchant_transaction_id=merchant_txn_id,
                    amount=final_total,
                    raw_initiate_response={},
                    status="failed",
                    message=str(exc),
                )
                return Response(
                    {"error": "Failed to initiate payment"},
                    status=drf_status.HTTP_502_BAD_GATEWAY,
                )

            # 6) Create initial PaymentTransaction record
            PaymentTransaction.objects.create(
                order=order,
                merchant_transaction_id=merchant_txn_id,
                amount=final_total,
                raw_initiate_response=phonepe_resp,
                status="initiated" if phonepe_resp.get("success") else "failed",
                message=phonepe_resp.get("message", ""),
            )

            # 7) Handle PhonePe initiate failure
            if not phonepe_resp.get("success"):
                logger.warning("PhonePe initiate failed for order %s: %s", order.id, phonepe_resp)
                order.status = "failed"
                order.notes = f"PhonePe initiate failed: {phonepe_resp}"
                order.save(update_fields=["status", "notes"])
                return Response(
                    {"error": "Failed to initiate payment", "details": phonepe_resp},
                    status=drf_status.HTTP_502_BAD_GATEWAY,
                )

            redirect_info = (
                phonepe_resp.get("data", {})
                .get("instrumentResponse", {})
                .get("redirectInfo", {})
            )
            pay_page_url = redirect_info.get("url")

            if not pay_page_url:
                logger.error("No redirect URL from PhonePe for order %s: %s", order.id, phonepe_resp)
                order.status = "failed"
                order.notes = f"No redirect URL from PhonePe: {phonepe_resp}"
                order.save(update_fields=["status", "notes"])
                PaymentTransaction.objects.filter(
                    merchant_transaction_id=merchant_txn_id
                ).update(
                    status="failed",
                    message="No redirect URL from PhonePe",
                )
                return Response(
                    {"error": "Payment gateway error"},
                    status=drf_status.HTTP_502_BAD_GATEWAY,
                )

            # 8) Return URL for redirecting user to PhonePe pay page
            return Response(
                {
                    "order_number": order.order_number,
                    "redirect_url": pay_page_url,
                },
                status=drf_status.HTTP_200_OK,
            )

        except Exception as exc:
            logger.exception("Unexpected error initiating PhonePe payment")
            return Response(
                {"error": "Server error initiating payment"},
                status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PhonePeStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return self._handle(request)

    def post(self, request, *args, **kwargs):
        return self._handle(request)

    def _handle(self, request):
        merchant_txn_id = request.query_params.get("txn") or request.data.get("txn")
        if not merchant_txn_id:
            return redirect(_build_frontend_url("payment-failed"))

        try:
            order = Order.objects.get(order_number=merchant_txn_id)
        except Order.DoesNotExist:
            logger.warning("Status check for non-existent order: %s", merchant_txn_id)
            return redirect(_build_frontend_url("payment-failed"))

        try:
            status_resp = phonepe_check_status(merchant_txn_id)
            success = bool(status_resp.get("success"))
            data = status_resp.get("data", {}) or {}
            pay_state = data.get("state") or data.get("paymentState")
            provider_ref = (
                data.get("providerReferenceId")
                or data.get("transactionId")
            )

            order_status, tx_status = _normalize_phonepe_state(success, pay_state)

            order.status = order_status
            order.notes = f"PhonePe status: {status_resp}"
            order.save(update_fields=["status", "notes"])

            PaymentTransaction.objects.filter(
                merchant_transaction_id=merchant_txn_id
            ).update(
                phonepe_transaction_id=provider_ref or "",
                raw_status_response=status_resp,
                status=tx_status,
                payment_state=pay_state or "",
                message=status_resp.get("message", ""),
            )

            if order.status == "paid":
                return redirect(
                    _build_frontend_url("payment-success", f"order={order.order_number}")
                )
            return redirect(
                _build_frontend_url("payment-failed", f"order={order.order_number}")
            )

        except (PhonePeError, PhonePeAPIError) as exc:
            logger.exception("PhonePe status error for order %s", order.id)
            return redirect(_build_frontend_url("payment-failed"))
        except Exception:
            logger.exception("Unexpected error in PhonePeStatusView")
            return redirect(_build_frontend_url("payment-failed"))


class PhonePeWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        # Simple shared-secret auth; consider using PhonePe signature validation if available.[web:31]
        auth_header = request.headers.get("Authorization", "")
        expected = hashlib.sha256(
            f"{PHONEPE_WEBHOOK_USER}:{PHONEPE_WEBHOOK_PASS}".encode("utf-8")
        ).hexdigest()
        if not PHONEPE_WEBHOOK_USER or not PHONEPE_WEBHOOK_PASS:
            logger.error("PHONEPE_WEBHOOK_USER/PASS not configured")
            return Response(
                {"detail": "Webhook not configured"},
                status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        if auth_header != expected:
            logger.warning("Invalid PhonePe webhook auth header")
            return Response(
                {"detail": "Unauthorized"}, status=drf_status.HTTP_401_UNAUTHORIZED
            )

        merchant_txn_id = request.data.get("merchantTransactionId")
        if not merchant_txn_id:
            return Response(
                {"detail": "Missing transaction id"},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = Order.objects.get(order_number=merchant_txn_id)
        except Order.DoesNotExist:
            logger.warning("Webhook for non-existent order: %s", merchant_txn_id)
            return Response(
                {"detail": "Order not found"},
                status=drf_status.HTTP_404_NOT_FOUND,
            )

        try:
            status_resp = phonepe_check_status(merchant_txn_id)
            success = bool(status_resp.get("success"))
            data = status_resp.get("data", {}) or {}
            state = data.get("state") or data.get("paymentState")
            provider_ref = (
                data.get("providerReferenceId")
                or data.get("transactionId")
            )

            order_status, tx_status = _normalize_phonepe_state(success, state)

            order.status = order_status
            order.notes = f"Webhook: {status_resp}"
            order.save(update_fields=["status", "notes"])

            PaymentTransaction.objects.filter(
                merchant_transaction_id=merchant_txn_id
            ).update(
                phonepe_transaction_id=provider_ref or "",
                raw_status_response=status_resp,
                status=tx_status,
                payment_state=state or "",
                message=status_resp.get("message", ""),
            )

            return Response({"detail": "OK"}, status=drf_status.HTTP_200_OK)

        except (PhonePeError, PhonePeAPIError) as exc:
            logger.exception("PhonePe webhook status error for order %s", order.id)
            order.notes = f"Webhook PhonePe error: {exc}"
            order.save(update_fields=["notes"])
            return Response(
                {"detail": "Upstream payment gateway error"},
                status=drf_status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            logger.exception("Unexpected error in PhonePeWebhookView for order %s", order.id)
            order.notes = f"Webhook error: {exc}"
            order.save(update_fields=["notes"])
            return Response(
                {"detail": "Server error"},
                status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class PaymentMethodConfigViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/payment-method-config/
    """
    queryset = PaymentMethodConfig.objects.all().order_by("method")
    serializer_class = PaymentMethodConfigSerializer
    permission_classes = [permissions.AllowAny]  # or tighten as needed