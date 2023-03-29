from services.models import FilterConfig
from .filters import FilterGroup


class FiltersMixin:

    def load_vendor_service_filters(self, vendor_id, service_filters):
        db_services = self.dba.get_vendor_services(vendor_id)
        if db_services is None:
            return
        return {el[0]: FilterGroup(service_filters[el[1]]) for el in db_services}

    @staticmethod
    def get_service_filters():
        """ Returns the service filters configuration in the DB"""

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

