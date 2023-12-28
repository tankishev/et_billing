
from contracts.models import Client, Contract
from stats.models import UsageTransaction
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
import re

logger = logging.getLogger(f'et_billing.{__name__}')


class BaseRater:

    def __init__(self, period='2023-11'):
        self.period_start = None
        self.period_end = None
        self.period = period
        self.transactions = []
        self._dev_setup()

    def _dev_setup(self):
        self.client = Client.objects.get(pk=7)

    @property
    def period(self):
        return self._period

    @period.setter
    def period(self, value):
        try:
            pattern = r'^\d{4}-\d{2}$'
            if isinstance(value, str) and re.match(pattern, value):
                self.period_start = datetime.strptime(value, '%Y-%m')
                self.period_end = self.period_start + relativedelta(months=1)
                self._period = value
            else:
                logger.warning(f'Period {value} is not in format YYYY-MM')

        except Exception as e:
            logger.error(f'Error: {e}')
            raise

    @property
    def client(self):
        return self._client

    @client.setter
    def client(self, value):
        try:
            self.transactions.clear()
            if isinstance(value, Client):
                usage_transactions = UsageTransaction.objects.filter(
                    vendor__client=value,
                    timestamp__gte=self.period_start,
                    timestamp__lt=self.period_end
                )
                if usage_transactions.exists():
                    transactions_list = list(usage_transactions)
                    self.transactions = sorted(transactions_list, key=lambda x: x.timestamp)

        except Exception as e:
            logger.error('Error: {e}')
            raise
