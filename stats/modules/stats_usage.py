from ..models import UsageStats


def save_service_usage(data):
    """ Saves service usage statistics
    :param data: tuple in format ('2022-12', vendor_id, service_id, 123)
    """
    period, vendor_id, service_id, unit_count = data

    try:
        usage = UsageStats.objects.get(period=period, vendor_id=vendor_id, service_id=service_id)
        if usage.unit_count != unit_count:
            usage.unit_count = unit_count
            usage.save()
    except UsageStats.DoesNotExist:
        usage = UsageStats.objects.create(
            period=period, vendor_id=vendor_id, service_id=service_id, unit_count=unit_count)
        usage.save()
