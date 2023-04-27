# CODE OK ... ADD LOGGER
from ..models import UsageStats


def save_service_usage(period: str, vendor_id: int, service_id: int, unit_count: int) -> None:
    """ Saves or updates service usage statistics. """

    try:
        usage = UsageStats.objects.get(period=period, vendor_id=vendor_id, service_id=service_id)
        if usage.unit_count != unit_count:
            usage.unit_count = unit_count
            usage.save()

    except UsageStats.DoesNotExist:
        usage = UsageStats.objects.create(
            period=period, vendor_id=vendor_id, service_id=service_id, unit_count=unit_count)
        usage.save()
