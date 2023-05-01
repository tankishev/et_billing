from django.contrib import admin
from django.db import models
from django.forms import Textarea

from services.models import Service
from shared.utils import get_parent_object_from_request
from vendors.models import VendorService
from .models import Contract, Order, OrderPrice, OrderService, Currency


class ContractOrderInline(admin.TabularInline):
    model = Order
    show_change_link = True
    extra = 0

    formfield_overrides = {models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 60})}}


class ContractsAdmin(admin.ModelAdmin):
    list_display = ['client', 'start_date', 'is_active']
    search_fields = ['client__reporting_name', 'client__client_id']
    ordering = ['client']
    list_per_page = 20

    fields = ['client', 'start_date', 'is_active']
    readonly_fields = ['client']
    inlines = [ContractOrderInline]


class OrderPriceInline(admin.TabularInline):
    model = OrderPrice
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == "service":
            order = get_parent_object_from_request(self, request)
            if order is not None:
                order = get_parent_object_from_request(self, request)
                if db_field.name == "service" and order is not None:
                    order_qs = Order.objects\
                        .select_related('contract__client')\
                        .filter(order_id=order.order_id)\
                        .values('contract__client_id')\
                        .first()
                    client_id = order_qs.get('contract__client_id')
                    vs_qs = VendorService.objects.filter(vendor__client__client_id=client_id).values('service_id')
                    services_list = [el.get('service_id') for el in vs_qs]
                    kwargs["queryset"] = Service.objects.filter(service_id__in=services_list)
        return super(OrderPriceInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


class OrderServiceInline(admin.TabularInline):
    model = OrderService
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "service":
            order = get_parent_object_from_request(self, request)
            if order is not None:
                order_qs = Order.objects\
                    .select_related('contract__client')\
                    .filter(order_id=order.order_id)\
                    .values('contract__client_id')\
                    .first()
                client_id = order_qs.get('contract__client_id')
                kwargs["queryset"] = VendorService.objects.filter(vendor__client__client_id=client_id)
        return super(OrderServiceInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


class OrderAdmin(admin.ModelAdmin):
    list_per_page = 20
    ordering = ['contract__client', 'order_id']
    search_fields = ['contract__client__reporting_name']
    list_select_related = True

    fields = ['contract', 'start_date', 'description',
              'ccy_type', 'tu_price', 'payment_type', 'is_active']
    readonly_fields = ['contract']
    inlines = [OrderPriceInline, OrderServiceInline]
    formfield_overrides = {models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 60})}}


admin.site.register(Contract, ContractsAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Currency)
