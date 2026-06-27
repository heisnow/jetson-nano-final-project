from __future__ import annotations

import argparse

from app import analyze_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a sample recycling scan record.")
    parser.add_argument("--text", default="PET 寶特瓶")
    parser.add_argument("--device", default="manual demo")
    args = parser.parse_args()

    result = analyze_text(args.text)
    print(f"Input: {args.text}")
    print(f"Item: {result['item_name']}")
    print(f"Category: {result['category']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Steps: {result['disposal_steps']}")


if __name__ == "__main__":
    main()
