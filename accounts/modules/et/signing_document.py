import hashlib


class Document:
    """ A class defining a File object as per ET API """

    def __init__(self, filepath: str, description=None):
        self.filepath = filepath
        self.description = 'Document for signature' if description is None else description
        self.sha512 = None
        self.file_data = None
        self.preview = 0
        self.optional = 0

    def prepare(self):
        """ Calculate read the document and calculate its hash """
        with open(self.filepath, 'rb') as f:
            self.file_data = f.read()
            self.sha512 = hashlib.sha512(self.file_data).hexdigest()

    @property
    def data_basic(self) -> dict:
        """ Returns the 'data' attribute for the API call """

        return {
                "description": self.description,
                "checksumDocument": self.sha512
                }

    @property
    def data_group_sign(self):
        """ Returns the 'data' attribute for a group signing API call """

        data = self.data_sign
        data.update({"optional": self.optional})
        return data

    @property
    def data_sign(self) -> dict:
        """ Returns the 'data' attribute for a signing API call """

        data = self.data_basic
        data.update({"preview": self.preview})
        return data
