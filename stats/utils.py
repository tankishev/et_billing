from django.db.models import OuterRef, Subquery

from vendors.models import VendorService
from .models import UsageStats


def get_stats_usage_not_in_vendor_services():
    """ Returns a QuerySet with UsageStats that do not have a corresponding VendorService """

    vs_subquery = VendorService.objects.filter(
        vendor_id=OuterRef('vendor_id'),
        service_id=OuterRef('service_id')
    ).values('service_id')[:1]

    return UsageStats.objects.annotate(vs_service_id=Subquery(vs_subquery)).filter(vs_service_id=None)
