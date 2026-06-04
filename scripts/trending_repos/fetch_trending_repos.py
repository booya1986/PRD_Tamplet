import datetime


def iso_week_string(d):
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def since_date(d):
    return (d - datetime.timedelta(days=7)).isoformat()
