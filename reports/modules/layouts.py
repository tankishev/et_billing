class BaseLayout:

    _CCY_SHORT_MASK = '__CCY_SHORT__'
    _CCY_LONG_MASK = '__CCY_LONG__'
    _CELL_FORMATS_KEY = 'cell_formats'
    _COLS_SIZE_KEY = 'cols_size'
    _FIELD_FORMATS_KEY = 'field_formats'
    _FIELD_FORMATS_KEY_TABLE = 'table_fields_formats'
    _LABELS_KEY = 'labels'
    _LABELS_KEY_TABLES = 'table_labels'
    _LABELED_CELLS_KEY = 'labeled_cells'
    _LAYOUT_CONFIG_KEY = 'layout_config'
    _LOGO_KEY = 'logo'
    _LOGO_FILENAME = 'logo.png'
    _LOGO_FILENAME_KEY = 'filename'
    _LOGO_LOCATION = (0, 0)
    _LOGO_LOCATION_KEY = 'logo_rc'
    _ROWS_SIZE_KEY = 'rows_size'
    _TABLE_BORDERS_KEY = 'table_borders'
    _TOP_RC_KEY = 'billing_summary_top_rc'
    _VALUE_CELLS_KEY = 'value_cells'
    _WORKBOOK_FORMATS_KEY = 'workbook_formats'

    def __init__(self, *args, **kwargs):
        self._layout = kwargs.get(self._LAYOUT_CONFIG_KEY)
        self._ccy_long = kwargs.get('ccy_long')
        self._ccy_short = kwargs.get('ccy_short')
        self.language = kwargs.get('language')

    @property
    def cell_formats(self):
        if self._layout:
            return self._layout.get(self._CELL_FORMATS_KEY)

    @property
    def cols_size(self):
        if self._layout:
            return self._layout.get(self._COLS_SIZE_KEY)

    @property
    def rows_size(self):
        if self._layout:
            return self._layout.get(self._ROWS_SIZE_KEY)

    @property
    def table_borders(self):
        return self._layout.get(self._TABLE_BORDERS_KEY)

    @property
    def top_rc(self):
        return self._layout.get(self._TOP_RC_KEY)

    @property
    def wb_formats(self):
        return self._layout.get(self._WORKBOOK_FORMATS_KEY)

    @property
    def value_cells(self):
        if self._layout:
            return self._layout.get(self._VALUE_CELLS_KEY)

    def _load_field_formats(self, fields_key):
        if self._layout:
            field_formats = self._layout.get(fields_key)
            if field_formats:
                for k, v in field_formats.items():
                    setattr(self, f'format_{k}', v)

    def _load_labels(self, labels_key):
        if self._layout:
            field_name = f'{labels_key}_{self.language.lower()}'
            labels = self._layout.get(field_name, labels_key)
            if labels:
                for k, v in labels.items():
                    v = self._replace_ccy(v)
                    setattr(self, f'label_{k}', v)

    def _replace_ccy(self, el):
        if type(el) == tuple:
            retval = []
            for label in el:
                if self._CCY_LONG_MASK in label:
                    label = label.replace(self._CCY_LONG_MASK, self._ccy_long)
                elif self._CCY_SHORT_MASK in label:
                    label = label.replace(self._CCY_SHORT_MASK, self._ccy_short)
                retval.append(label)
            return tuple(retval)

        if self._CCY_LONG_MASK in el:
            el = el.replace(self._CCY_LONG_MASK, self._ccy_long)
        elif self._CCY_SHORT_MASK in el:
            el = el.replace(self._CCY_SHORT_MASK, self._ccy_short)
        return el


class DBReportingLayout(BaseLayout):

    def __init__(self, *args, **kwargs):
        super(DBReportingLayout, self).__init__(*args, **kwargs)

        load_tables = kwargs.get('load_tables', False)
        if self._layout is not None:
            if load_tables:
                self._load_labels(self._LABELS_KEY_TABLES)
                self._load_field_formats(self._FIELD_FORMATS_KEY_TABLE)
            else:
                self._load_labels(self._LABELS_KEY)
                self._load_field_formats(self._FIELD_FORMATS_KEY)

    @property
    def labeled_cells(self):
        if self._layout:
            return self._layout.get(self._LABELED_CELLS_KEY)

    @property
    def logo_filename(self):
        if self._layout:
            logo = self._layout.get(self._LOGO_KEY)
            if logo:
                return logo.get(self._LOGO_FILENAME_KEY, self._LOGO_FILENAME)

    @property
    def logo_location(self):
        if self._layout:
            logo = self._layout.get(self._LOGO_KEY)
            if logo:
                return logo.get(self._LOGO_LOCATION_KEY, self._LOGO_LOCATION)


class LayoutFactory:

    _LAYOUT_CONFIG_KEY = 'layout_config'

    def __init__(self, layout_config: dict, new_layout=False):
        self.layout_config = layout_config
        self._new_layout = new_layout

    def get_layout(self, *args, **kwargs):
        kwargs[self._LAYOUT_CONFIG_KEY] = self.layout_config
        return DBReportingLayout(*args, **kwargs)
