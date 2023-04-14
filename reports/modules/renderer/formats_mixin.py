import xlsxwriter
from xlsxwriter import worksheet, workbook


class FormatMixin:
    """ A mixin class to add format methods to renderer classes """

    worksheet: worksheet
    workbook: workbook

    def _apply_cell_format(self, cells_formats: tuple) -> None:
        """ Apply formats to cell or range of cells based on provided tuple.
        :param cells_formats: tuple in the format (row, col, format_name) or ((row, row, col, col), format_name).
        """

        if not cells_formats:
            return

        ws = self.worksheet
        for cell in cells_formats:

            rs, re, cs, ce, xf_format = None, None, None, None, None

            if len(cell) == 2:  # range format
                rs, re, cs, ce = cell[0]
                cell_format = cell[1]
                xf_format = self._get_format(cell_format)

            elif len(cell) == 3:  # cell format
                rs, cs, cell_format = cell
                re, ce = rs, cs
                xf_format = self._get_format(cell_format)

            for r in range(rs, re + 1):
                for c in range(cs, ce + 1):
                    ws.write_blank(r, c, None, xf_format)

    def _apply_row_sizes(self, sizes: tuple) -> None:
        """ Change row sizes based on provided tuple.
        :param sizes: tuple in the format ((row_number, row_size),)
        """

        ws = self.worksheet
        if sizes:
            for row, size in sizes:
                ws.set_row(row, size)

    def _apply_col_sizes(self, sizes: tuple) -> None:
        """ Change col size based on provided tuple.
        :param sizes: tuple in the format ((row_number, row_size),)
        """

        ws = self.worksheet
        if sizes:
            for col, size in sizes:
                ws.set_column(col, col, size)

    def _get_format(self, format_name) -> xlsxwriter.workbook.Format:
        """ Returns a xlsxwriter.workbook.Format from the child object's _wb_formats property """

        return self._wb_formats.get(format_name, None)

    def _load_formats(self, wb_formats: dict) -> None:
        """ Adds a dictionary with xlsxwriter.workbook.Format to the child object
        :param wb_formats: dictionary with objects
        """

        wb = self.workbook
        self._wb_formats = {name: wb.add_format(params) for (name, params) in wb_formats.items()}
