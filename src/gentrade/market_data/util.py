import logging
import time
import datetime

import ntplib
from dateutil.tz import tzlocal

LOG = logging.getLogger(__name__)

def check_ntp_offset() -> float:
    """
    Sync with NTP server

    :return : offset in seconds
    """
    ntp_servers = [
        'ntp.ntsc.ac.cn', 'ntp.sjtu.edu.cn', 'cn.ntp.org.cn',
        'cn.pool.ntp.org', 'ntp.aliyun.com'
        ]
    retry = len(ntp_servers) - 1
    client = ntplib.NTPClient()
    while retry > 0:
        LOG.info("Try to get time from NTP: %s", ntp_servers[retry])

        try:
            ret = client.request(ntp_servers[retry], version=3)
            offset = (ret.recv_time - ret.orig_time +
                    ret.dest_time - ret.tx_time) / 2
            LOG.info("NTP offset: %.2f seconds", offset)
            return offset
        except ntplib.NTPException:
            LOG.error("Fail to get time, try another")
            retry -= 1
            continue
    return None

def get_timezone():
    """
    Get timezone info
    """
    now_ts_local = time.time()
    now_date_utc   = datetime.datetime.fromtimestamp(now_ts_local, datetime.UTC)
    tl = tzlocal()

    return {
        'tz_name': tl.tzname(now_date_utc),
        'tz_offset': int(tl.utcoffset(now_date_utc).total_seconds()),
    }
