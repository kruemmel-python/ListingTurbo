from __future__ import annotations

import argparse
import os

from listingturbo.core.license import PUBLIC_VERIFY_SECRET, create_license_key, machine_fingerprint


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline-Lizenzschlüssel für ListingTurbo erzeugen.")
    parser.add_argument("owner", help="Name oder E-Mail des Käufers")
    parser.add_argument("plan", choices=["STANDARD", "PRO"], help="Lizenzplan")
    parser.add_argument("--machine-id", default=machine_fingerprint(), help="Machine-ID des Zielrechners")
    parser.add_argument("--activation-id", help="Bestell-/Aktivierungs-ID, optional")
    parser.add_argument("--expires", help="Ablaufdatum im Format YYYY-MM-DD, optional")
    parser.add_argument(
        "--secret-env",
        default="LISTINGTURBO_LICENSE_SECRET",
        help="Environment-Variable für Shop-Signatursecret",
    )
    args = parser.parse_args()
    secret = os.getenv(args.secret_env, PUBLIC_VERIFY_SECRET)
    print(
        create_license_key(
            args.owner,
            args.plan,
            secret=secret,
            machine_id=args.machine_id,
            activation_id=args.activation_id,
            expires=args.expires,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
