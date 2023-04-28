from django.contrib import admin
from .models import ReportSkipColumnConfig, Report
from vendors.models import Vendor
from shared.utils import get_parent_object_from_request


class ReportVendorsInline(admin.TabularInline):
    model = Report.vendors.through
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "vendor":
            client = get_parent_object_from_request(self, request)
            if client is not None:
                kwargs["queryset"] = Vendor.objects.filter(client_id=client.client_id)
        return super(ReportVendorsInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        """
        Override the formset function in order to remove the add and change buttons beside the foreign key pull-down
        menus in the inline.
        """
        formset = super(ReportVendorsInline, self).get_formset(request, obj, **kwargs)
        form = formset.form
        widget = form.base_fields['vendor'].widget
        widget.can_add_related = False
        widget.can_change_related = False
        widget.can_delete_related = False
        return formset


class ReportAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'client', 'report_type', 'language', 'include_details', 'show_pids', 'is_active']
    list_editable = ['is_active']
    list_display_links = ['file_name']
    ordering = ['file_name']
    search_fields = ['client__reporting_name', 'file_name']
    list_per_page = 20
    list_filter = ['is_active', 'include_details', 'show_pids']

    fields = ['client', 'report_type', 'language', 'file_name', 'include_details',
              'skip_columns', 'show_pids', 'is_active']
    exclude = ['vendors']
    inlines = [ReportVendorsInline]

    def get_form(self, request, obj=None, **kwargs):
        form = super(ReportAdmin, self).get_form(request, obj, **kwargs)
        for field_name, field in form.base_fields.items():
            if field_name in ['report_type', 'language', 'client', 'skip_columns']:
                field.widget.can_add_related = False
                field.widget.can_change_related = False
                field.widget.can_delete_related = False
        return form


class SkipColumnsAdmin(admin.ModelAdmin):
    list_display = ['skip_columns', 'description', 'report_count']
    ordering = ['skip_columns']

    @staticmethod
    def report_count(obj):
        return obj.reports.count()


admin.site.register(Report, ReportAdmin)
admin.site.register(ReportSkipColumnConfig, SkipColumnsAdmin)
