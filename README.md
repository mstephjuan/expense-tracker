# Expense Tracker (CLI)

A simple command-line expense tracker with JSON storage in your home directory.

## Install / Run

- Windows PowerShell:
```powershell
python expense-tracker\expense_tracker.py --help
```

- Optional: Add a shim so you can run `expense-tracker` from anywhere:
```powershell
New-Item -ItemType File -Path expense-tracker\expense-tracker.cmd -Force -Value "@echo off\r\npython %~dp0expense_tracker.py %*\r\n"
```
Then run:
```powershell
.\expense-tracker\expense-tracker.cmd --help
```

The app stores data at `%USERPROFILE%\.expense_tracker\data.json`.

## Commands

- Add expense:
```powershell
python expense-tracker\expense_tracker.py add --description "Lunch" --amount 20 --category Food
```
- Update expense:
```powershell
python expense-tracker\expense_tracker.py update --id 1 --amount 25
```
- Delete expense:
```powershell
python expense-tracker\expense_tracker.py delete --id 1
```
- List expenses:
```powershell
python expense-tracker\expense_tracker.py list
python expense-tracker\expense_tracker.py list --category Food
python expense-tracker\expense_tracker.py list --month 8
```
- Summary:
```powershell
python expense-tracker\expense_tracker.py summary
python expense-tracker\expense_tracker.py summary --month 8
```
- Budgets:
```powershell
python expense-tracker\expense_tracker.py budget set --month 8 --amount 200
python expense-tracker\expense_tracker.py budget show
python expense-tracker\expense_tracker.py budget show --month 8
```
- Export CSV:
```powershell
python expense-tracker\expense_tracker.py export --csv out\expenses.csv
```

## Notes
- Dates default to today; supply `--date YYYY-MM-DD` to set explicitly.
- `--month` refers to a month in the current year.
- Amounts must be positive; categories are optional.
