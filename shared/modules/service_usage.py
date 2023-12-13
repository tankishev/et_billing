from .transactions import TransactionFactory
from collections import namedtuple

MappedTransactions = namedtuple("MappedTransactions", ["dataframe", "transactions", "fully_mapped"])


class ServiceUsageMixin:
    """ Mixing to add functionality to calculate service usage on a given DataFrame """

    @staticmethod
    def map_transactions(df, service_filters: dict) -> MappedTransactions:
        """ Maps service_filters dictionary to each row in a dataframe to calculate service usage.
            :param df: Pandas dataframe from Vendor Input File
            :param service_filters: {service_id: FilterGroup} dictionary for mapping transaction based services
            :returns : named tuple ("dataframe": DataFrame, "transactions": list, "fully_mapped": bool)
        """

        transactions_list = []
        headers = df.columns.tolist()
        transactions_factory = TransactionFactory(headers)
        df['service_id'] = None
        for row in df.itertuples():
            i, data = row[0], row[1:-1]

            if data:
                # Generate transaction from data
                transaction = transactions_factory.gen_transaction(data)

                # Apply filters to map service
                filter_result = next((k for k, v in service_filters.items() if v.apply_all(transaction)), None)

                # Update dataframe and transaction and add to output
                df.at[i, 'service_id'] = filter_result
                transaction.service_id = filter_result
                transactions_list.append(transaction)

        fully_mapped = sum(df.service_id.value_counts()) == len(df)
        return MappedTransactions(dataframe=df, transactions=transactions_list, fully_mapped=fully_mapped)
