from datetime import date
from rest_framework import serializers
from celery_tasks.models import FileProcessingTask
from clients.models import Client, Industry, ClientCountry
from contracts.models import Order, Contract, OrderPrice, Service, OrderService, Currency, PaymentType
from vendors.models import Vendor, VendorService, VendorFilterOverride
from reports.models import ReportFile, Report, ReportType, ReportSkipColumnConfig, ReportLanguage


class ReportSerializerBase(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['file_name', 'vendors']


class ReportFileSerializer(serializers.ModelSerializer):
    report = ReportSerializerBase(many=False)

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
    end_date = serializers.DateField(required=False)

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
                  "end_date",
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


class VendorSerializerBasic(serializers.ModelSerializer):

    class Meta:
        model = Vendor
        fields = ['vendor_id', 'description']


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
                  "end_date",
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


class ReportSerializer(serializers.ModelSerializer):
    vendors = VendorSerializerBasic(many=True, required=False)

    class Meta:
        model = Report
        fields = ['id', 'client', 'file_name', 'is_active', 'include_details',
                  'show_pids', 'language', 'skip_columns', 'vendors']

    def create(self, validated_data):
        if 'report_type' not in validated_data:
            try:
                default_report_type = ReportType.objects.get(pk=1)
            except ReportType.DoesNotExist:
                raise serializers.ValidationError("Default report_type does not exist. Provide report_type in request.")
            validated_data['report_type'] = default_report_type
        return super().create(validated_data)


class ReportVendorUpdateSerializer(serializers.ModelSerializer):
    vendors = serializers.PrimaryKeyRelatedField(many=True, queryset=Vendor.objects.all())

    def validate_vendors(self, value):
        report = self.instance
        if report:
            valid_vendors = Vendor.objects.filter(client=report.client)
            if not all(vendor in valid_vendors for vendor in value):
                raise serializers.ValidationError("Some vendors are not associated with the report's client.")
        return value

    class Meta:
        model = Report
        fields = ['vendors']


class ReportSkipColumnsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportSkipColumnConfig
        fields = '__all__'


class ReportLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportLanguage
        fields = '__all__'


class YearMonthField(serializers.CharField):
    def to_internal_value(self, data):
        # Validate format
        try:
            year, month = map(int, data.split('-'))
            parsed_date = date(year, month, 1)
        except ValueError:
            raise serializers.ValidationError("Period must be in YYYY-MM format.")

        # Validate year and month
        if parsed_date.year < 2020:
            raise serializers.ValidationError("Period cannot be earlier than 2020-01.")

        # Check if date is in the future
        if parsed_date > date.today():
            raise serializers.ValidationError("Period cannot be in the future.")

        return parsed_date


class ClientPeriodSerializer(serializers.Serializer):
    period = YearMonthField()
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ReportPeriodSerializer(serializers.Serializer):
    period = YearMonthField()
    report = serializers.PrimaryKeyRelatedField(queryset=Report.objects.all())

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class VendorPeriodSerializer(serializers.Serializer):
    period = YearMonthField()
    vendor = serializers.PrimaryKeyRelatedField(queryset=Vendor.objects.all())

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ClientReportListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Report
        fields = ['id', 'file_name']


class CeleryTaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = FileProcessingTask
        fields = '__all__'
