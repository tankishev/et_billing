from django.contrib import admin
from django.db.models import Count

from services.models import Service, Filter, ServiceFilterOverride
from shared.utils import get_parent_object_from_request
from .models import Vendor, VendorService, VendorInputFile


class ServiceFilterOverrideAdmin(admin.ModelAdmin):
    list_display = ['id', 'vendor', 'service', 'filter']
    search_fields = ['vendor__id', 'vendor__description']
    ordering = ['vendor_id', 'service_id']


class VendorServicesInline(admin.TabularInline):
    model = VendorService
    extra = 0
    ordering = ['service']
    verbose_name = 'Service'
    verbose_name_plural = 'services used'


class ServiceFilterOverrideInline(admin.TabularInline):
    model = ServiceFilterOverride
    extra = 0
    ordering = ['service']
    verbose_name = 'Filter Override'
    verbose_name_plural = 'service filter overrides'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "service":
            vendor = get_parent_object_from_request(self, request)
            if vendor is not None:
                vs_qs = VendorService.objects.filter(vendor=vendor).values('service_id')
                services_list = [el.get('service_id') for el in vs_qs]
                kwargs["queryset"] = Service.objects.filter(service_id__in=services_list)
        elif db_field.name == 'filter':
            kwargs["queryset"] = Filter.objects.order_by('filter_name')
        return super(ServiceFilterOverrideInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


class VendorAdmin(admin.ModelAdmin):
    ordering = ['vendor_id']
    list_per_page = 20
    list_display = ['vendor_id', 'client_name', 'description', 'service_count', 'is_reconciled', 'is_active']
    list_filter = ['is_reconciled', 'is_active']
    search_fields = ['vendor_id', 'client__reporting_name', 'client__legal_name']
    list_select_related = ['client']

    fields = ['client', 'vendor_id', 'description', 'iteco_name', 'is_reconciled', 'is_active']
    readonly_fields = ['iteco_name']
    exclude = ['services']
    inlines = [VendorServicesInline, ServiceFilterOverrideInline]

    def get_form(self, request, obj=None, **kwargs):
        form = super(VendorAdmin, self).get_form(request, obj, **kwargs)
        field = form.base_fields["client"]
        field.widget.can_add_related = False
        field.widget.can_change_related = False
        field.widget.can_delete_related = False
        return form

    @staticmethod
    def client_name(obj):
        return obj.client.reporting_name

    @staticmethod
    def service_count(obj):
        return obj.service_count

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(service_count=Count("vendor_services"))
        return queryset


class VendorInputFileAdmin(admin.ModelAdmin):
    list_display = ['period', 'vendor']
    search_fields = ['period', 'vendor__vendor_id', 'vendor__description']


admin.site.register(ServiceFilterOverride, ServiceFilterOverrideAdmin)
admin.site.register(Vendor, VendorAdmin)
admin.site.register(VendorInputFile, VendorInputFileAdmin)
