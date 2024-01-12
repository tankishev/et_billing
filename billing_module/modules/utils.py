from enum import Enum


class ChargeType(Enum):
    """
    Enumeration representing different types of charges.
    """

    PREPAID = 1
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
