from django.db.models import RestrictedError, Count, Subquery, Q, Exists, OuterRef, DateField, Value
from django.db.models.functions import TruncMonth, Coalesce
from django.utils import timezone

from contracts.models import Contract, OrderService
from vendors.models import VendorService
from stats.models import UsageStats

from datetime import datetime
from dateutil.relativedelta import relativedelta


def get_duplicated_account_services_in_active_orders(client_id):
    vs_qs = VendorService.objects.filter(
        orderservice__order__is_active=True, vendor__client_id=client_id
    ).annotate(num_count=Count('orderservice')).filter(num_count__gt=1).order_by('vendor_id', 'service_id')
    return vs_qs


def get_account_service_not_in_active_orders(client_id):
    os_to_exclude = OrderService.objects.filter(
        order__contract__client_id=client_id,
        order__is_active=True
    ).values('pk')

    vs_qs = VendorService.objects.filter(
        vendor__client_id=client_id
    ).exclude(
        orderservice__in=Subquery(os_to_exclude)
    ).order_by('vendor_id', 'service_id')
    return vs_qs


def get_active_contracts_without_active_orders(client_id):
    contracts_qs = Contract.objects.filter(
        client_id=client_id,
        is_active=True
    ).annotate(
        active_order_count=Count(
            'orders',
            filter=Q(orders__is_active=True),
            distinct=True
        )
    ).filter(active_order_count=0)
    return contracts_qs


def get_usage_data_without_account_service(client_id):
    vs_set = VendorService.objects.filter(
        vendor=OuterRef('vendor'),
        service=OuterRef('service')
    )
    unmatched_us_qs = UsageStats.objects.filter(vendor__client_id=client_id).exclude(
        Exists(vs_set)
    ).order_by('period', 'vendor_id', 'service_id')
    return unmatched_us_qs


def get_usage_without_orders(client_id, months_range=0):

    first_day_of_current_month = timezone.now().date().replace(day=1)
    # Set report limit
    min_period = None
    if months_range != 0:
        min_period = first_day_of_current_month + relativedelta(months=-months_range)

    # Get stats_usage data
    vs_sub_query = VendorService.objects.filter(
        vendor_id=OuterRef('vendor_id'),
        service_id=OuterRef('service_id')
    ).values('id')[:1]

    usage_period_qs = UsageStats.objects.filter(
        vendor__client_id=client_id
    ).annotate(vs_id=Subquery(vs_sub_query))
    if min_period:
        usage_period_qs = usage_period_qs.filter(period__gte=min_period)
    usage_period_qs = usage_period_qs.values_list('period', 'vs_id', 'vendor_id', 'service_id').distinct()

    # Prepare stats_usage sets & dict
    vs_set = set()
    us_set = set()
    for el in usage_period_qs:
        vs_set.add((el[1], el[2], el[3]))
        us_set.add((str(el[0]), el[1]))
    vs_dict = {el[0]: (el[1], el[2]) for el in vs_set}

    # Get orders services data
    order_service_qs = OrderService.objects.filter(order__contract__client_id=client_id)
    if min_period:
        order_service_qs = order_service_qs.filter(Q(order__end_date__isnull=True) | Q(order__end_date__gte=min_period))
    order_service_qs = order_service_qs.annotate(
        start_month=TruncMonth('order__start_date'),
        end_month=Coalesce(
            TruncMonth('order__end_date'),
            Value(first_day_of_current_month, output_field=DateField())
        )
    ).values_list('service', 'start_month', 'end_month').distinct()

    # Prepare order_services set
    os_set = set()
    for item in order_service_qs:
        service_id, start_date, end_date = item

        if isinstance(start_date, datetime):
            start_date = start_date.date()

        if isinstance(end_date, datetime):
            end_date = end_date.date()

        while start_date <= end_date:
            period = start_date.strftime('%Y-%m')
            os_set.add((period, service_id))
            start_date += relativedelta(months=1)

    # Find differences
    set_diff = us_set - os_set
    return [(el[0], vs_dict.get(el[1], ('N/A', 'N/A'))) for el in set_diff]
