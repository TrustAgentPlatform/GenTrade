"""
Time Interval class
"""
import time
import datetime

class TimeFrame:

    SECOND = "s"
    MINUTE = "m"
    HOUR   = "h"
    DAY    = "d"
    WEEK   = "w"
    MONTH  = "M"

    _delta = {
        MINUTE : 60,
        HOUR   : 60 * 60,
        DAY    : 60 * 60 * 24,
        WEEK   : 60 * 60 * 24 * 7
    }

    def __init__(self, name="1h") -> None:
        self.interval = name[-1]
        assert self.interval in [ TimeFrame.MINUTE, TimeFrame.HOUR,
            TimeFrame.DAY, TimeFrame.WEEK, TimeFrame.MONTH ]
        self.count = int(name[0:-1])

    def __str__(self) -> str:
        return "%d%s" % (self.count, self.interval)

    def ts_last(self, refer_ts=-1):
        """
        Get the timestamp of the last frame boundary from the reference's
        timestamp. If reference's timestamp is -1, then it is now

        :param current: the end timestamp for reference
        """
        if refer_ts == -1:
            refer_ts = time.time()

        if self.interval in [TimeFrame.MINUTE, TimeFrame.HOUR, TimeFrame.DAY]:
            delta_ts = TimeFrame._delta[self.interval] * self.count
            last_now_ts = int(refer_ts / delta_ts) * delta_ts
            return last_now_ts

        today = datetime.datetime.fromtimestamp(refer_ts)
        if self.interval == TimeFrame.WEEK:
            assert self.count == 1
            last_week = datetime.datetime(
                today.year, today.month, today.day - today.weekday())
            last_week_ts = last_week.replace(
                tzinfo=datetime.timezone.utc).timestamp()
            return last_week_ts

        if self.interval == TimeFrame.MONTH:
            assert self.count == 1
            today = datetime.datetime.now()
            last_month = datetime.datetime(today.year, today.month, 1)
            last_month_ts = last_month.replace(
                tzinfo=datetime.timezone.utc).timestamp()
            return last_month_ts
        return None

    def ts_last_limit(self, limit, refer_ts=-1):
        """
        Get the timestamp back in the time before limit count's interval
        till reference timestamp.
        """
        last_ts = self.ts_last(refer_ts)
        if self.interval in [TimeFrame.MINUTE, TimeFrame.HOUR,
                             TimeFrame.DAY, TimeFrame.WEEK]:
            delta_ts = TimeFrame._delta[self.interval] * self.count
            return last_ts - (limit - 1) * delta_ts

        if self.interval == TimeFrame.MONTH:
            last_month = datetime.datetime.fromtimestamp(last_ts)
            previous_month_index = last_month.month - (limit - 1)
            previous_year_index = last_month.year
            if previous_month_index < 0:
                previous_month_index += 12
                previous_year_index -= 1
            first_month = datetime.datetime(previous_year_index,
                                            previous_month_index, 1)
            first_month_ts = first_month.replace(
                tzinfo=datetime.timezone.utc).timestamp()
            return first_month_ts

        return None
