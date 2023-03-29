from .transactions import TransactionFactory


class ServiceUsageMixin:

    def calc_usage(self, df, services):
        df, _, is_reconciled = self._calc_usage(df, services)
        return df, is_reconciled

    def calc_transactions(self, df, services):
        _, transactions, res = self._calc_usage(df, services)
        return transactions, res

    @staticmethod
    def _calc_usage(df, services):
        transactions = []
        headers = df.columns.tolist()
        trans_f = TransactionFactory(headers)
        df['service_id'] = None
        for row in df.itertuples():
            i, data = row[0], row[1:-1]
            if data:
                trans = trans_f.gen_transaction(data)
                filter_result = next((k for k, v in services.items() if v.apply_all(trans)), None)
                df.at[i, 'service_id'] = filter_result
                trans.service_id = filter_result
                transactions.append(trans)

        res = df.service_id.value_counts()
        return df, transactions, sum(res) == len(df)
