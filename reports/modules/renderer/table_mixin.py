from .formats_mixin import FormatMixin


class TableRenderMixin:
    """ Interface for rendering tables in report """

    @staticmethod
    def _get_table(**kwargs):
        """ Returns the correct table class depending on billing type """

        billing_type = kwargs.get('billing_type')

        if billing_type == 'prepaid':
            return PrepaidTable(**kwargs)
        elif billing_type == 'prepaid_shared':
            return PrepaidTableShared(**kwargs)
        elif billing_type == 'invoice':
            return InvoiceTable(**kwargs)
        elif billing_type == 'subscription':
            return SubscriptionTable(**kwargs)
        elif billing_type == 'users_summary':
            return UsersSummaryTable(**kwargs)


class BaseTableRenderer(FormatMixin):

    _DATA_COLS = ('service', 'stype', 'description', 'unit_count', 'unit_cost')
    _ROWS_BETWEEN_TABLES = 2
    _TABLE_TOP_ROWS_NUM = 6
    _TABLE_FOOTER_ROWS_NUM = 2
    _XL_COLS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']

    def __init__(self, **kwargs):
        self.t_row = kwargs.get('t_row')
        self.t_col = kwargs.get('t_col')
        self.worksheet = kwargs.get('ws')
        self.workbook = kwargs.get('wb')
        self.layout = kwargs.get('layout')

    def render_table(self, summary, *args, **kwargs) -> int:
        report = args[0]
        self._load_formats(self.layout.wb_formats)
        num_data_cols = len(getattr(self.layout, f'label_table_headers_{summary.layout_name}', []))
        start_col = self.t_col + 1
        end_col = self.t_col + num_data_cols

        # Apply formats
        self._apply_base_table_formats(summary, num_data_cols)

        # Write title
        self._write_title(summary, self.t_row + 1, start_col)

        # Write headers
        self._write_headers(summary, self.t_row + 1, start_col)

        # Write data
        start_data_row = self.t_row + 1
        self._write_data(summary, start_data_row, start_col)

        # Write total row
        self._write_total_row(summary, start_data_row, self.t_row - 1, self.t_row + 1, end_col)

        # Write table footer
        self._write_extended_rows(summary, end_col, report)

        return self.t_row + self._ROWS_BETWEEN_TABLES + 1

    def _apply_base_table_formats(self, summary, num_data_cols):
        border_sm = self.layout.table_borders.get('small')
        border_lg = self.layout.table_borders.get('large')
        border_v = self.layout.table_borders.get('vertical')

        dr = len(summary.render_output)
        re = self.t_row + self._TABLE_TOP_ROWS_NUM + dr + self._TABLE_FOOTER_ROWS_NUM
        end_col = self.t_col + num_data_cols

        self._apply_row_sizes((
            (self.t_row, border_lg),
            (self.t_row + 3, border_sm),
            (self.t_row + 5, border_sm),
            (self.t_row + self._TABLE_TOP_ROWS_NUM + dr, border_sm)
        ))
        self._apply_col_sizes(((end_col + 1, border_v),))
        self._apply_cell_format(
            (((self.t_row, re, self.t_col, end_col + 1), self.layout.format_table_borders),)
        )

    def _write_title(self, summary, row, start_col):
        ws = self.worksheet
        xl_title_format = self._get_format(self.layout.format_table_titles)
        ws.write_string(row, start_col, summary.anex, xl_title_format)
        row += 1
        table_title_field = self._get_title_field(summary)
        table_title = getattr(self.layout, table_title_field)
        ws.write_string(row, start_col, table_title, xl_title_format)
        self.t_row = row + 1

    def _write_headers(self, summary, row, start_col, align_left_cols=3, cols_to_skip=()):
        ws = self.worksheet
        table_headers_field = f'label_table_headers_{summary.layout_name}'
        table_headers = getattr(self.layout, table_headers_field)
        for i, heading in enumerate(table_headers):
            if i in cols_to_skip:
                continue
            if i < align_left_cols:
                xl_format = self._get_format(self.layout.format_table_headers)
            else:
                xl_format = self._get_format(self.layout.format_table_headers_right)
            ws.write_string(row, start_col + i, heading, xl_format)
        self.t_row = row + 1

    def _write_data(self, summary, start_row, start_col):
        xl_format_str = self._get_format(self.layout.format_table_labels)
        xl_format_int = self._get_format(self.layout.format_table_values_int)
        xl_format_float_ext = self._get_format(self.layout.format_table_values_float_ext)
        xl_format_float = self._get_format(self.layout.format_table_values_float)
        for el in [xl_format_float, xl_format_float_ext, xl_format_int]:
            el.set_align('top')

        formats = {
            'str': xl_format_str,
            'int': xl_format_int,
            'float_ext': xl_format_float_ext,
            'float': xl_format_float
        }

        for line_item in summary.output:
            data = [line_item[el] for el in self._DATA_COLS]
            if line_item['skip_render']:
                continue
            self._write_data_row(data, formats, start_row, start_col)
            start_row += 1
        self.t_row = start_row

    def _write_data_row(self, data, formats, row, start_col):
        ws = self.worksheet
        for i, value in enumerate(data):
            if type(value) == str:
                ws.write_string(row, start_col + i, value, formats['str'])
            elif type(value) == float:
                ws.write_number(row, start_col + i, value, formats['float_ext'])
            elif type(value) == int:
                ws.write_number(row, start_col + i, value, formats['int'])

        n = len(data)
        total_col = start_col + n
        xl_units_col = self._XL_COLS[start_col + n - 2]
        xl_cost_col = self._XL_COLS[start_col + n - 1]

        xl_formula = f'=ROUND({xl_units_col}{row + 1}*{xl_cost_col}{row + 1}, 2)'
        ws.write_formula(
            row, total_col, xl_formula, formats['float'])

    def _write_total_row(self, summary, from_row, to_row, total_row, total_col):
        ws = self.worksheet

        self._apply_cell_format(
            (((total_row, total_row, self.t_col + 1, total_col), self.layout.format_total_row_labels),)
        )
        total_row_label_field = self._get_footer_total_field(summary)
        total_row_label = getattr(self.layout, total_row_label_field)
        ws.write_string(
            total_row, total_col - 1, total_row_label, self._get_format(self.layout.format_total_row_labels))
        xl_total_col = self._XL_COLS[total_col]
        xl_formula = f'=SUM({xl_total_col}{from_row + 1}:{xl_total_col}{to_row + 1})'
        ws.write_formula(
            total_row, total_col, xl_formula, self._get_format(self.layout.format_total_row_values))
        self.t_row = total_row + 1

    def _write_extended_rows(self, summary, end_col, *args, **kwargs):
        pass

    @staticmethod
    def _get_title_field(summary):
        return f'label_table_title_{summary.billing_type}'

    @staticmethod
    def _get_footer_total_field(summary):
        return f'label_footer_{summary.layout_name}_{summary.billing_type}'


