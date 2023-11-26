# CODE OK ... ADD LOGGING
from services.models import FilterConfig, Service
from .db_proxy import DBProxyFilters
from .filters import FilterGroup

from celery.utils.log import get_task_logger
import logging


logger = logging.getLogger('et_billing.services.mixins')
celery_logger = get_task_logger('services.mixins')


class FiltersMixin:
    """ A mixin class to add methods for loading service filters.
        Filters are used to identify the service for each transaction in a vendor input file
    """

    def load_all_service_filters(self, usage_based_only=True) -> dict:
        """ Returns a dictionary with FilterGroups for all services """

        celery_logger.debug("Loading service filters")
        services = Service.objects.all().filter(usage_based=usage_based_only)
        service_filters = self.get_service_filters()
        return {el.service_id: FilterGroup(service_filters[el.filter_id]) for el in services}

    @staticmethod
    def load_vendor_service_filters(vendor_id, service_filters) -> dict | None:
        """ Returns a dictionary with FilterGroups for each service of the given vendor.
        :param vendor_id: vendor_id to load services for
        :param service_filters: a dictionary with services filter functions
        """

        celery_logger.debug(f"Loading service filters for vendor {vendor_id}")
        dbp = DBProxyFilters()
        db_services = dbp.get_vendor_services_filters(vendor_id)
        if db_services:
            celery_logger.debug("Services loaded. Returning filters")
            return {el[0]: FilterGroup(service_filters[el[1]]) for el in db_services}
        celery_logger.critical("No services found")

    @staticmethod
    def get_service_filters() -> dict | None:
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


class ServicesMixin:
    """ A class to add methods to access Services objects """

    @staticmethod
    def get_service_types_for_reports() -> dict[int: dict[str: str]] | None:
        """ Returns the list of services in the DB
        :return: None or {service_id: {service, stype}}
        """

        services_data = Service.objects.order_by('service_order').values_list('service_id', 'service', 'stype')
        if services_data.exists():
            return {_id: {'service': service, 'stype': stype} for _id, service, stype in services_data}
