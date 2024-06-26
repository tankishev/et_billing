from .et import ETApi, SigningUser
import time
import logging

logger = logging.getLogger(f'et_billing.{__name__}')

AUTH_TIMEOUT = 45  # Time in seconds for the user to complete 2FA before timeout and login rejected
TIME_BETWEEN_CHECKS = 2  # Seconds between checks with ET for successful authentication


def authorise_user(user, timeout=AUTH_TIMEOUT) -> tuple[bool, str]:
    """ Authorise user with 2FA of Evrotrust
        :param user: django user object
        :param timeout: Number of seconds to try to authorise before giving up and returning False
    """

    # Check if user profile includes phone or PID
    if user.profile.pid or user.profile.phone_number:
        logger.debug('Setting up user and API objects')
        et_user = SigningUser(
            pid=user.profile.pid,
            phone=user.profile.phone_number
        )
        et_api = ETApi()

        # Call 2FA API
        logger.debug('Sending 2FA call to ET')
        is_successful, response = et_api.auth(et_user)

        if is_successful:
            # Get transaction_id
            transaction_id = response.get('transactionID')
            # Start checking for successful 2FA
            start_time = time.time()
            timeout_seconds = timeout
            while (time.time() - start_time) < timeout_seconds:
                res = et_api.check_document_status(transaction_id)
                if res:
                    status = res.get('status')
                    processing = res.get('isProcessing')

                    if status == 3:
                        logger.info('Authorisation rejected by user')
                        return False, 'Authorisation rejected by user'

                    elif status == 2 and processing == 0:
                        logger.info('Authorisation approved')
                        return True, 'Successful'

                time.sleep(TIME_BETWEEN_CHECKS)
            logger.info('Authorisation timeout')
            return False, '2FA authorisation timeout'
        else:
            logger.critical('2FA API error')
            return False, 'Error with 2FA Authorisation'
    else:
        logger.warning('User profile does not contain PID or phone number')
        return False, 'Profile incomplete - contact site admin'
