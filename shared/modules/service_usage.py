# CODE OK
from .transactions import TransactionFactory


class ServiceUsageMixin:
    """ Mixing to add functionality to calculate service usage """
    def calc_usage(self, df, services):
        df, _, is_reconciled = self._calc_usage(df, services)
        return df, is_reconciled

    def calc_transactions(self, df, services):
        _, transactions, res = self._calc_usage(df, services)
        return transactions, res

    @staticmethod
    def _calc_usage(df, services) -> tuple:
        """ Maps services dictionary to each row in a dataframe to calculate service usage.
            :param df: Pandas dataframe from Vendor Input File
            :param services: dictionary with filters for mapping transaction based services
            :returns tuple: dataframe, list of transactions, boolean if all transactions were mapped
        """

        transactions = []
        headers = df.columns.tolist()
        trans_f = TransactionFactory(headers)
        df['service_id'] = None
        for row in df.itertuples():
            i, data = row[0], row[1:-1]

            if data:
                # Generate transaction from data
                trans = trans_f.gen_transaction(data)

                # Apply filters and save service
                filter_result = next((k for k, v in services.items() if v.apply_all(trans)), None)
                df.at[i, 'service_id'] = filter_result

                # Update transaction and add to output
                trans.service_id = filter_result
                transactions.append(trans)

        res = df.service_id.value_counts()
        return df, transactions, sum(res) == len(df)
