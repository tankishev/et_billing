from shared.modules import DBProxy


class DBProxyFilters(DBProxy):
    """ A class used to access complex DB queries for Filter object """
    def get_vendor_services_filters(self, vendor_id) -> list:
        """ Return the filter_id for each service_id
            :param vendor_id: The vendor for which the filters should be returned
        """

        sql = """
            select s.service_id,
            case
                when vso.filter_id is null
                then s.filter_id
                else vso.filter_id
            end as filter_name
            from vendor_services vs
            left join services s on vs.service_id = s.service_id
            left join vendor_filters_overrides vso on vs.service_id = vso.service_id and vs.vendor_id = vso.vendor_id
            where vs.vendor_id = %s and usage_based = 1
            """
        res = self.exec(sql, data=(vendor_id,))
        # return res.fetchall()
        return res
