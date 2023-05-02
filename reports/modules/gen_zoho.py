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
        select ? as period
             , tmp2.vendor_id as vendor_id
             , c.client_id
             , c.reporting_name as client_name
             , s2.service, s2.stype, s2.desc_bg as description
             , tmp2.unit_count, tmp2.tu_cost, tmp2.unit_cost, tmp2.total_cost, tmp2.bgn_cost
             , c.client_group, ci.industry
        from (
            select vendor_id, service_id, sum(unit_count) as unit_count
                 ,round(avg(tu_price),2) as tu_cost, round(avg(unit_cost),2) as unit_cost
                 ,round(sum(total_cost),2) as total_cost, round(sum(bgn_cost),2) as bgn_cost
            from (
                select
                    su.vendor_id
                    ,su.service_id
                    ,su.unit_count
                    ,case
                        when o.ccy_type = 3 then o.tu_price
                        when o.ccy_type = 4 then o.tu_price / 1.95583
                        else 0
                    end tu_price
                    ,case
                        when o.ccy_type = 1 then op.unit_price / 1.95583
                        when o.ccy_type = 2 then op.unit_price
                        when o.ccy_type = 3 then op.unit_price * o.tu_price / 1.95583
                        when o.ccy_type = 4 then op.unit_price * o.tu_price
                        else 0
                    end unit_cost
                    ,case
                        when o.ccy_type = 1 then su.unit_count * op.unit_price / 1.95583
                        when o.ccy_type = 2 then su.unit_count * op.unit_price
                        when o.ccy_type = 3 then su.unit_count * op.unit_price * o.tu_price / 1.95583
                        when o.ccy_type = 4 then su.unit_count * op.unit_price * o.tu_price
                        else 0
                    end total_cost
                    ,case
                        when o.ccy_type = 1 then su.unit_count * op.unit_price
                        when o.ccy_type = 2 then su.unit_count * op.unit_price * 1.95583
                        when o.ccy_type = 3 then su.unit_count * op.unit_price * o.tu_price
                        when o.ccy_type = 4 then su.unit_count * op.unit_price * o.tu_price * 1.95583
                        else 0
                    end bgn_cost
                from stats_usage su
                left join services s on su.service_id = s.service_id
                left join vendor_services vs on su.vendor_id = vs.vendor_id and su.service_id = vs.service_id
                left join order_services os on vs.id = os.vendor_service_id
                left join orders o on os.order_id = o.order_id
                left join order_prices op on o.order_id = op.order_id and op.service_id = su.service_id
                where su.period = ? and o.is_active = 1
                 ) tmp
            group by vendor_id, service_id
             ) tmp2
        left join services s2 on s2.service_id = tmp2.service_id
        left join vendors cv2 on cv2.vendor_id = tmp2.vendor_id
        left join client_data c on cv2.client_id = c.client_id
        left join client_industries ci on c.industry_id = ci.id
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
