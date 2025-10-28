#!/usr/bin/env python3
import argparse
import csv
import json
import os
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DATA_DIR_NAME = ".expense_tracker"
DATA_FILE_NAME = "data.json"


def get_data_file_path() -> Path:
    home = Path.home()
    data_dir = home / DATA_DIR_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / DATA_FILE_NAME


def load_data() -> Dict[str, Any]:
    path = get_data_file_path()
    if not path.exists():
        return {"next_id": 1, "expenses": [], "budgets": {}}
    with path.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            # Corrupt file fallback: backup and reset
            backup = path.with_suffix(".bak")
            try:
                path.replace(backup)
            except Exception:
                pass
            return {"next_id": 1, "expenses": [], "budgets": {}}
    # Ensure required keys
    data.setdefault("next_id", 1)
    data.setdefault("expenses", [])
    data.setdefault("budgets", {})
    return data


def save_data(data: Dict[str, Any]) -> None:
    path = get_data_file_path()
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp_path.replace(path)


def parse_date(value: Optional[str]) -> str:
    if not value:
        return date.today().isoformat()
    try:
        # Accept YYYY-MM-DD
        d = datetime.strptime(value, "%Y-%m-%d").date()
        return d.isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid date format. Use YYYY-MM-DD.")


def month_to_ym(month: int, year: Optional[int] = None) -> Tuple[int, int]:
    if month < 1 or month > 12:
        raise argparse.ArgumentTypeError("Month must be between 1 and 12.")
    y = year if year is not None else date.today().year
    return (y, month)


def ym_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def month_name(month: int) -> str:
    return datetime(2000, month, 1).strftime("%B")


@dataclass
class Expense:
    id: int
    date: str  # YYYY-MM-DD
    description: str
    amount: float
    category: Optional[str] = None


def validate_amount(amount: float) -> float:
    if amount <= 0:
        raise argparse.ArgumentTypeError("Amount must be positive.")
    return round(float(amount), 2)


def add_expense(args: argparse.Namespace) -> None:
    data = load_data()
    expense_id = data["next_id"]
    expense = Expense(
        id=expense_id,
        date=parse_date(args.date),
        description=args.description.strip(),
        amount=validate_amount(args.amount),
        category=(args.category.strip() if args.category else None),
    )
    data["expenses"].append(asdict(expense))
    data["next_id"] = expense_id + 1
    save_data(data)
    print(f"Expense added successfully (ID: {expense.id})")


def update_expense(args: argparse.Namespace) -> None:
    data = load_data()
    try:
        exp = next(e for e in data["expenses"] if e["id"] == args.id)
    except StopIteration:
        print("Error: Expense ID not found.")
        return
    if args.description is not None:
        exp["description"] = args.description.strip()
    if args.amount is not None:
        exp["amount"] = validate_amount(args.amount)
    if args.date is not None:
        exp["date"] = parse_date(args.date)
    if args.category is not None:
        exp["category"] = args.category.strip() if args.category else None
    save_data(data)
    print("Expense updated successfully")


def delete_expense(args: argparse.Namespace) -> None:
    data = load_data()
    before = len(data["expenses"])
    data["expenses"] = [e for e in data["expenses"] if e["id"] != args.id]
    after = len(data["expenses"])
    if before == after:
        print("Error: Expense ID not found.")
        return
    save_data(data)
    print("Expense deleted successfully")


def filter_expenses(expenses: List[Dict[str, Any]], category: Optional[str], month: Optional[int]) -> List[Dict[str, Any]]:
    filtered = expenses
    if category:
        filtered = [e for e in filtered if (e.get("category") or "").lower() == category.lower()]
    if month is not None:
        year = date.today().year
        y, m = month_to_ym(month, year)
        prefix = f"{y:04d}-{m:02d}-"
        filtered = [e for e in filtered if str(e.get("date", "")).startswith(prefix)]
    return sorted(filtered, key=lambda e: (e.get("date", ""), e["id"]))


def list_expenses(args: argparse.Namespace) -> None:
    data = load_data()
    expenses = filter_expenses(data["expenses"], args.category, args.month)
    if not expenses:
        print("No expenses found.")
        return
    headers = ["ID", "Date", "Description", "Amount", "Category"]
    rows: List[List[str]] = []
    for e in expenses:
        rows.append([
            str(e["id"]),
            e.get("date", ""),
            e.get("description", ""),
            f"${e.get('amount', 0):.2f}",
            e.get("category") or "-",
        ])
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    def fmt_row(cols: List[str]) -> str:
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
    print(fmt_row(headers))
    for r in rows:
        print(fmt_row(r))


