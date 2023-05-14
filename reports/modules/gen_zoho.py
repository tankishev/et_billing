# CODE OK ... ADD CELERY CREATE NEW TEMPLATE
from django.conf import settings

from stats.models import UquStatsPeriodVendor, UquStatsPeriodClient, UquStatsPeriod

import pandas as pd
import sqlite3 as sl
import os


DB_PATH = settings.DATABASES.get('default').get('NAME')
REPORT_PATH = settings.MEDIA_ROOT / 'output/zoho'
USAGE_FILENAME = 'usage_summary.xlsx'
UQU_VENDORS_FILENAME = 'uqu_vendors.xlsx'
UQU_CLIENTS_FILENAME = 'uqu_clients.xlsx'
UQU_PERIODS_FILENAME = 'uqu_period.xlsx'


def gen_zoho_usage_summary(period):
    """ Generate service usage report for Zoho Analytics"""

    conn = sl.connect(DB_PATH)

    sql = """
        select ? as period, *, round(total_cost * 1.95583, 2) as bgn_cost 
        from (
            select u.vendor_id, c.client_id, c.reporting_name as client_name, c.client_group, ci.industry,
                s.service, s.stype, s.desc_en as description,
                u.unit_count, u.tu_price * ccy_rate as tu_cost,
                round(coalesce(op.unit_price, 0) * ccy_rate * case when is_tu then tu_price else 1 end,2) as unit_cost,
                round(coalesce(op.unit_price, 0) * ccy_rate * case when is_tu then tu_price else 1 end * u.unit_count, 2) as total_cost
            from (
                select 
                    su.vendor_id, su.service_id, su.unit_count, o.order_id, 
                    coalesce(o.tu_price, 0) as tu_price, ccy_type,
                    case
                        when o.ccy_type in (1, 3) then 0.51129
                        when o.ccy_type in (2, 4) then 1
                        when o.ccy_type = 6 then 0.91
                        else 0
                    end ccy_rate,
                    case when o.ccy_type in (3, 4, 6) then 1 else 0 end is_tu
                from vendor_services vs
                join stats_usage su on vs.service_id = su.service_id and vs.vendor_id = su.vendor_id and su.period = ?
                left join order_services os on vs.id = os.vendor_service_id and os.order_id in (
                        select order_id from orders o where is_active = 1
                    )
                left join orders o on os.order_id = o.order_id
            ) u
            left join order_prices op on u.order_id = op.order_id and u.service_id = op.service_id
            left join vendors v on u.vendor_id = v.vendor_id
            left join client_data c on v.client_id = c.client_id
            left join services s on u.service_id = s.service_id
            left join client_industries ci on c.industry_id = ci.id
        );
    """

    month = period + '-01'
    df = pd.read_sql(sql, conn, params=(period, month))
    output_path = REPORT_PATH / period
    os.makedirs(output_path, exist_ok=True)
    filepath = os.path.join(output_path, USAGE_FILENAME)
    df.to_excel(filepath, index=False)

    return USAGE_FILENAME,


def gen_zoho_uqu_vendors(period):
    """ Generate Unique Users by Vendors report for Zoho

    :param period: report will include data for the given period and all periods before it
    :return:
    """

    retval = []
    uqu_vendors = UquStatsPeriodVendor.objects.filter(period__lte=period).order_by('period', 'vendor_id')
    for el in uqu_vendors:
        retval.append((el.period, el.vendor_id, el.uqu_month, el.cumulative, el.uqu_new, el.uqu_month - el.uqu_new))
    df = pd.DataFrame(retval, columns=['period', 'vendor_id', 'uqu_month', 'uqu_cumulative', 'uqu_new', 'uqu_existing'])
    save_uqu_file(df, period, UQU_VENDORS_FILENAME)
    return df


def gen_zoho_uqu_clients(period):
    retval = []
    uqu_clients = UquStatsPeriodClient.objects.filter(period__lte=period).order_by('period', 'client_id')
    for el in uqu_clients:
        retval.append((el.period, el.client_id, el.uqu_month, el.cumulative, el.uqu_new, el.uqu_month - el.uqu_new))
    df = pd.DataFrame(retval, columns=['period', 'client_id', 'uqu_month', 'uqu_cumulative', 'uqu_new', 'uqu_existing'])
    save_uqu_file(df, period, UQU_CLIENTS_FILENAME)
    return df


def gen_zoho_uqu_period(period):
    retval = []
    uqu_periods = UquStatsPeriod.objects.filter(period__lte=period).order_by('period')
    for el in uqu_periods:
        retval.append((el.period, el.uqu_month, el.cumulative, el.uqu_new, el.uqu_month - el.uqu_new))
    df = pd.DataFrame(retval, columns=['period', 'uqu_month', 'uqu_cumulative', 'uqu_new', 'uqu_existing'])
    save_uqu_file(df, period, UQU_PERIODS_FILENAME)
    return df


def save_uqu_file(df, period, filename):
    output_path = REPORT_PATH / period
    os.makedirs(output_path, exist_ok=True)
    filepath = os.path.join(output_path, filename)
    df.to_excel(filepath, index=False)


def prior_period(period):
    year, month = [int(x) for x in period.split('-')]
    year = year - 1 if month == 1 else year
    month = month - 1 if month != 1 else 12
    return f'{year}-{month}'
