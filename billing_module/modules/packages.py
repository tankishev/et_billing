from __future__ import annotations
from datetime import date
from dateutil.relativedelta import relativedelta
from django.db import transaction
from .utils import ChargeStatus
from ..models import PrepaidPackage, PrepaidPackageCharge, PackageStatus

import logging

logger = logging.getLogger(f'et_billing.{__name__}')


def renew_package(package: PrepaidPackage, renew_date) -> PrepaidPackage | None:

    description = f'{package.description} RENEWED' if package.description else f'Package {package.pk} RENEWED'
    end_date = renew_date + relativedelta(months=1)
    new_package = PrepaidPackage.objects.create(
        start_date=renew_date,
        expiry_date=end_date,
        description=description,
        original_balance=package.original_balance,
        currency=package.currency,
        original_rate=package.original_rate
    )

    if transfer_balance(package, new_package, post_transaction=False):
        return new_package


def transfer_balance(from_package: PrepaidPackage, to_package: PrepaidPackage, post_transaction=True, **kwargs) -> bool:
    """
    Transfers balance from one prepaid package to another.

    This function transfers the entire balance from 'from_package' to 'to_package', recalculates the new average rate
    for to_package based on the transferred balance, and updates the package states accordingly. The function performs
    checks to ensure both packages are active and share the same currency type before proceeding with the transfer.
    It also logs the transfer details and creates corresponding charge records.

    Parameters:
    - from_package (PrepaidPackage): The package from which the balance will be deducted.
    - to_package (PrepaidPackage): The package to which the balance will be credited.
    - post_transaction (bool, optional): Flag to indicate if the transaction should be posted immediately.
      Defaults to True. If False, the transaction is marked as pending.
    - **kwargs: Additional keyword arguments. Currently, supports 'transfer_date' which specifies the date of
      the transfer. Defaults to the current date if not provided.

    Returns:
    - bool: True if the transfer was successful, False otherwise. The function returns False if the packages
      are not active, do not share the same currency, or if the 'from_package' does not have positive balance.

    Note:
    - The function sets 'from_package' to inactive and assigns a closing date after the transfer.
    - This function assumes that the 'balance' and 'average_rate' properties of PrepaidPackage are correctly
      implemented and provide accurate values.

    Example:
        transfer_balance(package1, package2, post_transaction=False, transfer_date='2024-01-12')
        True
    """

    logger.info(f'Call to transfer balance between packages: {from_package.id} --> {to_package.id}')

    if from_package.currency != to_package.currency:
        logger.warning('Both packages must be of the same currency type')
        return False

    if not from_package.is_active:
        logger.warning('From package is marked an inactive')
        return False

    if post_transaction and not to_package.is_active:
        logger.warning('Can not post transaction to package not marked as active')
        return False

    if to_package.status not in (PackageStatus.PRE_ACTIVE.value, PackageStatus.ACTIVE.value):
        logger.warning('Can not transfer to package not in active or pre_active status')
        return False

    from_balance, to_balance = from_package.balance, to_package.balance
    if from_balance > 0:

        # Calculating new_rate
        from_value = from_balance * from_package.average_rate
        to_value = to_balance * to_package.average_rate
        new_balance = from_balance + to_balance
        new_value = from_value + to_value
        new_rate = new_value / new_balance

        # Posting charges
        charge_date = kwargs.get('transfer_date', str(date.today()))
        charge_status = ChargeStatus.POSTED.value if post_transaction else ChargeStatus.PENDING.value
        charges = [
            PrepaidPackageCharge(
                charge_date=charge_date,
                prepaid_package_id=from_package.id,
                charged_units=from_balance,
                is_credit=False,
                charge_status=charge_status
            ),
            PrepaidPackageCharge(
                charge_date=charge_date,
                prepaid_package_id=to_package.id,
                charged_units=from_balance,
                is_credit=True,
                charge_status=charge_status
            ),
        ]

        # Update package states
        to_package.average_rate = new_rate
        from_package.closing_date = charge_date
        from_package.status = PackageStatus.CLOSED.value if post_transaction else PackageStatus.PRE_CLOSED.value

        # Save changes
        with transaction.atomic():
            PrepaidPackageCharge.objects.bulk_create(charges)
            to_package.save()
            from_package.save()

        logger.info(f'Recorded transfer of balance of {from_balance} from package {from_package.id} to {to_package.id}')
        return True

    return False
