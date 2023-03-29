from shared.utils import DictToObjectMixin
from .currency import CurrencyMixin


class BillingSummary(CurrencyMixin, DictToObjectMixin):

    def __init__(self, *args, **kwargs):
        self.add_attributes(**kwargs)
        CurrencyMixin.__init__(self, *args, **kwargs)
        self.layout = None

    def load_layout(self, layout_factory):
        localization = {
            'language': self.language,
            'currency': self.currency,
            'ccy_short': self.ccy_short,
            'ccy_long': self.ccy_long,
            'load_tables': True
        }
        self.layout = layout_factory.get_layout(**localization)
