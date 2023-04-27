# CODE OK
from shared.utils import DictToObjectMixin


class KwargsTransaction(DictToObjectMixin):
    """ Simple class mapping dictionary values to transaction object """

    def __init__(self, all_data, **kwargs):
        self.all_data = all_data
        self.render_from_headers = False
        self.processed = False
        self.add_attributes(**kwargs)


class TransactionFactory:
    """ A simple class to generate KwargsTransactions """

    _HEADERS_MAP = {
        'Date created': 'date_created',
        'Vendor ID': 'vendor_id',
        'Vendor name': 'vendor_name',
        'ThreadID': 'thread_id',
        'TransactionID': 'transaction_id',
        'GroupTransactionID': 'group_transaction_id',
        'Description': 'description',
        'Country sender': 'sender_country',
        'PID sender': 'sender_pid',
        'Names sender': 'sender_names',
        'Country receiver': 'receiver_country',
        'PID receiver': 'receiver_pid',
        'Names receiver': 'receiver_names',
        'Type': 'transaction_type',
        'Status': 'transaction_status',
        'Signing type': 'signing_type',
        'Cost': 'cost',
        'Payer': 'payer',
        'Cost EUR': 'cost',
        'Bio required': 'bio',
    }

    def __init__(self, headers):
        self.headers = headers

    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, headers_list):
        self._headers = [self._HEADERS_MAP.get(el) for el in headers_list]

    def gen_transaction(self, data):
        """ Generate KwargsTransaction from the given data """

        headers = self.headers
        if len(data) == len(headers):
            init_kwargs = {headers[i]: el for i, el in enumerate(data)}
            init_kwargs['headers'] = headers
            return KwargsTransaction(data, **init_kwargs)
