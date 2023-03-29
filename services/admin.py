from django.db import models
from django.forms import Textarea
from django.contrib import admin
from .models import Filter, FilterConfig, Service


class FilterConfigInline(admin.TabularInline):
    model = FilterConfig
    extra = 0

    def get_formset(self, request, obj=None, **kwargs):
        """
        Override the formset function in order to remove the add and change buttons beside the foreign key pull-down
        menus in the inline.
        """
        formset = super(FilterConfigInline, self).get_formset(request, obj, **kwargs)
        form = formset.form
        widget = form.base_fields['func'].widget
        widget.can_add_related = False
        widget.can_change_related = False
        widget.can_delete_related = False
        return formset


class FilterAdmin(admin.ModelAdmin):
    ordering = ['filter_name']
    search_fields = ['filter_name']
    inlines = [FilterConfigInline]

    formfield_overrides = {models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 60})}}

    def render_change_form(self, request, context, *args, **kwargs):
        form_instance = context['adminform'].form
        form_instance.fields['description'].widget.attrs['placeholder'] = 'optional: filter description'
        return super().render_change_form(request, context, *args, **kwargs)


class ServiceAdmin(admin.ModelAdmin):
    list_display = ['service_id', 'service', 'stype', 'desc_en', 'filter', 'service_order']
    list_filter = ['service']
    list_display_links = ['desc_en']
    list_editable = ['service_order']
    ordering = ['service_order']
    list_per_page = 20


admin.site.register(Filter, FilterAdmin)
admin.site.register(Service, ServiceAdmin)
