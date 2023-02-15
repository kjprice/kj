import numpy as np

SECOND = 1
MINUTE = SECOND * 60
HOUR = MINUTE * 60
DAY = HOUR * 24

def format_time(seconds: float, show_trailing_ms = False) -> str:
  if seconds < SECOND:
    ms =  int(seconds * 1000)
    return f'{ms}ms'

  if not show_trailing_ms:
    seconds = int(seconds)

  if seconds == 0:
    return ''
  if seconds < MINUTE:
    return f'{seconds}s'
  if seconds < HOUR:
    minutes = int(seconds / MINUTE)
    seconds_remainder = seconds % MINUTE
    seconds_formatted = format_time(seconds_remainder, show_trailing_ms)
    return f'{minutes}m{seconds_formatted}'
  if seconds < DAY:
    hours = int(seconds / HOUR)
    minutes_remainder = seconds % HOUR
    minutes_formatted = format_time(minutes_remainder, show_trailing_ms)
    return f'{hours}h{minutes_formatted}'
  
  days = int(seconds / DAY)
  hours_remainder = seconds % DAY
  hours_formatted = format_time(hours_remainder, show_trailing_ms)
  return f'{days}d{hours_formatted}'
