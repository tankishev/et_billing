from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Count

from contracts.models import Contract
from vendors.models import Vendor

from .models import Client, Industry, ClientCountry


# Inline admin for Vendor
class ClientVendorInline(admin.TabularInline):
    model = Vendor
    extra = 0
    show_change_link = True
    readonly_fields = ['is_reconciled']
    max_num = 0


# Inline admin for Contract
class ClientContractsInline(admin.TabularInline):
    model = Contract
    extra = 0
    show_change_link = True


# Custom filter for clients with/ without contracts
class HasContractFilter(SimpleListFilter):
    title = 'has contract'
    parameter_name = 'has_contract'

    def lookups(self, request, model_admin):
        return (
            (1, 'Yes'),
            (0, 'No')
        )

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(contracts__isnull=False)
        elif self.value() == "0":
            return queryset.filter(contracts__isnull=True)
        return queryset


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['client_id', 'legal_name', 'reporting_name',
                    'client_group', 'industry', 'is_billable',
                    'is_validated', 'vendor_count', 'country']
    list_editable = ['is_billable', 'is_validated']
    list_display_links = ['legal_name']
    search_fields = ['legal_name', 'reporting_name', 'client_id']
    list_per_page = 20
    list_filter = ['is_billable', HasContractFilter, 'is_validated', 'country']
    inlines = [ClientVendorInline, ClientContractsInline]

    def get_form(self, request, obj=None, **kwargs):
        form = super(ClientAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields["industry"].widget.can_add_related = False
        form.base_fields["industry"].widget.can_change_related = False
        form.base_fields["industry"].widget.can_delete_related = False
        return form

    @staticmethod
    def vendor_count(obj):
        return obj.vendor_count

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(vendor_count=Count("vendors"))
        return queryset


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    pass


@admin.register(ClientCountry)
class ClientCountryAdmin(admin.ModelAdmin):
    pass
