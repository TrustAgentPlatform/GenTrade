"""
Time Interval class
"""
import logging
import time
import datetime

LOG = logging.getLogger(__name__)

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

        ----------------------------------------------------------
                               ^                            ^
        Time Frame xxxxxxxxxxx |                            |
                     last frame boundary                 current

        """
        if refer_ts == -1:
            refer_ts = time.time()

        if self.interval in [TimeFrame.MINUTE, TimeFrame.HOUR, TimeFrame.DAY]:
            delta_ts = TimeFrame._delta[self.interval] * self.count
            last_now_ts = int(refer_ts / delta_ts) * delta_ts
            return last_now_ts

        today = datetime.datetime.fromtimestamp(refer_ts)
        if self.interval == TimeFrame.WEEK:
            # TODO: now only support 1w, but 4w or 8w
            assert self.count == 1
            last_week = datetime.datetime(
                today.year, today.month, today.day - today.weekday())
            last_week_ts = last_week.replace(
                tzinfo=datetime.timezone.utc).timestamp()
            return last_week_ts

        if self.interval == TimeFrame.MONTH:
            # TODO: now only support 1M, but 4M or 8M
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

            while previous_month_index < 0:
                previous_month_index += 12
                previous_year_index -= 1
            first_month = datetime.datetime(previous_year_index,
                                            previous_month_index, 1)
            first_month_ts = first_month.replace(
                tzinfo=datetime.timezone.utc).timestamp()
            return first_month_ts

        return None

    def ts_since(self, since_ts:int) -> int:
        """
        Get the timestamp of the first frame boundary close to since date
        ------------------------------------------------------
           ^             ^
           |             | xxxxxxxxxxx Time Frame  xxxxxxxxxxx
         since    first frame boundary
        """
        if self.interval in [TimeFrame.MINUTE]:
            # BUG: sound like binance API has issue to handle minute,
            # so workaround here
            delta_ts = TimeFrame._delta[self.interval] * self.count
            next_ts = (int(since_ts / delta_ts)) * delta_ts
            return next_ts

        if self.interval in [TimeFrame.HOUR, TimeFrame.DAY]:
            delta_ts = TimeFrame._delta[self.interval] * self.count
            next_ts = (int(since_ts / delta_ts) + 1) * delta_ts
            return next_ts


        since_day = datetime.datetime.fromtimestamp(since_ts)
        if self.interval == TimeFrame.WEEK:
            next_week = datetime.datetime(
                since_day.year, since_day.month,
                since_day.day + (7 - since_day.weekday()))
            next_week_ts = next_week.replace(
                tzinfo=datetime.timezone.utc).timestamp()
            return next_week_ts

        if self.interval == TimeFrame.MONTH:
            assert self.count == 1
            LOG.info("since day: %s", since_day)
            if since_day.month == 12:
                next_month = datetime.datetime(
                    since_day.year + 1, 1, 1)
            else:
                next_month = datetime.datetime(
                    since_day.year, since_day.month + 1, 1)

            next_month_ts = next_month.replace(
                tzinfo=datetime.timezone.utc).timestamp()
            return next_month_ts

        return None

    def ts_since_limit(self, since_ts:int, limit:int) -> int:
        next_first_ts = self.ts_since(since_ts)
        if self.interval in [TimeFrame.MINUTE, TimeFrame.HOUR,
                             TimeFrame.DAY, TimeFrame.WEEK]:
            delta_ts = TimeFrame._delta[self.interval] * self.count
            next_last_ts = next_first_ts + (limit - 1) * delta_ts

        if self.interval == TimeFrame.MONTH:
            since_day = datetime.datetime.fromtimestamp(since_ts)
            next_month_index = since_day.month + (limit - 1)
            next_year_index = since_day.year
            while next_month_index > 12:
                next_month_index -= 12
                next_year_index += 1
            next_month = datetime.datetime(
                next_year_index, next_month_index+1, 1)
            next_last_ts = next_month.replace(
                tzinfo=datetime.timezone.utc).timestamp()

        if next_last_ts > time.time():
            next_last_ts = self.ts_last()

        return next_last_ts

    def calculate_count(self, since_ts:int, max_count:int) -> int:
        start = self.ts_since(since_ts)
        to = self.ts_since_limit(since_ts, max_count)

        if self.interval in [TimeFrame.MINUTE, TimeFrame.HOUR,
                             TimeFrame.DAY, TimeFrame.WEEK]:
            delta_ts = TimeFrame._delta[self.interval] * self.count
            return min(max_count, (to - start) / delta_ts + 1)

        if self.interval == TimeFrame.MONTH:
            start_date = datetime.datetime.fromtimestamp(start)
            to_date = datetime.datetime.fromtimestamp(to)
            delta_month = to_date.month - start_date.month
            if delta_month < 0:
                delta_month += 12
            return min(max_count, delta_month + 1)

        return None
