from __future__ import annotations

import argparse
import time

from listingturbo.core.mobile_sync import MOBILE_SYNC_PORT, MobileSyncServer


def main() -> int:
    parser = argparse.ArgumentParser(description="ListingTurbo lokalen Mobile-Sync-Server starten.")
    parser.add_argument("--port", type=int, default=MOBILE_SYNC_PORT)
    parser.add_argument("--pin", help="sechsstellige Transfer-PIN, optional")
    args = parser.parse_args()
    server = MobileSyncServer(port=args.port, token=args.pin)
    server.start()
    print(f"ListingTurbo Mobile Sync läuft: {server.display_url}")
    print(f"PIN: {server.token}")
    print("Beenden mit STRG+C.")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        server.stop()
        print("Mobile Sync gestoppt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
