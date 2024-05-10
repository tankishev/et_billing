from celery import current_task
from celery_tasks.models import FileProcessingTask

from reports.models import Client
from .bililng_summary import BillingSummary
from .utils import ReportClient, Report

from datetime import timedelta as td, datetime as dt

import logging

logger = logging.getLogger(f'et_billing.{__name__}')


class DBReportFactory:
    """ A class that generates usage reports """

    def __init__(self, period: str, db_report, layout_factory, renderer) -> None:
        """ Class that generates billing reports

        :param period: period for which the reports are generated (e.g. '2023-01')
        :param db_report: a DBReport object used to access complex queries
        :param renderer: a ReportRenderer object used to render the reports
        """
        self.period = period
        self.dbr = db_report
        self._layout_factory = layout_factory
        self._renderer = renderer
        self._reporting_period = self._calc_period()
        self.services = self.dbr.get_service_types_for_reports()

    def close(self) -> None:
        self.dbr.close()

    def generate_report_by_client(self, client_id: int):
        """ Generates all reports for a given client """

        report_data = self.dbr.get_reports_data(self.period, client_id=client_id)
        if len(report_data) > 0:
            self.generate_reports(report_data)
        else:
            message = f'No report data for client {client_id} for {self.period}'
            mark_task_failed(current_task.request.id, message)

    def generate_report_by_report_id(self, report_id: int):
        """ Generates a specific report given its report_id """

        report_data = self.dbr.get_report_data(self.period, report_id=report_id)
        if len(report_data) > 0:
            self.generate_reports(report_data)
        else:
            message = f'No report data for report_id {report_id} for {self.period}'
            mark_task_failed(current_task.request.id, message)

    def generate_reports(self, report_data=None):
        """ Generates a specific report given its DB data or all reports if report_data is None """

        logger.debug(f'Starting report/s generation')

        if report_data is None:
            report_data = self.dbr.get_report_data(self.period)

        if report_data is None or len(report_data) < 1:
            message = f'No report data for for {self.period}'
            mark_task_failed(current_task.request.id, message)
        else:
            retval = []

            # Get the number of reports
            number_of_reports = len(report_data)
            logger.info(f'Reports to generate: {number_of_reports}')

            # Get task to be updated
            task_id = current_task.request.id
            logger.debug(f'Updating queued task {task_id}')
            task_status = FileProcessingTask.objects.get(task_id=task_id)
            task_status.number_of_files = number_of_reports
            task_status.save()

            # Cycle through records and generate reports
            for i, data in enumerate(report_data):
                if data.report_type is not None:

                    # Generate report object
                    report = self._generate_report_obj(data)
                    with_details = data.render_details

                    # Render report and save to ReportFile
                    report_file = self._renderer.render(report, with_details=with_details, period=self.period)
                    retval.append(report_file)

                    # Update celery task
                    progress = min(100 * i // number_of_reports, 100)
                    self._update_task_status(task_status, progress, report_file)

                    logger.info(f'{report_file.filename} - Complete')

            # Mark task as complete
            logger.debug(f'Marking task {task_id} as COMPLETE')
            task_status.progress = 100
            task_status.status = 'COMPLETE'
            task_status.save()

    # Private methods used to generate Report
    def _generate_report_obj(self, data) -> Report:
        """ Generates Report object from DBReport data """

        logger.debug(f'Generating Report object for client_id {data.client_id}')
        client_data = ReportClient(data.legal_name, data.client_id, data.contract_date)
        client = Client.objects.get(client_id=data.client_id)
        output_file_name = self._get_output_filename(data)
        reporting_period = self._calc_period()
        layout = self._layout_factory.get_layout(language=data.language)
        billing_summaries = self._generate_summaries(data.report_id, data.language)
        columns_to_skip = tuple(int(el) for el in data.skip_cols.split(','))
        hide_pids = data.show_pids == 0
        transactions, is_reconciled = self.dbr.get_report_transactions(data.report_id, hide_pids)

        return Report(**{
            'client_data': client_data,
            'client': client,
            'billing_summaries': billing_summaries,
            'report_language': data.language,
            'reporting_period': reporting_period,
            'columns_to_skip': columns_to_skip,
            'output_file_name': output_file_name,
            'layout': layout,
            'transactions': transactions,
            'is_reconciled': is_reconciled,
            'report_id': data.report_id
        })

    def _generate_summaries(self, report_id, language) -> list:
        """ Generates a list of BillingSummaries for the report """

        summaries = []
        orders_data = self.dbr.get_report_order_details(report_id, language)
        for orders_details in orders_data:
            order_summary = BillingSummary(**orders_details)
            order_summary.load_layout(self._layout_factory)
            summaries.append(order_summary)
        return summaries

    # Private utility methods
    def _calc_period(self):
        start_dt = dt.strptime(self.period, '%Y-%m')
        year = start_dt.year
        month = (start_dt.month + 1) % 12
        month = 12 if month == 0 else month
        year = year + 1 if month == 1 else year
        next_month = dt.strptime(f'{year}-{month}', '%Y-%m')
        end_dt = next_month - td(days=1)
        return {'period': f'{start_dt.strftime("%d.%m.%Y")} - {end_dt.strftime("%d.%m.%Y")}'}

    def _get_output_filename(self, data) -> str:
        return f'{data.file_name}_{self._get_period()}.xlsx'

    def _get_period(self, dir_format=False) -> str:
        if dir_format:
            return f'{self.period[0:4]}-{self.period[5:]}'
        return f'{self.period[0:4]}{self.period[5:]}'

    @staticmethod
    def _update_task_status(task_status, progress, report_file):
        """ Update the details for the task """

        task_status.progress = progress
        task_status.processed_documents.append({
            'fileName': report_file.filename,
            'resultCode': 0,
            'resultText': 'Complete',
            'fileId': report_file.id
        })
        task_status.save()


def mark_task_failed(task_id, message):
    logger.warning(message)
    task_status = FileProcessingTask.objects.get(task_id=task_id)
    task_status.status = 'FAILED'
    task_status.note = message
    task_status.progress = 100
    task_status.save()
