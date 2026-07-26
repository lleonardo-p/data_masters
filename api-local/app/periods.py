from datetime import date, datetime, timedelta


def parse_month(value: str) -> tuple[date, date]:
    for date_format in ("%Y-%m", "%m-%Y"):
        try:
            start = datetime.strptime(value, date_format).date().replace(day=1)

            if start.month == 12:
                end = date(start.year + 1, 1, 1)
            else:
                end = date(start.year, start.month + 1, 1)

            return start, end
        except ValueError:
            continue

    raise ValueError("Use YYYY-MM ou MM-YYYY.")


def parse_day(value: str) -> date:
    for date_format in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    raise ValueError("Use YYYY-MM-DD ou DD-MM-YYYY.")


def day_range(reference_date: date) -> tuple[date, date]:
    return reference_date, reference_date + timedelta(days=1)