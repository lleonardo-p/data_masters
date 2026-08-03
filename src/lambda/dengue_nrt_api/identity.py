import re
from typing import Any


class InvalidCpfError(ValueError):
    """Raised when a CPF does not have a valid format and checksum."""


def normalize_cpf(value: str) -> str:
    normalized = re.sub(r"\D", "", value)

    if len(normalized) != 11 or len(set(normalized)) == 1:
        raise InvalidCpfError("CPF must contain 11 valid digits.")

    digits = [int(character) for character in normalized]
    first_sum = sum(
        digit * weight
        for digit, weight in zip(digits[:9], range(10, 1, -1))
    )
    first_remainder = first_sum % 11
    first_digit = 0 if first_remainder < 2 else 11 - first_remainder

    second_sum = sum(
        digit * weight
        for digit, weight in zip(digits[:10], range(11, 1, -1))
    )
    second_remainder = second_sum % 11
    second_digit = 0 if second_remainder < 2 else 11 - second_remainder

    if digits[-2:] != [first_digit, second_digit]:
        raise InvalidCpfError("CPF checksum is invalid.")

    return normalized


def generate_cpf_fingerprint(
    kms_client: Any,
    key_arn: str,
    normalized_cpf: str,
) -> str:
    response = kms_client.generate_mac(
        KeyId=key_arn,
        MacAlgorithm="HMAC_SHA_256",
        Message=normalized_cpf.encode("utf-8"),
    )
    return bytes(response["Mac"]).hex()
