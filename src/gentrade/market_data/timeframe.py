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

    SUPPORTED = {
        "1m"  : "1min",
        "15m" : "15min",
        "1h"  : "1hour",
        "4h"  : "4hour",
        "8h"  : "8hour",
        "12h" : "12hour",
        "1d"  : "1day",
        "1w"  : "1week",
        "1M"  : "1mon",
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
            delta = datetime.timedelta(-today.weekday(), weeks=-1 * self.count)
            pre = today + delta
            pre_date = datetime.datetime(pre.year, pre.month, pre.day, 0, 0, 0,
                                         tzinfo=datetime.UTC)
            return pre_date.timestamp()

        if self.interval == TimeFrame.MONTH:
            pre_year = today.year
            pre_month = today.month - 1 * self.count
            if pre_month <= 0:
                pre_month += 12
                pre_year -= 1
            pre_date = datetime.datetime(pre_year, pre_month, 1, 0, 0, 0,
                                         tzinfo=datetime.UTC)
            return pre_date.timestamp()
        return None

    def ts_last_limit(self, limit, to=-1):
        """
        Get the timestamp back in the time before limit count's interval
        till reference timestamp.
        """
        last_ts = self.ts_last(to)
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
            first_month = datetime.datetime(
                previous_year_index, previous_month_index, 1,
                tzinfo=datetime.UTC)
            return first_month.timestamp()

        return None

    def ts_since(self, since_ts:int) -> int:
        """
        Get the timestamp of the first frame boundary close to since date
        ------------------------------------------------------
           ^             ^
           |             | xxxxxxxxxxx Time Frame  xxxxxxxxxxx
         since    first frame boundary
        if since is just in the first frame boundary, then return it.
        """
        if self.interval in [TimeFrame.MINUTE, TimeFrame.HOUR, TimeFrame.DAY]:
            delta_ts = TimeFrame._delta[self.interval] * self.count
            if int(since_ts) % delta_ts != 0:
                next_ts = (int(since_ts / delta_ts) + 1) * delta_ts
            else:
                next_ts = (int(since_ts / delta_ts)) * delta_ts
            return next_ts

        since_day = datetime.datetime.fromtimestamp(since_ts)
        if since_day.weekday() == 0:
            this_week_first_day_ts = datetime.datetime(
                since_day.year, since_day.month, since_day.day).replace(
                    tzinfo=datetime.timezone.utc).timestamp()
            if this_week_first_day_ts == since_ts:
                return since_ts
        if self.interval == TimeFrame.WEEK:
            next_week_day = since_day + datetime.timedelta(
                days=8 - since_day.isoweekday())
            next_week = datetime.datetime(
                next_week_day.year, next_week_day.month,
                next_week_day.day)
            next_week_ts = next_week.replace(
                tzinfo=datetime.timezone.utc).timestamp()
            return next_week_ts

        if self.interval == TimeFrame.MONTH:
            assert self.count == 1
            this_month_first_day_ts = datetime.datetime(
                since_day.year, since_day.month,
                1).replace(tzinfo=datetime.timezone.utc).timestamp()
            if since_ts == this_month_first_day_ts:
                return since_ts
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
            while next_month_index >= 12:
                next_month_index -= 12
                next_year_index += 1
            next_month = datetime.datetime(
                next_year_index, next_month_index+1, 1)
            next_last_ts = next_month.replace(
                tzinfo=datetime.timezone.utc).timestamp()

        if next_last_ts > time.time():
            next_last_ts = self.ts_last()

        return next_last_ts

    def calculate_count(self, since:int, max_count:int=-1, to:int=-1) -> int:
        start = self.ts_since(since)
        if to == -1:
            to = self.ts_since_limit(since, max_count)

        assert to >= start, "start:%d to:%d" % (start, to)

        if self.interval in [TimeFrame.MINUTE, TimeFrame.HOUR,
                             TimeFrame.DAY, TimeFrame.WEEK]:
            delta_ts = TimeFrame._delta[self.interval] * self.count
            if max_count != -1:
                return min(max_count, int((to - start) / delta_ts) + 1)
            return int((to - start) / delta_ts) + 1

        if self.interval == TimeFrame.MONTH:
            start_date = datetime.datetime.fromtimestamp(start)
            to_date = datetime.datetime.fromtimestamp(to)
            delta_year = to_date.year - start_date.year
            delta_month = to_date.month - start_date.month
            if delta_month < 0:
                delta_month += 12
                delta_year -= 1
            if max_count == -1:
                return delta_month + delta_year * 12 + 1
            return min(max_count, delta_month + delta_year * 12 + 1)

        return None

    def is_same_frame(self, source, target) -> bool:
        if self.interval in [TimeFrame.MINUTE, TimeFrame.HOUR,
                             TimeFrame.DAY, TimeFrame.WEEK]:
            return abs(target -source) <= \
                TimeFrame._delta[self.interval] * self.count

        if self.interval == TimeFrame.MONTH:
            date_source = datetime.datetime.fromtimestamp(source)
            date_target = datetime.datetime.fromtimestamp(target)
            return (date_source.year == date_target.year and \
                date_target.month == date_source.month)
        return False

    @staticmethod
    def check_valid(tf_str:str):
        return tf_str[-1] in [
            TimeFrame.MINUTE, TimeFrame.HOUR,
            TimeFrame.DAY, TimeFrame.WEEK,
            TimeFrame.MONTH ]

    def normalize(self, since, to, limit):
        if limit == -1:
            assert since != -1, "since must be set without limit"
            since_new = self.ts_since(since)
            to_new = self.ts_last(to)
        else:
            if since == -1:
                since_new = self.ts_last_limit(limit, to)
            else:
                since_new = self.ts_since(since)
            to_new = self.ts_since_limit(since_new, limit)
        return (since_new, to_new)
