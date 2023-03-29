class FieldFilter:
    """ A factory class to generage FieldFilters from given config """

    _ACCEPTED_FIELDS = ['transaction_type', 'transaction_status', 'description', 'cost', 'signing_type', 'receiver_pid']

    def __init__(self, field_name=None, func=None, lookup_value=None):
        self.field_name = field_name
        self.match_func = func
        self.lookup_value = lookup_value

    def apply(self, transaction):
        field_value = getattr(transaction, self.field_name)
        func = getattr(self, self.match_func)
        return func(field_value)

    @classmethod
    def set_accepted_fields(cls, fields):
        cls._ACCEPTED_FIELDS.clear()
        for field_name in fields:
            cls._ACCEPTED_FIELDS.append(field_name)

    @classmethod
    def create_filter(cls, filter_name, filter_value):
        field_name, func_name = filter_name.split('__')
        match_func_name = f'_match_{func_name}'
        if field_name in cls._ACCEPTED_FIELDS and hasattr(cls, match_func_name):
            filter_obj = cls(field_name, match_func_name, filter_value)
            return filter_obj

    # Filter functions
    def _match_gt(self, field_value):
        return field_value > self.lookup_value

    def _match_gte(self, field_value):
        return field_value >= self.lookup_value

    def _match_lte(self, field_value):
        return field_value <= self.lookup_value

    def _match_eq(self, field_value):
        return self.lookup_value == field_value

    def _match_not_eq(self, field_value):
        return self.lookup_value != field_value

    def _match_incl(self, field_value):
        return field_value in self.lookup_value

    def _match_not_incl(self, field_value):
        return field_value not in self.lookup_value


class FilterGroup:
    """ A class to hold a list of FieldFilters and method to apply them to a transaction """

    def __init__(self, filters_config=None):
        self.filters = []
        if filters_config:
            for filter_config in filters_config:
                if filter_config is not None:
                    self._add_filters_from_config(filter_config)

    def apply_all(self, transaction) -> bool:
        """ Returns True if the transaction matches all filters in the FilterGroup else returns False """

        for field_filter in self.filters:
            if not field_filter.apply(transaction):
                return False
        return True

    def _add_filters_from_config(self, filter_config):
        """ Adds filters to the FieldGroup given the config
        :param filter_config: a tuple of (field_name__func_name, filter_value)
        """

        field_filter = FieldFilter.create_filter(*filter_config)
        if field_filter:
            self.filters.append(field_filter)
