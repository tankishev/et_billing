# CODE OK
from django.conf import settings
import sqlite3 as sl


class DBProxy:
    """ A class used to extract data from the DB """

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
