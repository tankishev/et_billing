from django.contrib import admin
from shared.utils import get_parent_object_from_request
from contracts.models import Order
from .models import PrepaidPackage, OrderPackages


# Inline for OrderPackage
class OrderPackagesInline(admin.TabularInline):
    model = OrderPackages
    extra = 0
    fields = ['order']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'order':
            package = get_parent_object_from_request(self, request)
            if package is not None:
                kwargs["queryset"] = Order.objects.filter(contract=package.contract)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(PrepaidPackage)
class PrepaidPackageAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'description', 'start_date', 'original_balance', 'currency', 'status'
    )
    list_filter = ('status', 'currency')
    search_fields = ('description',)
    readonly_fields = ('available_balance', 'balance', 'value_eur')
    inlines = [OrderPackagesInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('currency')

    def available_balance(self, obj):
        return obj.available_balance
    available_balance.short_description = 'Available Balance'

    def balance(self, obj):
        return obj.balance
    balance.short_description = 'Balance'

    def value_eur(self, obj):
        return obj.value_eur
    value_eur.short_description = 'Value in EUR'
