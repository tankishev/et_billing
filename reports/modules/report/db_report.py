from typing import List, Tuple
from services.modules import FiltersMixin, ServicesMixin
from shared.utils import DictToObjectMixin
from shared.modules import ServiceUsageMixin, InputFilesMixin
from .db_proxy import DBProxyReports

import logging

logger = logging.getLogger(f'et_billing.{__name__}')


class ReportData(DictToObjectMixin):
    """ A simple class with attributes needed to render a billing report """

    def __init__(self, **data):
        self.add_attributes(**data)


class DBReport(InputFilesMixin, FiltersMixin, ServiceUsageMixin, ServicesMixin):
    """ A class used to process and generate different data objects for the Report object """

    def __init__(self):
        self.dba = DBProxyReports()

    def close(self):
        """ Drops the temp data table and closes the DB session connection """

        self.dba.drop_temp_data_table()
        self.dba.close()

    def get_report_data(self, period: str, client_id=None, report_id=None) -> list:
        """ Returns a list with ReportData objects for given period.
        :param period: period to extract data for
        :param client_id: if not none will filter the results only for that client_id
        :param report_id: if not none will filter the results only for this report_id
        """

        logger.debug(f'Extracting report data from DB')

        # Generate temp_table
        self.dba.create_temp_data_table(period)

        # Choose the correct reports extract
        if report_id:
            report_data = self.dba.get_report_data_by_report_id(report_id)
        elif client_id:
            report_data = self.dba.get_report_data_by_client(client_id)
        else:
            report_data = self.dba.get_report_data()

        # Prepare ReportData list
        retval = []
        for data in report_data:
            report_id, file_name, report_type, language, skip_cols, details, show_pids, \
                client_id, legal_name, contract_id, contract_date = data

            render_details = details == 1
            retval.append(ReportData(**{
                'report_id': report_id,
                'file_name': file_name,
                'report_type': report_type,
                'language': language,
                'skip_cols': skip_cols,
                'render_details': render_details,
                'show_pids': show_pids,
                'client_id': client_id,
                'legal_name': legal_name,
                'contract_id': contract_id,
                'contract_date': contract_date
            }))

        logger.debug(f'Returning list with {len(retval)} ReportData object/s')
        return retval

    def get_report_order_details(self, report_id: int, report_language: str) -> list:
        """ Returns a list of Orders (BillingSummaries) to be included in the report """

        retval = []
        orders_data = self.dba.get_report_details(report_id)
        for i, order in enumerate(orders_data):
            order_id, order_descr, ccy_type, payment_type, tu_price = order
            currency = 'BGN' if ccy_type in [1, 3] else 'EUR'
            layout_name = 'regular' if tu_price == 0 else 'trust_units'
            other_services = ccy_type == 5
            service_data = self._get_report_order_services(report_id, order_id)
            retval.append((other_services, order_id, {
                'anex': order_descr,
                'tu_price': tu_price,
                'layout_name': layout_name,
                'billing_type': payment_type,
                'currency': currency,
                'language': report_language,
                'output': service_data,
                'render_output': service_data
            }))
        retval.sort(key=lambda el: el[0:2])
        return [el[-1] for el in retval]

    def get_report_transactions(self, report_id, hide_pids=True, skip_status_five=True) -> Tuple[List, bool]:
        """ Generates a list of Transactions to be rendered in the Details sheet """

        service_types = self.get_service_types_for_reports()
        vendor_files = self.dba.get_vendor_files_by_report_id(report_id)
        retval = []
        fully_mapped = True
        for file in vendor_files:
            service_filters = self.load_vendor_service_filters(file.vendor_id)
            df = self.load_data_for_service_usage(file.file.path, skip_status_five)
            mapped_transactions = self.map_transactions(df, service_filters)
            fully_mapped *= mapped_transactions.fully_mapped

            for transaction in mapped_transactions.transactions:
                service_id = transaction.service_id
                if service_id is None:
                    print(f'Vendor {file.vendor_id}: transaction {transaction.transaction_id} '
                          f'not rated (service_id = None)')
                    continue
                if hide_pids:
                    if transaction.receiver_pid != '':
                        transaction.receiver_pid = self._mask_pid(transaction.receiver_pid)
                    if transaction.sender_pid != '':
                        transaction.sender_pid = self._mask_pid(transaction.sender_pid)
                transaction.service = service_types[service_id].get('service', None)
                transaction.stype = service_types[service_id].get('stype', None)
                transaction.vendor_id = int(transaction.vendor_id)
                transaction.cost = float(transaction.cost)
                transaction.signing_type = int(transaction.signing_type)
                transaction.transaction_status = int(transaction.transaction_status)
                transaction.transaction_type = int(transaction.transaction_type)
                transaction.render_from_headers = True
                retval.append(transaction)
        return retval, fully_mapped

    def _get_report_order_services(self, report_id: int, order_id: int) -> list | None:
        """ Returns a list of services to be included for a given order (BillingSummary) """

        services_data = self.dba.get_report_order_services(report_id, order_id)
        if services_data:
            retval = []
            for el in services_data:
                _, service_group, service_type, service_descr, unit_price, skip_service_render, unit_count = el
                skip_render = skip_service_render == 1
                retval.append({
                    'service': service_group,
                    'stype': service_type,
                    'description': service_descr,
                    'unit_count': unit_count,
                    'unit_cost': unit_price,
                    'total_cost': unit_count * unit_price,
                    'skip_render': skip_render
                 })
            return retval

    @staticmethod
    def _mask_pid(pid: str) -> str:
        """ Masks the last 4 digits of an identifier by replacing them with **** """
        return f'{str(pid)[:-4]}****' if pid and len(str(pid)) in (9, 10) else pid
