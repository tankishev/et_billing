from django.conf import settings
import sqlite3 as sl


class DBProxy:

    _DB_NAME = settings.DATABASES.get('default').get('NAME')

    def __init__(self):
        self._conn = sl.connect(self._DB_NAME)

    @property
    def conn(self):
        return self._conn

    def close(self):
        self.conn.close()

    def exec(self, sql, data=None, commit=False):
        """
        Save data to db given sql expression
        :param sql: valid sql expression with data placeholders
        :param data: data tuple
        :param commit: commit the transaction
        :return: result
        """

        curr = self.conn.cursor()
        if data is None:
            res = curr.execute(sql)
        else:
            res = curr.execute(sql, data)
        if commit:
            self.conn.commit()
        return res

    def get_vendor_services(self, vendor_id):
        """ Return the services configured for a given vendor
        """
        sql = """
            select s.service_id,
            case
                when vso.filter_id isnull
                then s.filter_id
                else vso.filter_id
            end as filter_name
            from vendor_services vs
            left join services s on vs.service_id = s.service_id
            left join vendor_filters_overrides vso on vs.service_id = vso.service_id and vs.vendor_id = vso.vendor_id
            where vs.vendor_id = ? and usage_based = 1
            """
        res = self.exec(sql, (vendor_id,))
        services = res.fetchall()
        if services:
            return services
