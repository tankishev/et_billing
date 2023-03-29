class ReportClient:
    """ A basic class to structure client data for ReportRenderer """
    def __init__(self, client_name, client_id, contract_date):
        self.client_name = client_name
        self.client_id = client_id
        self.contract_date = contract_date


class Report:
    """ A basic class to structure report data for ReportRenderer """

    def __init__(self, **kwargs):
        self.client_data = kwargs.get('client_data')
        self.client = kwargs.get('client')
        self.billing_summaries = kwargs.get('billing_summaries')
        self.report_language = kwargs.get('data.language')
        self.reporting_period = kwargs.get('reporting_period')
        self.columns_to_skip = kwargs.get('columns_to_skip')
        self.output_file_name = kwargs.get('output_file_name')
        self.layout = kwargs.get('layout')
        self.transactions = kwargs.get('transactions')
        self.is_reconciled = kwargs.get('is_reconciled')
        self.report_id = kwargs.get('report_id')
