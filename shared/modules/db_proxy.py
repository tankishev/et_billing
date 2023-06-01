# CODE needs cleaning to support both postgres and sqlite
from django.conf import settings
import sqlite3 as sl
import psycopg2 as pg


class DBProxy:
    """ A class used to extract data from the DB """

    def __init__(self):
        db_config = settings.DATABASES.get('default')
        if settings.DEBUG:
            self._conn = sl.connect(self._DB_NAME)
        else:
            self._conn = pg.connect(
                host=db_config.get('HOST'),
                port=db_config.get('PORT'),
                user=db_config.get('USER'),
                password=db_config.get('PASSWORD'),
                database=db_config.get('NAME'),
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

        # curr = self.conn.cursor()
        # if data is None:
        #     res = curr.execute(sql)
        # else:
        #     res = curr.execute(sql, data)
        # if commit:
        #     self.conn.commit()
        # return res

        curr = self.conn.cursor()
        try:
            if data is None:
                curr.execute(sql)
            else:
                curr.execute(sql, data)
            if commit:
                self.conn.commit()
            res = curr.fetchall()  # Retrieve the result, if needed
        except Exception as e:
            self.conn.rollback()  # Rollback the transaction
            raise e
        finally:
            curr.close()  # Close the cursor
        return res
