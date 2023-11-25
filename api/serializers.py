from rest_framework import serializers
from clients.models import Client, Industry, ClientCountry
from contracts.models import Order, Contract, OrderPrice, Service, OrderService, Currency, PaymentType
from vendors.models import Vendor, VendorService, VendorFilterOverride
from reports.models import ReportFile, Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['file_name', 'vendors']


class ReportFileSerializer(serializers.ModelSerializer):
    report = ReportSerializer(many=False)

    class Meta:
        model = ReportFile
        fields = ['id', 'period', 'report', 'file', 'type_id']


class ServiceIDListSerializer(serializers.Serializer):
    ids = serializers.PrimaryKeyRelatedField(many=True, queryset=Service.objects.all())

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["service_id", "service", "stype", "desc_bg", "desc_en", "service_order"]


class ServiceSerializerLimited(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["service_id", "service", "stype", "service_order", "desc_en"]


class OrderSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = '__all__'


class OrderSerializerVerbose(serializers.ModelSerializer):
    currency = serializers.ReadOnlyField()
    payment = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = ["order_id",
                  "start_date",
                  "description",
                  "currency",
                  "ccy_type",
                  "payment",
                  "payment_type",
                  "tu_price",
                  "is_active"
                  ]


# Vendors
class VendorsListSerializer(serializers.Serializer):
    ids = serializers.PrimaryKeyRelatedField(many=True, queryset=Vendor.objects.all())

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class VendorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Vendor
        fields = '__all__'


class VendorAssignSerializer(serializers.ModelSerializer):

    class Meta:
        model = Vendor
        fields = ['vendor_id', 'client_id']


class VendorServiceSerializer(serializers.ModelSerializer):
    service = ServiceSerializerLimited(many=False)
    filter_override = serializers.SerializerMethodField()

    class Meta:
        model = VendorService
        fields = '__all__'

    def get_filter_override(self, obj):
        vfo = VendorFilterOverride.objects.filter(vendor=obj.vendor, service=obj.service).first()
        if vfo:
            return vfo.filter.filter_name
        return None


class ClientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Client
        fields = ['client_id', 'legal_name', 'reporting_name', 'client_group', 'industry', 'country']


class OrderServiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderService
        fields = '__all__'


class OrderServiceSerializerVerbose(serializers.ModelSerializer):
    service = VendorServiceSerializer(many=False)

    class Meta:
        model = OrderService
        fields = '__all__'


class OrderPriceSerializer(serializers.ModelSerializer):
    service = ServiceSerializerLimited(many=False)

    class Meta:
        model = OrderPrice
        fields = '__all__'


class OrderRelated(OrderSerializerVerbose):
    service_prices = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["order_id",
                  "currency",
                  "ccy_type",
                  "payment",
                  "payment_type",
                  "start_date",
                  "description",
                  "tu_price",
                  "is_active",
                  'service_prices']

    def get_service_prices(self, obj):
        prices = OrderPrice.objects.filter(order_id=obj.order_id)
        serializer = OrderPriceSerializer(prices, many=True)
        return serializer.data


class ContractListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = '__all__'


class ContractSerializer(ContractListSerializer):
    orders = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = '__all__'

    def get_orders(self, obj):
        orders = obj.orders.all()
        serializer = OrderSerializerVerbose(orders, many=True)
        return serializer.data


# Metadata related
class CurrencySerializer(serializers.ModelSerializer):

    class Meta:
        model = Currency
        fields = ['id', 'ccy_type']


class PaymentTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = PaymentType
        fields = ['id', 'description']


class IndustrySerializer(serializers.ModelSerializer):

    class Meta:
        model = Industry
        fields = '__all__'


class CountrySerializer(serializers.ModelSerializer):

    class Meta:
        model = ClientCountry
        fields = ['id', 'country']


class VendorServiceIDsSerializer(serializers.Serializer):
    ids = serializers.PrimaryKeyRelatedField(many=True, queryset=VendorService.objects.all())

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
