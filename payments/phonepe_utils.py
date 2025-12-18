# import base64
# import hashlib
# import json
# import requests
# from django.conf import settings

# def phonepe_generate_checksum(payload_base64: str, path: str) -> str:
#   """
#   X-VERIFY = SHA256(base64Payload + path + saltKey) + '###' + saltIndex
#   path example: '/pg/v1/pay' or f'/pg/v1/status/{merchantId}/{txnId}'
#   """
#   salt_key = settings.PHONEPE_SALT_KEY
#   salt_index = settings.PHONEPE_SALT_INDEX
#   data = payload_base64 + path + salt_key
#   sha256 = hashlib.sha256(data.encode("utf-8")).hexdigest()
#   return f"{sha256}###{salt_index}"

# def phonepe_initiate_payment(payload: dict) -> dict:
#   """
#   Initiate payment via PhonePe PAY API.
#   """
#   payload_str = json.dumps(payload, separators=(",", ":"))
#   payload_base64 = base64.b64encode(payload_str.encode("utf-8")).decode("utf-8")

#   path = "/pg/v1/pay"
#   checksum = phonepe_generate_checksum(payload_base64, path)

#   url = settings.PHONEPE_BASE_URL + path
#   headers = {
#     "Content-Type": "application/json",
#     "X-VERIFY": checksum,
#     "X-MERCHANT-ID": settings.PHONEPE_MERCHANT_ID,
#   }
#   resp = requests.post(url, json={"request": payload_base64}, headers=headers, timeout=15)
#   resp.raise_for_status()
#   return resp.json()

# def phonepe_check_status(merchant_txn_id: str) -> dict:
#   merchant_id = settings.PHONEPE_MERCHANT_ID
#   path = f"/pg/v1/status/{merchant_id}/{merchant_txn_id}"
#   checksum = phonepe_generate_checksum("", path)  # status signature as per docs

#   url = settings.PHONEPE_BASE_URL + path
#   headers = {
#     "Content-Type": "application/json",
#     "X-VERIFY": checksum,
#     "X-MERCHANT-ID": merchant_id,
#   }
#   resp = requests.get(url, headers=headers, timeout=15)
#   resp.raise_for_status()
#   return resp.json()

# phonepe_utils.py

import base64
import hashlib
import json
import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from requests import Response
from requests.exceptions import RequestException, Timeout


logger = logging.getLogger(__name__)


class PhonePeError(Exception):
    """Base exception for PhonePe related errors."""


class PhonePeAPIError(PhonePeError):
    """Raised when PhonePe returns a non-success response."""

    def __init__(self, message: str, response: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.response = response or {}


def _phonepe_generate_checksum(payload_base64: str, path: str) -> str:
    """
    X-VERIFY = SHA256(base64Payload + path + saltKey) + '###' + saltIndex
    path example: '/pg/v1/pay' or f'/pg/v1/status/{merchantId}/{txnId}'
    """
    salt_key = settings.PHONEPE_SALT_KEY
    salt_index = settings.PHONEPE_SALT_INDEX
    data = f"{payload_base64}{path}{salt_key}"
    sha256 = hashlib.sha256(data.encode("utf-8")).hexdigest()
    return f"{sha256}###{salt_index}"


def _request_with_handling(
    method: str,
    url: str,
    *,
    headers: Dict[str, str],
    json_body: Optional[Dict[str, Any]] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    try:
        resp: Response
        if method.upper() == "POST":
            resp = requests.post(url, json=json_body, headers=headers, timeout=timeout)
        elif method.upper() == "GET":
            resp = requests.get(url, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    except Timeout as exc:
        logger.error("PhonePe request timeout: %s %s", method, url, exc_info=True)
        raise PhonePeError("PhonePe request timed out") from exc
    except RequestException as exc:
        logger.error("PhonePe request error: %s %s", method, url, exc_info=True)
        raise PhonePeError("PhonePe network error") from exc

    # Log non-2xx for debugging (without sensitive data)
    if not resp.ok:
        logger.warning(
            "PhonePe non-2xx response: %s %s status=%s body=%s",
            method,
            url,
            resp.status_code,
            resp.text,
        )

    try:
        data = resp.json()
    except ValueError as exc:
        logger.error("Invalid JSON from PhonePe: %s %s body=%s", method, url, resp.text)
        raise PhonePeError("Invalid response from PhonePe") from exc

    return data


def phonepe_initiate_payment(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initiate payment via PhonePe PAY API.

    payload must already contain required fields as per Pay API:
    - merchantId
    - merchantTransactionId
    - amount
    - redirectUrl / redirectMode / callbackUrl, etc.[web:6]
    """
    # Deterministic JSON for checksum
    payload_str = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    payload_base64 = base64.b64encode(payload_str.encode("utf-8")).decode("utf-8")

    path = "/pg/v1/pay"
    checksum = _phonepe_generate_checksum(payload_base64, path)

    url = settings.PHONEPE_BASE_URL.rstrip("/") + path
    headers = {
        "Content-Type": "application/json",
        "X-VERIFY": checksum,
        "X-MERCHANT-ID": settings.PHONEPE_MERCHANT_ID,
    }

    body = {"request": payload_base64}
    response_data = _request_with_handling("POST", url, headers=headers, json_body=body)

    # Optional: enforce success flag from PhonePe
    if not response_data.get("success", False):
        logger.warning("PhonePe initiate payment failed: %s", response_data)
        raise PhonePeAPIError(
            f"PhonePe initiate payment failed: {response_data.get('code')}",
            response=response_data,
        )

    return response_data


def phonepe_check_status(merchant_txn_id: str) -> Dict[str, Any]:
    """
    Check payment status via PhonePe Check Status API.

    merchant_txn_id: merchantTransactionId used in pay call.[web:10]
    """
    merchant_id = settings.PHONEPE_MERCHANT_ID
    path = f"/pg/v1/status/{merchant_id}/{merchant_txn_id}"

    # For status API, checksum is computed with empty payload + path + saltKey.[web:10]
    checksum = _phonepe_generate_checksum("", path)

    url = settings.PHONEPE_BASE_URL.rstrip("/") + path
    headers = {
        "Content-Type": "application/json",
        "X-VERIFY": checksum,
        "X-MERCHANT-ID": merchant_id,
    }

    response_data = _request_with_handling("GET", url, headers=headers)

    if not response_data.get("success", False):
        logger.warning("PhonePe status check failed: %s", response_data)
        raise PhonePeAPIError(
            f"PhonePe status check failed: {response_data.get('code')}",
            response=response_data,
        )

    return response_data