def summary(args: argparse.Namespace) -> None:
    data = load_data()
    expenses = filter_expenses(data["expenses"], None, args.month)
    total = sum(float(e.get("amount", 0)) for e in expenses)
    if args.month is None:
        print(f"Total expenses: ${total:.2f}")
    else:
        mname = month_name(args.month)
        print(f"Total expenses for {mname}: ${total:.2f}")
    # Budget warning
    if args.month is not None:
        y, m = month_to_ym(args.month, date.today().year)
        key = ym_key(y, m)
        budget_map: Dict[str, float] = data.get("budgets", {})
        if key in budget_map:
            budget_amount = float(budget_map[key])
            if total > budget_amount:
                print(f"Warning: over budget for {key}! Budget ${budget_amount:.2f}, spent ${total:.2f}")


def budget_set(args: argparse.Namespace) -> None:
    data = load_data()
    y, m = month_to_ym(args.month, date.today().year)
    key = ym_key(y, m)
    data.setdefault("budgets", {})[key] = validate_amount(args.amount)
    save_data(data)
    print(f"Budget set for {key}: ${float(data['budgets'][key]):.2f}")


def budget_show(args: argparse.Namespace) -> None:
    data = load_data()
    budgets: Dict[str, float] = data.get("budgets", {})
    if args.month is None:
        if not budgets:
            print("No budgets set.")
            return
        headers = ["Month", "Budget"]
        rows = [[k, f"${float(v):.2f}"] for k, v in sorted(budgets.items())]
        widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
        def fmt_row(cols: List[str]) -> str:
            return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
        print(fmt_row(headers))
        for r in rows:
            print(fmt_row(r))
    else:
        y, m = month_to_ym(args.month, date.today().year)
        key = ym_key(y, m)
        if key in budgets:
            print(f"Budget for {key}: ${float(budgets[key]):.2f}")
        else:
            print(f"No budget set for {key}.")


def export_csv(args: argparse.Namespace) -> None:
    data = load_data()
    expenses = filter_expenses(data["expenses"], args.category, args.month)
    if not expenses:
        print("No expenses to export.")
        return
    out_path = Path(args.csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "date", "description", "amount", "category"])
        writer.writeheader()
        for e in expenses:
            writer.writerow({
                "id": e.get("id"),
                "date": e.get("date"),
                "description": e.get("description"),
                "amount": e.get("amount"),
                "category": e.get("category"),
            })
    print(f"Exported {len(expenses)} expenses to {out_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="expense-tracker", description="Expense Tracker CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="Add an expense")
    p_add.add_argument("--description", required=True, help="Expense description")
    p_add.add_argument("--amount", required=True, type=float, help="Expense amount (positive number)")
    p_add.add_argument("--date", help="Date in YYYY-MM-DD format (default: today)")
    p_add.add_argument("--category", help="Optional category tag")
    p_add.set_defaults(func=add_expense)

    # update
    p_upd = sub.add_parser("update", help="Update an expense")
    p_upd.add_argument("--id", required=True, type=int, help="Expense ID")
    p_upd.add_argument("--description", help="New description")
    p_upd.add_argument("--amount", type=float, help="New amount (positive number)")
    p_upd.add_argument("--date", help="New date in YYYY-MM-DD")
    p_upd.add_argument("--category", help="New category (empty to clear)")
    p_upd.set_defaults(func=update_expense)

    # delete
    p_del = sub.add_parser("delete", help="Delete an expense")
    p_del.add_argument("--id", required=True, type=int, help="Expense ID")
    p_del.set_defaults(func=delete_expense)

    # list
    p_list = sub.add_parser("list", help="List expenses")
    p_list.add_argument("--category", help="Filter by category")
    p_list.add_argument("--month", type=int, help="Filter by month (1-12) of current year")
    p_list.set_defaults(func=list_expenses)

    # summary
    p_sum = sub.add_parser("summary", help="Show total expenses")
    p_sum.add_argument("--month", type=int, help="Month (1-12) of current year")
    p_sum.set_defaults(func=summary)

    # budget
    p_budget = sub.add_parser("budget", help="Manage monthly budgets")
    budget_sub = p_budget.add_subparsers(dest="budget_cmd", required=True)
    p_bset = budget_sub.add_parser("set", help="Set monthly budget")
    p_bset.add_argument("--month", required=True, type=int, help="Month (1-12) of current year")
    p_bset.add_argument("--amount", required=True, type=float, help="Budget amount (positive number)")
    p_bset.set_defaults(func=budget_set)
    p_bshow = budget_sub.add_parser("show", help="Show budgets")
    p_bshow.add_argument("--month", type=int, help="Specific month (1-12) of current year")
    p_bshow.set_defaults(func=budget_show)

    # export
    p_export = sub.add_parser("export", help="Export expenses to CSV")
    p_export.add_argument("--csv", required=True, help="Output CSV path")
    p_export.add_argument("--category", help="Filter by category")
    p_export.add_argument("--month", type=int, help="Filter by month (1-12) of current year")
    p_export.set_defaults(func=export_csv)

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except argparse.ArgumentTypeError as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("Aborted.")


if __name__ == "__main__":
    main()


