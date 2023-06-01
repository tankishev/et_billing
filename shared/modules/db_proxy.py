# CODE needs cleaning to support both postgres and sqlite
from django.conf import settings
import sqlite3 as sl
import psycopg2 as pg


class DBProxy:
    """ A class used to extract data from the DB """

    def __init__(self):
        self._debug = settings.DEBUG
        db_config = settings.DATABASES.get('default')
        db_name = db_config.get('NAME')
        if self._debug:
            self._conn = sl.connect(db_name)
        else:
            self._conn = pg.connect(
                host=db_config.get('HOST'),
                port=db_config.get('PORT'),
                user=db_config.get('USER'),
                password=db_config.get('PASSWORD'),
                database=db_name,
            )

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

        if self._debug:
            sql = sql.replace('%s', '?')
        try:
            curr = self.conn.cursor()
            if data is None:
                res = curr.execute(sql)
            else:
                res = curr.execute(sql, data)
            if commit:
                self.conn.commit()
            if settings.DEBUG:
                data = res.fetchall()
            else:
                data = curr.fetchall()  # Retrieve the result, if needed
        except Exception as e:
            if not self._debug:
                self.conn.rollback()  # Rollback the transaction
            raise e
        finally:
            curr.close()  # Close the cursor
        return data