class InvoiceTable(BaseTableRenderer):

    def _write_extended_rows(self, summary, end_col, *args, **kwargs):
        report = args[0]

        if summary.layout_name == 'trust_units':
            tu_price = summary.tu_price
            self._write_extended_rows_tu(tu_price, end_col)

        if report.client.country.code == 'BG' and summary.currency != 'BGN':
            label = self.layout.label_footer_regular_invoice_bgn
            self._write_extended_rows_ccy_bgn(end_col, label)

        border_lg = self.layout.table_borders.get('large')
        self._apply_row_sizes(((self.t_row, border_lg),))

    def _write_extended_rows_tu(self, tu_price, end_col):
        """ Adds fiat amount rows for invoice table in TUs"""

        # Apply formats
        ws = self.worksheet
        xl_labels_right = self._get_format(self.layout.format_table_labels_right)
        xl_values_float = self._get_format(self.layout.format_table_values_float)
        r, c = self.t_row, self.t_col
        re = self.t_row + 2
        self._apply_cell_format(
            (((self.t_row, re, self.t_col, end_col + 1), self.layout.format_table_borders),)
        )

        # Add TU price row
        ws.write_string(r, end_col - 1, self.layout.label_footer_trust_units_price, xl_labels_right)
        ws.write_number(r, end_col, tu_price, xl_values_float)

        # Add invoice amount row
        r += 1
        xl_col = self._XL_COLS[end_col]
        xl_formula = f'={xl_col}{r}*{xl_col}{r - 1}'
        ws.write_string(r, end_col - 1, self.layout.label_footer_regular_invoice, xl_labels_right)
        ws.write_formula(r, end_col, xl_formula, xl_values_float)

        # Update last used row
        self.t_row = re

    def _write_extended_rows_ccy_bgn(self, end_col, label):
        """ Adds one additional row with value in BGN if report is in EUR and company is registered in BG """

        # Apply formats
        r = self.t_row
        re = self.t_row + 1
        self._apply_cell_format(
            (((self.t_row, re, self.t_col, end_col + 1), self.layout.format_table_borders),)
        )

        # Add invoice amount row
        ws = self.worksheet
        xl_labels_right = self._get_format(self.layout.format_table_labels_right)
        xl_values_float = self._get_format(self.layout.format_table_values_float)

        xl_col = self._XL_COLS[end_col]
        xl_formula = f'={xl_col}{r}*1.95583'
        ws.write_string(r, end_col - 1, label, xl_labels_right)
        ws.write_formula(r, end_col, xl_formula, xl_values_float)

        # Update last used row
        self.t_row = re


