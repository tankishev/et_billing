from .signing_user import SigningUser
from .signing_document import Document
import json
import hashlib
import hmac
import time
import requests
import base64
import logging
import os

logger = logging.getLogger('ETAPi')


class ETApi:

    PUBLIC_KEY_FILE = os.environ.get('ENC_PUBLIC_KEY')
    VENDOR_API_KEY = os.environ.get('ETAPI_VENDOR_API_KEY')
    VENDOR_NUMBER = os.environ.get('ETAPI_VENDOR_NUMBER')
    URL = 'https://et.test.iteco.bg/vendor'

    def __init__(self, certificate_type=1, callback_url=None, **kwargs):
        self._vendor_api_key_sha256 = hashlib.sha256(self.VENDOR_API_KEY.encode('utf-8')).digest()
        self._public_key = self._get_public_key()
        self.callback_url = callback_url
        self.certificate_type = certificate_type
        self.signing_type = kwargs.get('signing_type', 'PDF3')
        self.sign_algorithm = kwargs.get('algorithm', 'SHA256')
        self.signing_coverage = kwargs.get('coverage', 20000)

    def auth(self, user: SigningUser, **kwargs):
        """ Send a 2FA authorisation request for a given PID """

        endpoint = '/document/auth/online'
        date_expire = kwargs.get('dateExpire', int(time.time()) + 5 * 60)
        description = kwargs.get('description', 'Approve login request')

        data = {
            'document': {
                'description': description,
                'dateExpire': date_expire
            },
            'signInfo': {
                'algorithm': self.sign_algorithm
            },
            'publicKey': self._public_key,
            'user': user.data,
            'vendorNumber': self.VENDOR_NUMBER
        }
        if self.callback_url:
            data['urlCallback'] = self.callback_url

        try:
            response = self.request(endpoint, data)
            return self._handle_response_auth(response)
        except requests.RequestException as err:
            logger.warning(err)

    def callback(self, transaction_id: str):

        endpoint = '/document/ready'
        data = {
            'transactionID': transaction_id,
            'status': 2,
        }
        response = self.request(endpoint, data, no_header=True)
        return self.handle_response(response)

    def check_document_status(self, transaction_id: str):
        """ Check the signing status of a document given its group_transaction_id """

        endpoint = '/document/status'
        response = self._transaction_id_call(endpoint, transaction_id)
        # {'status': 2, 'isProcessing': 0}
        # 1 - Pending, 2 - Signed, 3 - Rejected, 4 - Expired, 5 - Failed, 6 - Withdrawn, 7 - Undeliverable, 8 - Failed
        # face recognition, 99 - On hold;
        # 200 Document group status
        # 400 Invalid data supplied
        # 401 Unauthorized
        # 443 Document group not found
        return self.handle_response(response)

    def check_document_group_status(self, transaction_id: str):
        """ Check the signing status of the group of documents given their transaction_id """

        endpoint = '/document/group/status'
        response = self._transaction_id_call(endpoint, transaction_id)
        # {'status': 2, 'isProcessing': 0}
        # 1 - Pending, 2 - Signed, 3 - Rejected, 4 - Expired, 5 - Failed, 6 - Withdrawn, 7 - Undeliverable, 8 - Failed
        # face recognition, 99 - On hold;
        # 200 Document group status
        # 400 Invalid data supplied
        # 401 Unauthorized
        # 443 Document group not found
        return self.handle_response(response)

    def check_thread_status(self, thread_id: str):
        """ Checks the signing status of a group of documents given their thread_id """

        endpoint = '/document/thread/status'
        data = {
            'threadID': thread_id,
            'vendorNumber': self.VENDOR_NUMBER,
        }
        response = self.request(endpoint, data)
        # {'statuses': [{'documents': [{'transactionID': '739603815174', 'isProcessing': 0, 'status': 2}]},
        #               {'documents': [{'transactionID': '178894303929', 'isProcessing': 0, 'status': 3}]}]}

        # {'statuses': [{'groupTransactionID': '932773182721', 'groupIsProcessing': 0, 'groupStatus': 2,
        #                'documents': [{'transactionID': '278584612566', 'isProcessing': 0, 'status': 2},
        #                              {'transactionID': '819960119628', 'isProcessing': 0, 'status': 2}]},
        #               {'groupTransactionID': '540720845945', 'groupIsProcessing': 0, 'groupStatus': 2,
        #                'documents': [{'transactionID': '967018810249', 'isProcessing': 0, 'status': 2},
        #                              {'transactionID': '582007680454', 'isProcessing': 0, 'status': 2}]}]}

        # {'statuses': [
        #     {'groupTransactionID': '714030369254', 'groupIsProcessing': 0, 'groupStatus': 2, 'rejectReason': 'testing',
        #      'documents': [{'transactionID': '328094704119', 'isProcessing': 0, 'status': 2},
        #                    {'transactionID': '560373535935', 'isProcessing': 0, 'status': 3}]}]}
        return self.handle_response(response)

    def check_user(self, user: SigningUser, extended=False):
        """ Checks if user exists in Evrotrust """

        endpoint = '/user/check/extended' if extended else '/user/check'
        data = {
            'user': user.data,
            'vendorNumber': self.VENDOR_NUMBER
        }
        response = self.request(endpoint, data)
        # Empty response
        # 204 User found
        # 400 Invalid data supplied
        # 401 Unauthorized
        # 438 User not found

        # #If extended check & data is valid (means you get positive response for missing user)
        # 200 + json
        # 'Content-Type': 'application/json'
        # {'isRegistered': 1, 'isIdentified': 1, 'isRejected': 0, 'isSupervised': 1, 'isReadyToSign': 1,
        #  'hasConfirmedPhone': 1, 'hasConfirmedEmail': 1}
        return self.handle_response(response)

    def download_file(self, transaction_id: str):
        """ Downloads a signed file given its transaction_id """

        endpoint = '/document/download'
        response = self._transaction_id_call(endpoint, transaction_id)
        if response.ok:
            with open('downloaded_file.zip', 'wb') as f:
                f.write(response.content)
        else:
            print(response.status_code, response.text)

    @staticmethod
    def _handle_response_auth(response):
        """ Handle response from the 2FA api call

        Responses:
            200 Document added success {'transactionID': '686870597320', 'threadID': '92C8BAED461F'}
            400 Invalid data supplied
            401 Unauthorized
            438 User not found
            454 Incorrect coverage
        """
        if response.status_code == 200:
            return True, response.json()
        elif response.status_code == 438:
            return False, 'User not found'
        else:
            return False, 'Authentication error'

    @staticmethod
    def handle_response(response):
        try:
            if response.status_code == 200:
                json_response = response.json()
                if response.request.path_url == '/vendor/document/withdraw':
                    status = json_response.get('status')
                    verbose_status = {
                        1: 'successfully withdrawn',
                        2: 'unsuccessful withdrawal',
                        3: 'document already withdrawn'
                    }[status]
                    json_response.update({'verbose_status': verbose_status})
                print(json_response)
                return json_response
            elif response.request.path_url == '/vendor/user/check' and response.status_code in (204, 438):
                if response.status_code == 204:
                    print('User found')
                else:
                    print('User not found')
            else:
                logger.warning(f'{response.status_code} {response.text}')
                print(response.status_code, response.text)
        except Exception as err:
            print(err)

    def identification(self, user: SigningUser, eid_data: list, **kwargs):

        endpoint = '/document/doc/identification'
        date_expire = kwargs.get('dateExpire', int(time.time()) + 3 * 24 * 60)
        id_reason = kwargs.get('id_reason', "Electronic Identification")
        bio_required = kwargs.get('id_reason', False)
        data = {
            'document': {
                "dateExpire": date_expire,
            },
            'includes': {
                'names': True if 'names' in eid_data else False,
                'latinNames': True if 'latinNames' in eid_data else False,
                'emails': True if 'emails' in eid_data else False,
                'phones': True if 'phones' in eid_data else False,
                'address': True if 'address' in eid_data else False,
                'documentType': True if 'documentType' in eid_data else False,
                'documentNumber': True if 'documentNumber' in eid_data else False,
                'documentIssuerName': True if 'documentIssuerName' in eid_data else False,
                'documentValidDate': True if 'documentValidDate' in eid_data else False,
                'documentIssueDate': True if 'documentIssueDate' in eid_data else False,
                'documentCountry': True if 'documentCountry' in eid_data else False,
                'identificationNumber': True if 'identificationNumber' in eid_data else False,
                'gender': True if 'gender' in eid_data else False,
                'nationality': True if 'nationality' in eid_data else False,
                'documentPicture': True if 'documentPicture' in eid_data else False,
                'documentSignature': True if 'documentSignature' in eid_data else False,
                'picFront': True if 'picFront' in eid_data else False,
                'picBack': True if 'picBack' in eid_data else False,
                'picIDCombined': True if 'picIDCombined' in eid_data else False,
                'dateOfBirth': True if 'dateOfBirth' in eid_data else False,
                'placeOfBirth': True if 'placeOfBirth' in eid_data else False
            },
            'identificationReason': id_reason,
            'signInfo': {
                'algorithm': self.sign_algorithm
            },
            "BIOrequired": 1 if bio_required else 0,
            'publicKey': self._public_key,
            'user': user.data,
            'vendorNumber': self.VENDOR_NUMBER
        }
        if self.callback_url:
            data['urlCallback'] = self.callback_url

        try:
            response = self.request(endpoint, data)
            return self.handle_response(response)
        except requests.RequestException as err:
            logger.warning(err)

    def request(self, endpoint: str, data, files=None, no_header=False):
        """ Encodes the data, generates headers and sends request
            :param endpoint: API endpoint to which to send the request
            :param data: message to send
            :param no_header: set true to send plain request without authorization header
            :param files: files to be sent
            :return: The request response """

        url = self.URL + endpoint

        # Encode the data
        data_json = json.dumps(data).encode('utf-8')

        if no_header:
            return requests.post(url, data=data_json, timeout=30)

        # Generate headers
        authorization_header = hmac.new(self._vendor_api_key_sha256, data_json, hashlib.sha256).hexdigest()
        headers = {'Authorization': authorization_header}

        # Send request
        if files:
            response = requests.post(url, headers=headers, data={'data': json.dumps(data)}, files=files, timeout=30)
            return response
        headers.update({'Content-type': 'application/json'})
        return requests.post(url, headers=headers, data=data_json, timeout=30)

    def send_file(self, file: Document, users: list[SigningUser], bio_required=False, **kwargs):
        # Always run check user first because unexpected behavior might occur

        """ Used for sending a file for signature by user
            :param file: Document object to be sent for signing
            :param users: List with SigningUser objects. The order of the list determines order of signing
            :param bio_required: Whether bio id is required for the transaction as extra security
        """

        endpoint = '/document/doc/online'

        date_expire = kwargs.get('dateExpire', int(time.time()) + 3 * 24 * 60)

        # Prepare request file
        if file.sha512 is None:
            file.prepare()
        request_file = {"document": (file.filepath, file.file_data)}

        # Prepare request data
        document = file.data_sign
        document.update({
            "dateExpire": date_expire,
            "certificateType": self.certificate_type,
            "coverage": self.signing_coverage,
        })

        request_data = {
            "document": document,
            "signInfo": {
                "type": self.signing_type,
                "algorithm": self.sign_algorithm
            },
            "BIOrequired": 1 if bio_required else 0,
            "vendorNumber": self.VENDOR_NUMBER,
            "users": [el.data_for_sign for el in users],
            "publicKey": self._public_key
        }
        if self.callback_url:
            request_data['urlCallback'] = self.callback_url

        response = self.request(endpoint, data=request_data, files=request_file)
        # 'Content-Type': 'application/json'
        # {'threadID': '4FB9DCA58607',
        #  'transactions': [{'transactionID': '739603815174', 'identificationNumber': '8203216525', 'country': 'BG'},
        #                   {'transactionID': '178894303929', 'identificationNumber': '8203216525', 'country': 'BG'}]}
        # 200 Document added success
        # 400 Invalid data supplied
        # 401 Unauthorized
        # 438 User not found
        # 450 File exceeds max allowed file size
        # 454 Incorrect coverage
        # 457 Not supported file types
        return self.handle_response(response)

    def send_file_group(self, files: list[Document], description: str, users: list[SigningUser], **kwargs):
        """ Used for signing a group of files. Each file in the group will be signed.
            :param files: list with Document objects
            :param description: description of the group of documents
            :param users: list with SigningUser objects. The order of the list determines order of signing.
        """

        endpoint = '/document/group/online'

        date_expire = kwargs.get('dateExpire', int(time.time()) + 3 * 24 * 60)
        bio_required = kwargs.get('bio_required', False)

        # Prepare files
        for file in files:
            if file.sha512 is None:
                file.prepare()
        request_files = {f'documents[{i}]': (file.filepath, file.file_data) for i, file in enumerate(files)}

        # Prepare data
        documents = [file.data_group_sign for file in files]
        request_data = {
            "documents": documents,
            "signInfo": {
                "type": self.signing_type,
                "algorithm": self.sign_algorithm
            },
            "BIOrequired": 1 if bio_required else 0,
            "vendorNumber": self.VENDOR_NUMBER,
            "users": [el.data_for_sign for el in users],
            "publicKey": self._public_key,
            "groupDescription": description,
            "dateExpire": date_expire,
            "certificateType": self.certificate_type,
            "coverage": self.signing_coverage
        }
        if self.callback_url:
            request_data['urlCallback'] = self.callback_url

        response = self.request(endpoint, data=request_data, files=request_files)
        # The transaction_id returned by the response is the group_transaction_id
        # {'threadID': '037C2F14A5DE',
        #  'transactions': [{'identificationNumber': '8203216525', 'transactionID': '932773182721'},
        #                   {'identificationNumber': '8203216525', 'transactionID': '540720845945'}]}
        return self.handle_response(response)

    def deliver_file(self, file: Document, user: SigningUser, **kwargs):
        """ Used for secure delivery of document to user
            :param file: a Document object to be sent
            :param user: SigningUser object
        """

        endpoint = '/delivery/online'
        date_expire = kwargs.get('dateExpire', int(time.time()) + 3 * 24 * 60)

        # Prepare file
        if file.sha512 is None:
            file.prepare()
        file.description = 'Delivery notice'
        request_file = {"document": (file.filepath, file.file_data)}

        # Prepare data
        document = file.data_basic
        document['dateExpire'] = date_expire
        request_data = {
            "document": document,
            "vendorNumber": self.VENDOR_NUMBER,
            "user": user.data,
            "publicKey": self._public_key
        }

        response = self.request(endpoint, data=request_data, files=request_file)
        return self.handle_response(response)

    def withdraw_file(self, thread_id: str):

        endpoint = '/document/withdraw'
        data = {
            'threadID': thread_id,
            'vendorNumber': self.VENDOR_NUMBER,
        }
        response = self.request(endpoint, data)
        return self.handle_response(response)

    def _get_public_key(self):
        try:
            with open(self.PUBLIC_KEY_FILE, 'rb') as f:
                pem_data = f.read()
            return base64.b64encode(pem_data).decode('utf-8')
        except Exception as err:
            print(err.with_traceback())

    def _transaction_id_call(self, endpoint: str, transaction_id: str):
        """ Used for calls to different endpoints given transaction_id """

        data = {
            'transactionID': transaction_id,
            'vendorNumber': self.VENDOR_NUMBER,
        }
        response = self.request(endpoint, data)
        return response
