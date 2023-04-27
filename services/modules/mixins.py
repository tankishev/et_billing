# CODE OK ... ADD LOGGING
from services.models import FilterConfig, Service
from .db_proxy import DBProxyFilters
from .filters import FilterGroup


class FiltersMixin:
    """ A mixin class to add methods for loading service filters """

    def load_all_service_filters(self) -> dict:
        """ Returns a dictionary with FilterGroups for all services """

        services = Service.objects.all().filter(usage_based=True)
        service_filters = self.get_service_filters()
        return {el.service_id: FilterGroup(service_filters[el.filter_id]) for el in services}

    @staticmethod
    def load_vendor_service_filters(vendor_id, service_filters) -> dict | None:
        """ Returns a dictionary with FilterGroups for each service of the given vendor.
        :param vendor_id: vendor_id to load services for
        :param service_filters: a dictionary with services filter functions
        """

        dbp = DBProxyFilters()
        db_services = dbp.get_vendor_services_filters(vendor_id)
        if db_services:
            return {el[0]: FilterGroup(service_filters[el[1]]) for el in db_services}

    @staticmethod
    def get_service_filters() -> dict | None:
        """ Returns the service filters configuration in the DB in the form of {filter_id: [(func, value),]}"""

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
