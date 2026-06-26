from __future__ import annotations

from listingturbo.core.license import (
    PUBLIC_VERIFY_SECRET,
    create_license_key,
    decode_license_key_for_admin,
    machine_fingerprint,
    validate_license_payload,
)


def test_license_key_is_encoded_and_machine_bound() -> None:
    machine_id = machine_fingerprint()
    key = create_license_key(
        "kunde@example.com",
        "STANDARD",
        secret=PUBLIC_VERIFY_SECRET,
        machine_id=machine_id,
        activation_id="ORDER-1001",
    )
    assert key.startswith("LT2-")
    assert len(key) > 80
    payload = decode_license_key_for_admin(key)
    assert payload is not None
    assert payload["machine_id"] == machine_id
    assert validate_license_payload(payload, current_machine=machine_id) is None


def test_license_rejects_wrong_machine() -> None:
    key = create_license_key(
        "kunde@example.com",
        "PRO",
        secret=PUBLIC_VERIFY_SECRET,
        machine_id="0123456789abcdef01234567",
        activation_id="ORDER-1002",
    )
    payload = decode_license_key_for_admin(key)
    assert payload is not None
    message = validate_license_payload(payload, current_machine="fedcba9876543210fedcba98")
    assert message is not None
    assert "andere Maschine" in message


def test_machine_fingerprint_is_stable_shape() -> None:
    fingerprint = machine_fingerprint()
    assert len(fingerprint) == 24
    assert all(char in "0123456789abcdef" for char in fingerprint)


def test_license_decode_tolerates_wrapped_key() -> None:
    machine_id = machine_fingerprint()
    key = create_license_key(
        "kunde@example.com",
        "STANDARD",
        secret=PUBLIC_VERIFY_SECRET,
        machine_id=machine_id,
    )
    wrapped = "lt2-" + key[4:30] + "\n" + key[30:]
    payload = decode_license_key_for_admin(wrapped)

    assert payload is not None
    assert payload["machine_id"] == machine_id
