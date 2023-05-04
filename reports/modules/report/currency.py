class CurrencyMixin:

    _ALLOWED_CURRENCY = ['BGN', 'EUR', 'USD']
    _DEFAULT_CURRENCY = 'BGN'
    _DEFAULT_CCY_LANGUAGE = 'BG'
    _CURRENCY_DICT = {
        'EN': {
            'BGN': {'short': 'lv.', 'long': 'BGN'},
            'EUR': {'short': 'EUR', 'long': 'EUR'},
            'USD': {'short': 'USD', 'long': 'USD'}
        },
        'BG': {
            'BGN': {'short': 'лв.', 'long': 'лева'},
            'EUR': {'short': 'евро', 'long': 'евро'},
            'USD': {'short': 'щ.д.', 'long': 'щатски долари'}
        }
    }

    def __init__(self, *args, **kwargs):
        self._ccy_language = kwargs.get('language', self._DEFAULT_CCY_LANGUAGE)
        self.currency = kwargs.get('currency', self._DEFAULT_CURRENCY)

    @property
    def currency(self):
        return self._currency

    @currency.setter
    def currency(self, value):
        if value in self._ALLOWED_CURRENCY:
            self._currency = value
        else:
            self._currency = self._DEFAULT_CURRENCY

    @property
    def ccy_short(self):
        ccy_lang = self._CURRENCY_DICT.get(self._ccy_language)
        ccy_dict = ccy_lang.get(self._currency)
        return ccy_dict.get('short')

    @property
    def ccy_long(self):
        ccy_lang = self._CURRENCY_DICT.get(self._ccy_language)
        ccy_dict = ccy_lang.get(self._currency)
        return ccy_dict.get('long')
