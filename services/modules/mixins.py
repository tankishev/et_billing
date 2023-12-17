from __future__ import annotations
from typing import Dict, List, Tuple
from django.db.models import OuterRef, Case, When, Subquery, Exists, IntegerField, F

from vendors.models import VendorService, VendorFilterOverride
from services.models import FilterConfig, Service
from .filters import FilterGroup

from celery.utils.log import get_task_logger
import logging


logger = logging.getLogger(f'et_billing.{__name__}')
celery_logger = get_task_logger(f'et_billing.celery.{__name__}')


class FiltersMixin:
    """ A mixin class to add methods for loading service filters.
        Filters are used to identify the service for each transaction in a vendor input file
    """

    def load_all_service_filters(self, usage_based_only=True) -> Dict[int, FilterGroup]:
        """ Returns a dictionary with FilterGroups for all services """

        celery_logger.debug("Loading service filters")
        services = Service.objects.all().filter(usage_based=usage_based_only)
        service_filters = self.get_filter_configs()
        return {el.service_id: FilterGroup(service_filters[el.filter_id]) for el in services}

    def load_vendor_service_filters(self, vendor_id: int) -> Dict[int, FilterGroup] | None:
        """ Returns a dictionary with FilterGroups for each service of the given vendor.
            :param vendor_id: vendor_id to load services for
            :returns : {service_id: FilterGroup}
        """

        celery_logger.debug(f"Loading service filters for vendor {vendor_id}")

        db_services = self.get_vendor_service_filters(vendor_id)
        if db_services:
            celery_logger.debug("Services loaded. Returning filters")
            service_filters = self.get_filter_configs()
            return {el[0]: FilterGroup(service_filters[el[1]]) for el in db_services}
        celery_logger.critical("No services found")

    @staticmethod
    def get_filter_configs() -> Dict[int, List[Tuple[str, int]]] | None:
        """ Loads the service filters configuration from the DB and returns them in the form of a dict.
            Example: {2: [(transaction_type__eq, 1), (status__not_eq, 5)]}
        """

        try:
            filter_configs = FilterConfig.objects.all()
            retval = {}
            for el in filter_configs:
                filter_id = el.filter_id
                filter_func = f'{el.field}__{el.func.func}'
                value = el.value

                if value.isdigit():
                    value = int(value)
                elif value.replace('.', '', 1).isdigit():
                    value = float(value)

                if filter_id not in retval:
                    retval[filter_id] = []
                retval[filter_id].append((filter_func, value))

            return retval
        except FilterConfig.DoesNotExist:
            return None

    @staticmethod
    def get_vendor_service_filters(vendor_id: int, usage_based_only=True) -> List[Tuple[int, int]]:
        """ Returns the applicable filter_id for each VendorService service_id
            :param vendor_id: ID of vendor for which to extract the filter_id
            :param usage_based_only: return records only for usage based services
            :return: [(service_id, filter_id), ]
        """
        vfo_subquery = VendorFilterOverride.objects.filter(
            vendor_id=OuterRef('vendor_id'),
            service_id=OuterRef('service_id')
        ).values('filter_id')[:1]

        vs = VendorService.objects.filter(vendor_id=vendor_id, service__usage_based=usage_based_only) \
            .annotate(
            filter_name=Case(
                When(Exists(Subquery(vfo_subquery)), then=Subquery(vfo_subquery)),
                default=F('service__filter_id'),
                output_field=IntegerField()
            )) \
            .values_list('service_id', 'filter_name')

        return list(vs)


class ServicesMixin:
    """ A class to add methods to access Services objects """

    @staticmethod
    def get_service_types_for_reports() -> Dict[int: Dict[str: str]] | None:
        """ Returns the list of services in the DB
        :return: None or {service_id: {service, stype}}
        """

        services_data = Service.objects.order_by('service_order').values_list('service_id', 'service', 'stype')
        if services_data.exists():
            return {_id: {'service': service, 'stype': stype} for _id, service, stype in services_data}
