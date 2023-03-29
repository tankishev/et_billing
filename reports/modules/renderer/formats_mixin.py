from xlsxwriter import worksheet, workbook


class FormatMixin:
    worksheet: worksheet
    workbook: workbook

    def _apply_cell_format(self, cells_formats: tuple):
        """
        Apply formats to cell or range of cells
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

    def _apply_row_sizes(self, sizes: tuple):
        """
        Change row size
        :param sizes: tuple in the format ((row_number, row_size),)
        """
        ws = self.worksheet
        if sizes:
            for row, size in sizes:
                ws.set_row(row, size)

    def _apply_col_sizes(self, sizes: tuple):
        """
        Change col size
        :param sizes: tuple in the format ((row_number, row_size),)
        """
        ws = self.worksheet
        if sizes:
            for col, size in sizes:
                ws.set_column(col, col, size)

    def _get_format(self, format_name):
        return self._wb_formats.get(format_name, None)

    def _load_formats(self, wb_formats):
        wb = self.workbook
        self._wb_formats = {name: wb.add_format(params) for (name, params) in wb_formats.items()}
