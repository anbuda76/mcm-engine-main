def format_percent(value):
    try:
        return f"{value:.1f}%"
    except:
        return "-"
