# CODE OK
from django.conf import settings
from django.core.files import File
from reports.models import ReportFile
from .table_mixin import TableRenderMixin, FormatMixin

import xlsxwriter
import tempfile
import os
import logging

logger = logging.getLogger('et_billing.report.renderer')


class BaseReportRenderer(FormatMixin):
    """ A base report renderer class """

    def __init__(self):
        self._wb = None
        self._ws = None
        self._wb_formats = None

    @property
    def workbook(self):
        return self._wb

    @workbook.setter
    def workbook(self, value):
        self._wb = value

    @property
    def worksheet(self):
        return self._ws

    @worksheet.setter
    def worksheet(self, value):
        self._ws = value


class ReportRenderer(TableRenderMixin, BaseReportRenderer):
    """ A class for rendering XLSX file from a Report object """

    _DETAILS_COLUMN_HEADERS = [
        'Date created', 'VendorID', 'Vendor name', 'ThreadID', 'TransactionID',	'GroupTransactionID', 'Description',
        'Country sender', 'PID sender', 'Names sender', 'Country receiver', 'PID receiver', 'Names receiver', 'Type',
        'Status', 'Signing type', 'Cost EUR', 'Payer', 'Bio ID', 'Service', 'Type'
    ]
    _DETAILS_FLOAT_COLS = ['Cost', 'Cost EUR']
    _DETAILS_SHEET_NAME = 'Details'
    _RESOURCES_DIR = 'resources/'
    _TOTAL_SHEET_NAME = 'Summary'

    def __init__(self):
        super(ReportRenderer, self).__init__()
        self.t_row = 0
        self.t_col = 0
        self._resources_dir = str(settings.MEDIA_ROOT / self._RESOURCES_DIR)

    def close_workbook(self) -> None:
        """ Closes the XLSX file """

        if self._wb:
            self._wb.close()

    def render(self, report, **kwargs) -> ReportFile | None | str:
        """ Creates XLSX file and renders data in it given a Report object.
        :param report: Report object
        """

        logger.info(f'Rendering report {report.output_file_name}')

        if report.layout.wb_formats:
            logger.debug(f'Creating temp file for {report.output_file_name}')
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                wb = xlsxwriter.Workbook(temp_file.name)
                self._ws = wb.add_worksheet(self._TOTAL_SHEET_NAME)
                self._wb = wb

                with_details = kwargs.get('with_details', False)

                # Load formats
                if not report.layout.wb_formats:
                    logger.critical('Workbook formats missing')
                    return 'workbook formats missing'
                self._load_formats(report.layout.wb_formats)
                self.t_row, self.t_col = report.layout.top_rc

                # Render data
                logger.debug('Rendering data in temp file')
                self._render_header(report)
                self._render_tables(report)
                if with_details:
                    self._render_details(report)
                self.close_workbook()

            logger.debug(f'Temp file created')
            period = kwargs.get('period')
            report_id = report.report_id
            filename = report.output_file_name

            file_obj = open(temp_file.name, 'rb')
            django_file = File(file_obj, name=filename)
            django_file.seek(0)
            report_file = None
            try:
                report_file = ReportFile.objects.get(period=period, report_id=report_id, type_id=1)
                if report_file.file:
                    os.remove(report_file.file.path)
                logger.debug(f'Replacing existing ReportFile object for report_id {report_id}, period {period}')
                report_file.file.save(filename, django_file, save=True)

            except ReportFile.DoesNotExist:
                logger.debug(f'Saving ReportFile object for report_id {report_id}, period {period}')
                report_file = ReportFile.objects.create(
                    period=period, file=django_file, report_id=report.report_id, type_id=1)
                report_file.save()

            finally:
                file_obj.close()
                os.remove(temp_file.name)
                return report_file

        logger.warning(f'Cannot render report_id {report.report_id}. '
                       f'ReportFile object does not contain formats. {report.output_file_name}')

    def _render_details(self, report) -> None:
        """ Render Details sheet in an XLSX report.
        :param report: Report object
        """

        logger.debug(f'Rendering details')

        ws = self._wb.add_worksheet(self._DETAILS_SHEET_NAME)
        xl_format_headers = self._get_format(report.layout.format_table_titles)
        xl_format_int = self._get_format(report.layout.format_details_int)
        xl_format_float = self._get_format(report.layout.format_details_float)

        float_cols = []
        skipped = 0
        for col, column_name in enumerate(self._DETAILS_COLUMN_HEADERS):
            if col in report.columns_to_skip:
                skipped += 1
                continue
            if column_name in self._DETAILS_FLOAT_COLS:
                float_cols.append(col)
            ws.write_string(0, col - skipped, column_name, xl_format_headers)

        for row, data in enumerate(report.transactions):

            if data.render_from_headers is False:
                render_data = data.all_data
            else:
                render_data = [getattr(data, el, None) for el in data.headers]

            skipped_cols = 0
            for col, value in enumerate(render_data):
                if col in report.columns_to_skip:
                    skipped_cols += 1
                    continue
                if type(value) == int:
                    ws.write_number(row + 1, col - skipped_cols, value, xl_format_int)
                elif type(value) == float:
                    float_format = xl_format_float if col in float_cols else xl_format_int
                    ws.write_number(row + 1, col - skipped_cols, value, float_format)
                else:
                    ws.write_string(row + 1, col - skipped_cols, value)

                ws.write_string(row + 1, col + 1 - skipped_cols, data.service)
                if data.stype:
                    ws.write_string(row + 1, col + 2 - skipped_cols, data.stype)

    def _render_header(self, report) -> None:
        """ Render the header in the Summary sheet of the XLSX report.
        :param report: Report object
        """

        logger.debug('Rendering headers')

        layout = report.layout
        ws = self._ws

        if layout and ws:

            self._apply_cell_format(layout.cell_formats)
            self._apply_row_sizes(layout.rows_size)
            self._apply_col_sizes(layout.cols_size)

            if layout.logo_filename is not None:
                row, col = layout.logo_location
                path = os.path.join(self._resources_dir, layout.logo_filename)
                path.strip()
                logger.debug(f'{self._resources_dir}, {path}')
                ws.insert_image(row, col, path)
                if len(report.transactions) != 0 and report.is_reconciled is False:
                    self._apply_cell_format((((row, row, col, col + 6), 'bold-warning'),))

            if layout.labeled_cells:
                for cell in layout.labeled_cells:
                    label_name, row, col = cell
                    label = getattr(layout, f'label_{label_name}')
                    xl_format = self._get_format(layout.format_header_label)
                    ws.write_string(row, col, label, xl_format)

            if layout.value_cells:
                contract_date = [el for el in report.client_data.contract_date.split('-')]
                contract_date.reverse()
                data_to_render = {
                    'client_name': report.client.legal_name,
                    'reporting_period': report.reporting_period.get('period'),
                    'contract_date': '.'.join(contract_date)
                }
                for field, value in data_to_render.items():
                    if field in layout.value_cells:
                        row, col = layout.value_cells.get(field)
                        if type(value) != str:
                            value = str(value)
                        ws.write_string(row, col, value, self._get_format(layout.format_header_values))

    def _render_tables(self, report) -> None:
        """ Renders a table for each billing summary in the given report object.
        :param report: Report object
        """

        logger.debug(f'Rendering tables')

        init_kwargs = {
            'wb': self._wb,
            'ws': self._ws,
            'layout': report.layout
        }

        for summary in report.billing_summaries:
            summary_layout = getattr(summary, 'layout', None)
            if summary_layout is not None:
                init_kwargs.update({'layout': summary_layout})

            init_kwargs.update({
                't_row': self.t_row,
                't_col': self.t_col,
                'billing_type': summary.billing_type
            })

            table = self._get_table(**init_kwargs)
            self.t_row = table.render_table(summary, report)