class PrepaidTable(BaseTableRenderer):

    def _write_extended_rows(self, summary, end_col, *args, **kwargs):
        border_lg = self.layout.table_borders.get('large')
        ws = self.worksheet
        xl_labels_right = self._get_format(self.layout.format_table_labels_right)
        xl_values_float = self._get_format(self.layout.format_table_values_float)
        r, c = self.t_row, self.t_col

        re = 4 if summary.layout_name == 'trust_units' else 2
        re += self.t_row

        self._apply_cell_format(
            (((self.t_row, re, self.t_col, end_col + 1), self.layout.format_table_borders),)
        )
        self._apply_row_sizes(((re, border_lg),))

        ws.write_string(r, end_col - 1, self.layout.label_period_start, xl_labels_right)
        ws.write_number(r, end_col, 0, xl_values_float)

        r += 1
        xl_col = self._XL_COLS[end_col]
        xl_formula = f'={xl_col}{r}-{xl_col}{r - 1}'
        ws.write_string(r, end_col - 1, self.layout.label_period_end, xl_labels_right)
        ws.write_formula(r, end_col, xl_formula, xl_values_float)

        if summary.layout_name == 'trust_units':
            r += 1
            ws.write_string(r, end_col - 1, self.layout.label_footer_trust_units_price, xl_labels_right)
            ws.write_number(r, end_col, summary.tu_price, xl_values_float)

            r += 1
            xl_col = self._XL_COLS[end_col]
            xl_formula = f'={xl_col}{r}*{xl_col}{r - 3}'
            label = self.layout.label_footer_trust_units_prepaid_value
            ws.write_string(r, end_col - 1, label, xl_labels_right)
            ws.write_formula(r, end_col, xl_formula, xl_values_float)

        self.t_row = re


class PrepaidTableShared(BaseTableRenderer):

    def _write_extended_rows(self, summary, end_col, *args, **kwargs):
        border_lg = self.layout.table_borders.get('large')
        self._apply_row_sizes(((self.t_row, border_lg),))

    @staticmethod
    def _get_title_field(summary):
        return 'label_table_title_prepaid'

    @staticmethod
    def _get_footer_total_field(summary):
        return f'label_footer_{summary.layout_name}_prepaid'


class SubscriptionTable(BaseTableRenderer):

    _DATA_COLS = ('service', 'stype', 'description', 'unit_count')
    _TABLE_FOOTER_ROWS_NUM = 0

    def render_table(self, summary, *args, **kwargs) -> int:
        self._load_formats(self.layout.wb_formats)
        start_col = self.t_col + 1

        # Apply formats
        self._apply_base_table_formats(summary, 4)

        # Write title
        self._write_title(summary, self.t_row + 1, start_col)

        # Write headers
        self._write_headers(summary, self.t_row + 1, start_col, cols_to_skip=(4, 5))

        # Write data
        start_data_row = self.t_row + 1
        self._write_data(summary, start_data_row, start_col)

        # Write total row
        border_lg = self.layout.table_borders.get('large')
        self._apply_row_sizes(((self.t_row, border_lg),))

        return self.t_row + self._ROWS_BETWEEN_TABLES + 1

    def _write_data_row(self, data, formats, row, start_col):
        ws = self.worksheet
        for i, value in enumerate(data):
            if type(value) == str:
                ws.write_string(row, start_col + i, value, formats['str'])
            elif type(value) == int:
                ws.write_number(row, start_col + i, value, formats['int'])


class UsersSummaryTable(BaseTableRenderer):
    pass
