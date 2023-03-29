layout = {
    'field_formats': {
        'header_title': 'bold',
        'header_label': 'bold',
        'header_values': 'align-left',
        'warning': 'bold-warning',
        'details_int': 'number-int',
        'details_float': 'number-float',
        'table_titles': 'billing-label'
    },
    'table_fields_formats': {
        'table_borders': 'billing-border',
        'table_titles': 'billing-label',
        'table_headers': 'billing-header',
        'table_headers_right': 'billing-header-right',
        'table_labels': 'billing-label-wrapped',
        'table_labels_right': 'billing-label-right',
        'table_values_int': 'billing-int',
        'table_values_float': 'billing-float',
        'table_values_float_ext': 'billing-float-extended',

        'total_row_values': 'billing-float-underlined',
        'total_row_labels': 'billing-label-right-underlined',
    },
    'labels_bg': {
        'header_title': 'МЕСЕЧЕН ОТЧЕТ ЗА ПРЕДОСТАВЕНИ УСЛУГИ',
        'header_period': 'Отчетен период:',
        'header_client': 'Клиент:',
        'header_contract_date': 'Договор от дата:',
    },
    'table_labels_bg': {
        'table_headers_regular': ('Услуга', 'Тип', 'Описание', 'Бр.', 'Ед. цена __CCY_SHORT__', 'Обща цена'),
        'table_headers_trust_units': ('Услуга', 'Тип', 'Описание', 'Бр.', 'TU/бр.', 'Общо TU '),
        'table_title_invoice': 'СПРАВКА ПО ФАКТУРА',
        'table_title_prepaid': 'СПРАВКА ПО ПРЕДПЛАТЕН ПАКЕТ',
        'table_title_subscription': 'СПРАВКА ПО АБОНАМЕНТНА УСЛУГА',

        'footer_regular_invoice': 'Сума за фактуриране, __CCY_LONG__ (без ДДС):',
        'footer_regular_invoice_bgn': 'Сума за фактуриране, лева (без ДДС):',
        'footer_regular_prepaid': 'Изразходвана предплатена стойност, __CCY_LONG__ (без ДДС):',
        'footer_regular_subscription': '',
        'footer_trust_units_invoice': 'TU за фактуриране, бр.:',
        'footer_trust_units_prepaid': 'Изразходвани TUs за периода, бр.:',
        'footer_trust_units_prepaid_value': 'Стойност на изразходвани TUs, __CCY_LONG__ (без ДДС):',
        'footer_trust_units_price': 'Цена на TU, __CCY_LONG__ (без ДДС):',
        'period_start': 'Остатък към началото на периода:',
        'period_end': 'Остатък към края на периода:'
    },
    'labels_en': {
        'header_title': 'MONTHLY SERVICES USAGE REPORT',
        'header_period': 'Reporting period:',
        'header_client': 'Client:',
        'header_contract_date': 'Contract date:',
    },
    'table_labels_en': {
        'table_headers_regular': ('Services', 'Type', 'Description', 'Units', 'Unit cost __CCY_SHORT__', 'Total price'),
        'table_headers_trust_units': ('Services', 'Type', 'Description', 'Units', 'TU/unit', 'TUs spent'),
        'table_title_invoice': 'INVOICE BREAKDOWN',
        'table_title_prepaid': 'PREPAID PACKAGE REPORT',
        'table_title_subscription': 'SUBSCRIPTION PACKAGE REPORT',

        'footer_regular_invoice': 'Total invoice amount, __CCY_LONG__ (w/o VAT):',
        'footer_regular_invoice_bgn': 'Total invoice amount, BGN (w/o VAT):',
        'footer_regular_prepaid': 'Utilized prepaid credit amount, __CCY_LONG__ (w/o VAT):',
        'footer_regular_subscription': '',
        'footer_trust_units_invoice': 'TUs to be invoiced:',
        'footer_trust_units_prepaid': 'TUs spent for the period, units:',
        'footer_trust_units_prepaid_value': 'Cost of spent TUs, __CCY_LONG__ (w/o VAT):',
        'footer_trust_units_price': 'TU price, __CCY_LONG__ (w/o VAT):',
        'period_start': 'Beginning period balance:',
        'period_end': 'Ending period balance:'
    },
    'labeled_cells': (
        ('header_title', 4, 1),
        ('header_period', 6, 2),
        ('header_client', 7, 2),
        ('header_contract_date', 8, 2),
    ),
    'value_cells': {
        'client_name': (7, 3),
        'reporting_period': (6, 3),
        'contract_date': (8, 3)
    },
    'billing_summary_top_rc': (11, 1),
    'cell_formats': (
        # (3, 1, 'bold'),
        ((6, 10, 6, 6), 'align-right'),
    ),
    'rows_size': ((2, 40.5), (3, 5)),
    'cols_size': ((0, 5), (1, 0.55), (2, 14), (3, 10.4), (4, 52.4), (5, 10.4), (6, 10.4), (7, 10.4)),
    'table_borders': {
        'large': 5,
        'small': 3,
        'vertical': 0.55
    },
    'table_border_size': 5,
    'logo': {
        'logo_rc': (2, 1),
        'filename': 'et_logo.png'
    },
    'workbook_formats': {
        'number-int': {'num_format': '###0'},
        'number-float': {'num_format': '#,##0.00'},
        'bold': {'bold': True},
        'bold-warning': {'bold': True, 'bg_color': '#DA3832', 'font_color': '#FFFFFF'},
        'align-left': {'align': 'left'},
        'align-right': {'align': 'right'},
        'billing-header': {'bold': True, 'bg_color': '#006100', 'font_color': '#FFFFFF'},
        'billing-header-right': {'bold': True, 'bg_color': '#006100', 'font_color': '#FFFFFF', 'align': 'right'},
        'billing-header-warning': {'bold': True, 'bg_color': '#DA3832', 'font_color': '#FFFFFF', 'align': 'right'},
        'billing-int': {'bg_color': '#C6EFCE', 'font_color': '#006100', 'align': 'right', 'num_format': '#,##0'},
        'billing-float': {
            'bg_color': '#C6EFCE', 'font_color': '#006100',
            'align': "right",
            'num_format': '#,##0.00;(#,##0.00)'
        },
        'billing-float-extended': {
            'bg_color': '#C6EFCE', 'font_color': '#006100',
            'align': "right",
            'num_format': '#,##0.000;(#,##0.000)'
        },
        'billing-float-underlined': {
            'bg_color': '#C6EFCE',
            'font_color': '#006100',
            'align': "right",
            'num_format': '#,##0.00',
            'top': 6
        },
        'billing-label': {'bg_color': '#C6EFCE', 'font_color': '#006100'},
        'billing-label-wrapped': {'bg_color': '#C6EFCE', 'font_color': '#006100', 'text_wrap': True, 'align': 'top'},
        'billing-label-right': {'bg_color': '#C6EFCE', 'font_color': '#006100', 'align': 'right'},
        'billing-label-right-underlined': {
            'bg_color': '#C6EFCE',
            'font_color': '#006100',
            'align': 'right',
            'top': 6
        },
        'billing-border': {'bg_color': '#C6EFCE'}
    }
}
