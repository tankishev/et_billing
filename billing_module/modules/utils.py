from enum import Enum
from datetime import datetime
from dateutil.relativedelta import relativedelta


class ChargeType(Enum):
    """
    Enumeration representing different types of charges.
    """

    PREPAID_PACKAGE = 1
    SUBSCRIPTION = 2
    INVOICE = 3
    NO_CHARGE = 4
    PREPAID_SHARED = 5


class ChargeStatus(Enum):
    """
    Enumeration representing status of a prepaid charge.
    """

    PENDING = 1
    POSTED = 2


def get_last_date_of_period(period: str):
    first_date_of_period = datetime.strptime(period, '%Y-%m').date()
    first_date_of_next_month = first_date_of_period + relativedelta(months=+1)
    last_date_of_period = first_date_of_next_month - relativedelta(days=1)
    return last_date_of_period
