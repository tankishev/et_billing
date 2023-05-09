class SigningUser:
    """ A class to define an ET User """

    def __init__(self, pid=None, country=None, email=None, phone=None, employee=False):
        self.pid = pid
        self.country = country
        self.email = email
        self.phone = phone
        self.employee = employee

    @property
    def data(self):
        """ Returns the 'data' attribute for the API call """

        if self.pid:
            return {
                "identificationNumber": self.pid,
                "country": "BG" if self.country is None else self.country,
            }
        elif self.phone:
            return {"phone": self.phone}
        elif self.email:
            return {"email": self.phone}

    @property
    def data_for_sign(self):
        """ Returns the 'data' attribute for the API call if the user will be signing """

        user_data = self.data
        if user_data:
            user_data['employee'] = 1 if self.employee else 0
            return user_data
