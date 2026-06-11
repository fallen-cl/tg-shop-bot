from __future__ import annotations
from gspread import Cell
import sheets


def _product_columns(all_rows: list[list[str]]) -> tuple[int, int, int | None] | None:
    if not all_rows:
        return None
    headers = [h.lower().strip() for h in all_rows[0]]
    try:
        id_col = headers.index("id")
        stock_col = headers.index("stock")
    except ValueError:
        return None
    in_stock_col = headers.index("in_stock") if "in_stock" in headers else None
    return id_col, stock_col, in_stock_col


def apply_stock_deltas(deltas: dict[str, int]) -> tuple[bool, str]:
    if not deltas:
        return True, ""

    ws = sheets.get_sheet("products")
    all_rows = ws.get_all_values()
    cols = _product_columns(all_rows)
    if cols is None:
        return False, "Products sheet misconfigured"

    id_col, stock_col, in_stock_col = cols
    row_by_id: dict[str, tuple[int, list[str]]] = {}
    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) > id_col and row[id_col]:
            row_by_id[row[id_col]] = (i, row)

    for product_id, delta in deltas.items():
        if product_id not in row_by_id:
            return False, f"Product not found: {product_id}"
        _, row = row_by_id[product_id]
        try:
            current = int(row[stock_col]) if len(row) > stock_col else 0
        except Exception:
            current = 0
        if current + delta < 0:
            return False, f"Insufficient stock for {product_id}"

    cells: list[Cell] = []
    for product_id, delta in deltas.items():
        row_idx, row = row_by_id[product_id]
        try:
            current = int(row[stock_col]) if len(row) > stock_col else 0
        except Exception:
            current = 0
        new_stock = current + delta
        cells.append(Cell(row_idx, stock_col + 1, new_stock))
        if in_stock_col is not None:
            cells.append(Cell(row_idx, in_stock_col + 1, "TRUE" if new_stock > 0 else "FALSE"))

    ws.update_cells(cells, value_input_option="USER_ENTERED")
    return True, ""


def order_items_from_json(items_json: str) -> list[tuple[str, int]]:
    import json
    try:
        raw = json.loads(items_json or "[]")
    except Exception:
        return []
    items: list[tuple[str, int]] = []
    for item in raw:
        pid = str(item.get("product_id", ""))
        if not pid:
            continue
        try:
            qty = int(item.get("quantity", 1))
        except Exception:
            qty = 1
        if qty > 0:
            items.append((pid, qty))
    return items


def decrease_stock_for_order(items_json: str) -> tuple[bool, str]:
    deltas: dict[str, int] = {}
    for product_id, quantity in order_items_from_json(items_json):
        deltas[product_id] = deltas.get(product_id, 0) - quantity
    return apply_stock_deltas(deltas)


def increase_stock_for_order(items_json: str) -> tuple[bool, str]:
    deltas: dict[str, int] = {}
    for product_id, quantity in order_items_from_json(items_json):
        deltas[product_id] = deltas.get(product_id, 0) + quantity
    return apply_stock_deltas(deltas)
