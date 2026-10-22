
import os
import json
import base64
from decimal import Decimal, InvalidOperation
from datetime import datetime

from groq import Groq


client = Groq(api_key=os.environ["GROQ_API_KEY"])

MODEL_NAME = "qwen/qwen3.8-27b"


def read_receipt_with_groq(
    image_bytes: bytes,
    content_type: str,
) -> dict:
    """Extract receipt fields and line items from an image."""

    if content_type not in {"image/jpeg", "image/png"}:
        raise ValueError("This function currently accepts JPEG and PNG images.")

    encoded_image = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
    Read this receipt and return a JSON object with:
    merchant, purchase_date, currency, total, line_items.

    Each line item must contain:
    description, quantity, total_price.

    Rules:
    - Use null when a field cannot be read.
    - Do not invent missing values.
    - Return purchase_date in YYYY-MM-DD format.
    - Currency must be the currency explicitly supported by the receipt.
      If it is unclear, return null.
    - total_price is the total price for that line, not unit price.
    - Do not include subtotal, tax, or change as purchased items.
    - Include only items supported by the receipt image.
    - Return valid JSON only.
    """

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                f"data:{content_type};base64,"
                                f"{encoded_image}"
                            )
                        },
                    },
                ],
            }
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_completion_tokens=2048,
    )
    print(
    "RAW GROQ CONTENT:",
    repr(response.choices[0].message.content),
    flush=True,
)
    content = response.choices[0].message.content
    if not isinstance(content, str):
        raise ValueError("Groq returned no receipt content.")

    result = json.loads(content)
    print("PARSED GROQ DATA:", repr(result), flush=True)
    # Basic validation before the result reaches the database.
    if not isinstance(result, dict):
        raise ValueError("Groq returned an invalid receipt object.")

    if not isinstance(result.get("line_items"), list):
        raise ValueError("Groq returned invalid line items.")

    for item in result["line_items"]:
        if not isinstance(item, dict):
            raise ValueError("Invalid line item.")

        description = item.get("description")
        quantity = item.get("quantity")
        price = item.get("total_price")

        if not isinstance(description, str) or not description.strip():
            raise ValueError("A line item has no valid description.")

        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, (int, float))
            or quantity <= 0
        ):
            raise ValueError("A line item has an invalid quantity.")

        if isinstance(price, bool) or price is None:
            raise ValueError("A line item has no valid total price.")

        try:
            amount = Decimal(str(price))
        except InvalidOperation as exc:
            raise ValueError("Invalid line-item price.") from exc

        if not amount.is_finite() or amount < 0:
            raise ValueError("Invalid line-item price.")

    return result
