from __future__ import annotations
import json
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID, GOOGLE_SA_JSON, GOOGLE_SA_PATH
from functools import lru_cache

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


@lru_cache(maxsize=1)
def get_client() -> gspread.Client:
    if GOOGLE_SA_JSON:
        info = json.loads(GOOGLE_SA_JSON)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(GOOGLE_SA_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


def get_sheet(name: str) -> gspread.Worksheet:
    return get_client().open_by_key(GOOGLE_SHEET_ID).worksheet(name)


def get_all(sheet_name: str) -> list[dict]:
    return get_sheet(sheet_name).get_all_records()


def update_cell(sheet_name: str, row_idx: int, col: int, value: str) -> None:
    get_sheet(sheet_name).update_cell(row_idx, col, value)


def append_row(sheet_name: str, row: list) -> None:
    get_sheet(sheet_name).append_row(row, value_input_option="USER_ENTERED")


def find_row_idx(sheet_name: str, col: int, value: str) -> int | None:
    col_values = get_sheet(sheet_name).col_values(col)
    matches = [idx + 1 for idx, v in enumerate(col_values) if v == value]
    if len(matches) != 1:
        return None
    return matches[0]


def update_order_status_if(order_id: str, expected_status: str, new_status: str) -> bool:
    ws = get_sheet("orders")
    headers = [h.lower().strip() for h in ws.row_values(1)]
    try:
        status_col = headers.index("status") + 1
    except ValueError:
        return False

    records = ws.get_all_records()
    for idx, record in enumerate(records, start=2):
        if str(record.get("id", "")) != order_id:
            continue
        current = str(record.get("status", "new"))
        if current != expected_status:
            return False
        ws.update_cell(idx, status_col, new_status)
        return True
    return False
