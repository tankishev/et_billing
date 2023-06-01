# CODE needs cleaning to support both postgres and sqlite
from django.conf import settings
import sqlite3 as sl
import psycopg2 as pg


class DBProxy:
    """ A class used to extract data from the DB """

    _DB_NAME = settings.DATABASES.get('default').get('NAME')

    def __init__(self):
        # self._conn = sl.connect(self._DB_NAME)
        self._conn = pg.connect(database=self._DB_NAME)

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
            # res = curr.execute(sql)
            curr.execute(sql)
        else:
            # res = curr.execute(sql, data)
            curr.execute(sql, data)
        if commit:
            self.conn.commit()
        # return res
        res = curr.fetchall()
        curr.close()
        return res
