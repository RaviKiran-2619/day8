import os
import re
import json
import requests
from dotenv import load_dotenv


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

SHEETDB_API_URL = (
    "https://sheetdb.io/api/v1/2ccjxrxhx4umd?sheet=Day8"
)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_NAME = "openai/gpt-4o-mini"


# ============================================================
# 2. BATCH INPUT
# ============================================================

profile_texts = [
    """
    Name: Manoj
    Email: manoj@example.com
    Role: Lead Systems Engineer
    """,

    """
    Name: avinash
    Email: avinash@tech.io
    Role: Backend Architect
    """,

    """
    Name: Ravi Kumar
    Email: ravi.kumar@gmail.com
    Role: Python Developer
    """,

    """
    Name: Priya Sharma
    Email: priya.sharma@company.com
    Role: Data Engineer
    """,

    """
    Name: Invalid User
    Email: invalid-email
    Role: Tester
    """,

    """
    Name:
    Email: noname@gmail.com
    Role: Developer
    """
    
]


# ============================================================
# 3. LLM EXTRACTION
# ============================================================

def extract_profile(profile_text):

    prompt = f"""
You are a structured data extraction system.

Extract these fields from the profile:

1. name
2. email
3. role

Return ONLY valid JSON.

Required format:

{{
    "name": "string",
    "email": "string",
    "role": "string"
}}

Do not add:
- Markdown
- Explanation
- Extra fields

Profile:
{profile_text}
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0
    }

    try:

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        result = response.json()

        content = result["choices"][0]["message"]["content"]

        content = content.strip()

        # Remove markdown JSON fences if returned by LLM
        content = re.sub(
            r"^```json\s*|\s*```$",
            "",
            content,
            flags=re.IGNORECASE
        ).strip()

        extracted_data = json.loads(content)

        return extracted_data

    except Exception as error:

        print("LLM Extraction Error:", error)

        return None


# ============================================================
# 4. EMAIL VALIDATION
# ============================================================

def validate_email(email):

    if not isinstance(email, str):
        return False

    email = email.strip()

    pattern = (
        r"^[A-Za-z0-9._%+-]+"
        r"@[A-Za-z0-9.-]+"
        r"\.[A-Za-z]{2,}$"
    )

    return re.fullmatch(pattern, email) is not None


# ============================================================
# 5. RECORD VALIDATION
# ============================================================

def validate_record(record):

    if not isinstance(record, dict):

        return False, "Invalid record structure"

    name = record.get("name")
    email = record.get("email")
    role = record.get("role")

    # --------------------------------------------------------
    # Name validation
    # --------------------------------------------------------

    if not isinstance(name, str) or not name.strip():

        return False, "Name is missing"

    # --------------------------------------------------------
    # Email validation
    # --------------------------------------------------------

    if not validate_email(email):

        return False, "Invalid email format"

    # --------------------------------------------------------
    # Role validation
    # --------------------------------------------------------

    if not isinstance(role, str) or not role.strip():

        return False, "Role is missing"

    return True, "Valid"


# ============================================================
# 6. BUILD BATCH PAYLOAD
# ============================================================

def build_batch(profile_texts):

    valid_records = []
    invalid_records = []

    print("\n")
    print("=" * 60)
    print("DAY 8 - BATCH PROCESSING")
    print("=" * 60)

    for index, profile in enumerate(profile_texts, start=1):

        print(f"\nProcessing Record {index}")
        print("-" * 40)

        # ----------------------------------------------------
        # LLM Extraction
        # ----------------------------------------------------

        extracted_record = extract_profile(profile)

        if extracted_record is None:

            print("LLM Extraction : FAILED")

            invalid_records.append({
                "record_number": index,
                "reason": "LLM extraction failed"
            })

            continue

        print(
            "Extracted:",
            json.dumps(
                extracted_record,
                indent=2
            )
        )

        # ----------------------------------------------------
        # Defensive Validation
        # ----------------------------------------------------

        is_valid, reason = validate_record(
            extracted_record
        )

        if is_valid:

            print("Validation      : PASS")

            valid_records.append({
                "name": extracted_record["name"].strip(),
                "email": extracted_record["email"].strip(),
                "role": extracted_record["role"].strip()
            })

        else:

            print("Validation      : FAIL")
            print("Reason          :", reason)

            invalid_records.append({
                "record_number": index,
                "record": extracted_record,
                "reason": reason
            })

    return valid_records, invalid_records


# ============================================================
# 7. SHEETDB BATCH INSERT
# ============================================================

def insert_batch_to_sheetdb(valid_records):

    if not valid_records:

        print("\nNo valid records to insert.")

        return False

    # --------------------------------------------------------
    # Single bulk payload
    # --------------------------------------------------------

    payload = {
        "data": valid_records
    }

    headers = {
        "Content-Type": "application/json"
    }

    print("\n")
    print("=" * 60)
    print("SENDING BATCH TO SHEETDB")
    print("=" * 60)

    print("\nBatch Payload:")

    print(
        json.dumps(
            payload,
            indent=2
        )
    )

    try:

        # ONE HTTP REQUEST ONLY
        response = requests.post(
            SHEETDB_API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        print("\nSheetDB Status Code:", response.status_code)

        if response.ok:

            print("\nSUCCESS!")
            print("Valid records inserted into Day8 sheet.")

            print("\nSheetDB Response:")
            print(response.text)

            return True

        else:

            print("\nSheetDB insertion failed.")

            print("Response:")
            print(response.text)

            return False

    except requests.RequestException as error:

        print("\nSheetDB Connection Error:")
        print(error)

        return False


# ============================================================
# 8. MAIN PIPELINE
# ============================================================

def main():

    # --------------------------------------------------------
    # Check OpenRouter API key
    # --------------------------------------------------------

    if not OPENROUTER_API_KEY:

        print(
            "ERROR: OPENROUTER_API_KEY "
            "not found in .env"
        )

        return

    # --------------------------------------------------------
    # Step 1: Extract + Validate
    # --------------------------------------------------------

    valid_records, invalid_records = build_batch(
        profile_texts
    )

    # --------------------------------------------------------
    # Step 2: Summary
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)

    print(
        "Total Records   :",
        len(profile_texts)
    )

    print(
        "Valid Records   :",
        len(valid_records)
    )

    print(
        "Invalid Records :",
        len(invalid_records)
    )

    # --------------------------------------------------------
    # Step 3: Valid records
    # --------------------------------------------------------

    print("\nVALID RECORDS")

    print(
        json.dumps(
            valid_records,
            indent=2
        )
    )

    # --------------------------------------------------------
    # Step 4: Invalid records
    # --------------------------------------------------------

    if invalid_records:

        print("\nINVALID RECORDS")

        print(
            json.dumps(
                invalid_records,
                indent=2
            )
        )

    # --------------------------------------------------------
    # Step 5: ONE bulk SheetDB request
    # --------------------------------------------------------

    if valid_records:

        insert_batch_to_sheetdb(
            valid_records
        )

    else:

        print(
            "\nNo valid records found. "
            "SheetDB request skipped."
        )


# ============================================================
# 9. APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()