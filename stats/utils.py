# CODE OK
from .models import UsageStats


def get_stats_usage_not_in_vendor_services():
    """ Returns a QuerySet with UsageStats that do not have a corresponding VendorService """
    return UsageStats.objects.raw(
        'select * from stats_usage su '
        'left join vendor_services vs on su.service_id = vs.service_id and su.vendor_id = vs.vendor_id '
        'where vs.service_id is null'
    )
