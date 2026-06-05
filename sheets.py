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
    """Returns 1-based row index or None."""
    col_values = get_sheet(sheet_name).col_values(col)
    try:
        return col_values.index(value) + 1
    except ValueError:
        return None
