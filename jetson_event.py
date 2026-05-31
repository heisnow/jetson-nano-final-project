from __future__ import annotations

import argparse
from datetime import datetime, timezone

from database import SessionLocal, init_db
from models import JetsonEvent


def main() -> None:
    parser = argparse.ArgumentParser(description="Insert a Jetson helmet detection event.")
    parser.add_argument("--location", default="實驗場域")
    parser.add_argument("--status", default="未戴安全帽", choices=["未戴安全帽", "已戴安全帽", "無法判定"])
    parser.add_argument("--confidence", type=float, default=0.9)
    parser.add_argument(
        "--note",
        default="硬體型號未定時，可先用此腳本模擬 Jetson 寫入 PostgreSQL 的事件。",
    )
    args = parser.parse_args()

    init_db(seed=False)
    with SessionLocal() as session:
        session.add(
            JetsonEvent(
                location=args.location,
                helmet_status=args.status,
                confidence=args.confidence,
                device_note=args.note,
                captured_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
    print("Jetson event inserted.")


if __name__ == "__main__":
    main()
