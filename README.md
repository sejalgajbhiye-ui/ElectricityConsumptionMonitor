# Electricity Consumption Monitor

Desktop Tkinter application with MySQL login and registration, electricity bill estimation, insights, CO2 impact, and PDF export.

## Database SQL

```sql
CREATE DATABASE electricity_app;

USE electricity_app;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE,
    password VARCHAR(255)
);
```

## Install

```powershell
pip install mysql-connector-python matplotlib reportlab
```

## Run

```powershell
python app.py
```

## Notes

- Update MySQL credentials in `app.py` if your local setup is different
- Passwords are stored as SHA-256 hashes
- Requires Python with Tkinter support
