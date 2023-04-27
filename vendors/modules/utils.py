# CODE OK
from ..models import VendorService


def get_vendor_services_not_in_orders():
    """ Returns o ValuesListQuerySet with the VendorServices not included in Order objects """

    vs = VendorService.objects.filter(
        vendor__client__is_billable=True,
        vendor__client__is_validated=True,
        orderservice__isnull=True
    ).values_list('vendor_id', 'service_id', 'service__service', 'service__stype', 'service__desc_en')
    return vs
