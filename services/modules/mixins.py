from __future__ import annotations
from typing import Dict, List, Tuple
from django.db.models import OuterRef, Case, When, Subquery, Exists, IntegerField, F
from django.db.models.functions import Coalesce

from vendors.models import VendorService, VendorFilterOverride
from services.models import FilterConfig, Service
from .filters import FilterGroup

import logging


logger = logging.getLogger(f'et_billing.{__name__}')


class FiltersMixin:
    """ A mixin class to add methods for loading service filters.
        Filters are used to identify the service for each transaction in a vendor input file
    """

    def load_all_service_filters(self, usage_based_only=True) -> Dict[int, FilterGroup]:
        """ Returns a dictionary with FilterGroups for all services """

        logger.debug("Loading service filters")
        services = Service.objects.all().filter(usage_based=usage_based_only)
        service_filters = self.get_filter_configs()
        return {el.service_id: FilterGroup(service_filters[el.filter_id]) for el in services}

    def load_vendor_service_filters(self, vendor_id: int) -> Dict[int, FilterGroup] | None:
        """ Returns a dictionary with FilterGroups for each service of a given vendor.
            :param vendor_id: vendor_id to load services for
            :returns : {service_id: FilterGroup}
        """

        try:
            logger.debug(f"Loading service filters for vendor {vendor_id}")
            db_services = self.get_vendor_service_filters(vendor_id)

            if not db_services:
                logger.critical("No services found")
                return

            logger.debug("Services loaded. Returning filters")
            filter_configs = self.get_filter_configs()
            return {service_id: FilterGroup(filter_configs[filter_id]) for service_id, filter_id in db_services}

        except Exception as e:
            logger.error("Error: %s", e)
            raise

    def load_all_vendor_service_filters(self) -> Dict[int, Dict[int, FilterGroup]] | None:
        """ Returns a dictionary with FilterGroups for each service for each vendor.
            :returns : {vendor_id: {service_id: FilterGroup}}
        """

        try:
            logger.debug(f"Loading service filters for ALL vendor")
            db_services = self.get_all_vendor_service_filters()

            if not db_services:
                logger.critical("No services found")
                return

            logger.debug("Services loaded. Returning filters")
            filter_configs = self.get_filter_configs()
            service_filters_dict = dict()
            for vendor_id, service_id, filter_id in db_services:
                if vendor_id not in service_filters_dict.keys():
                    service_filters_dict[vendor_id] = dict()
                service_filters_dict[vendor_id][service_id] = FilterGroup(filter_configs[filter_id])

            return service_filters_dict

        except Exception as e:
            logger.error("Error: %s", e)
            raise

    @staticmethod
    def get_filter_configs() -> Dict[int, List[Tuple[str, int]]] | None:
        """ Loads the service filters configuration from the DB and returns them in the form of a dict.
            :returns {filter_id: [(filter_function, filter_value), ]
            Example: {2: [(transaction_type__eq, 1), (status__not_eq, 5)]}
        """

        try:
            filter_configs = FilterConfig.objects.select_related('func').all()
            filter_configs_list = list(filter_configs)
            retval = {}
            for el in filter_configs_list:
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

        except Exception as e:
            logger.error("Error: %s", e)
            raise

    @staticmethod
    def get_vendor_service_filters(vendor_id: int, usage_based_only=True) -> List[Tuple[int, int]]:
        """ Returns the applicable filter_id for each VendorService service_id
            :param vendor_id: ID of vendor for which to extract the filter_id
            :param usage_based_only: return records only for usage based services
            :return: [(service_id, filter_id), ]
        """
        try:
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

        except Exception as e:
            logger.error("Error: %s", e)
            raise

    @staticmethod
    def get_all_vendor_service_filters(usage_based_only=True) -> List[Tuple[int, int, int]]:
        """ Returns the applicable filter_id for each VendorService service_id for all vendors
            :param usage_based_only: return records only for usage based services
            :return: [(vendor_id, service_id, filter_id), ]
        """
        try:
            vfo_subquery = VendorFilterOverride.objects.filter(
                vendor_id=OuterRef('vendor_id'),
                service_id=OuterRef('service_id')
            ).values('filter_id')[:1]

            vs = VendorService.objects\
                .filter(service__usage_based=usage_based_only) \
                .annotate(res_filter_id=Coalesce(
                    Subquery(vfo_subquery, output_field=IntegerField()),
                    'service__filter__id',
                    output_field=IntegerField())) \
                .values_list('vendor_id', 'service_id', 'res_filter_id')

            if vs.exists():
                return list(vs)

        except Exception as e:
            logger.error("Error: %s", e)
            raise


class ServicesMixin:
    """ A class to add methods to access Services objects """

    @staticmethod
    def get_service_types_for_reports() -> Dict[int: Dict[str: str]] | None:
        """ Returns the list of services in the DB
        :return: None or {service_id: {service, stype}}
        """

        try:
            services_data = Service.objects.order_by('service_order').values_list('service_id', 'service', 'stype')
            if services_data.exists():
                return {_id: {'service': service, 'stype': stype} for _id, service, stype in services_data}

        except Exception as e:
            logger.error("Error: %s", e)
            raise
