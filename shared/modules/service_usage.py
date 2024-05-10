from collections import namedtuple
from .transactions import TransactionFactory

import logging

logger = logging.getLogger(f'et_billing.{__name__}')
MappedTransactions = namedtuple("MappedTransactions", ["dataframe", "transactions", "fully_mapped"])
TRANSACTION_STATUS_ERROR = 5


class ServiceUsageMixin:
    """ Mixing to add functionality to calculate service usage on a given DataFrame """

    @staticmethod
    def map_transactions(df, service_filters: dict) -> MappedTransactions:
        """ Generates Transaction objects for each row in the dataframe.
            If service_filters are provided, tries to map each transaction to a service.
            :param df: Pandas dataframe from Vendor Input File
            :param service_filters: {service_id: FilterGroup} dictionary for mapping transaction based services
            :returns : named tuple ("dataframe": DataFrame, "transactions": list, "fully_mapped": bool)
        """

        try:
            transactions_list = []
            headers = df.columns.tolist()
            transactions_factory = TransactionFactory(headers)
            df['service_id'] = None
            for row in df.itertuples():
                i, data = row[0], row[1:-1]

                if data:
                    # Generate transaction from data
                    transaction = transactions_factory.gen_transaction(data)
                    transaction.service_id = None

                    # Apply filters to map service, update dataframe and transaction, and add to output
                    if service_filters:
                        filter_result = next((k for k, v in service_filters.items() if v.apply_all(transaction)), None)
                        transaction.service_id = filter_result
                        df.at[i, 'service_id'] = filter_result

                    transactions_list.append(transaction)

            fully_mapped = True
            for el in transactions_list:
                if el.transaction_status != TRANSACTION_STATUS_ERROR and el.service_id is None:
                    fully_mapped = False
                    break
            # fully_mapped = sum(df.service_id.value_counts()) == len(df)
            return MappedTransactions(dataframe=df, transactions=transactions_list, fully_mapped=fully_mapped)

        except Exception as e:
            logger.error("Error: %s", e)
            raise
