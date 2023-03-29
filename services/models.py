from django.db import models


class Filter(models.Model):
    filter_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.filter_name

    class Meta:
        db_table = "service_filters"


class FilterFunction(models.Model):
    func = models.CharField(max_length=15, unique=True)
    description = models.CharField(max_length=50)

    def __str__(self):
        return self.description

    class Meta:
        db_table = "service_filter_functions"


class FilterConfig(models.Model):

    filter = models.ForeignKey(Filter, on_delete=models.CASCADE)
    field = models.CharField(max_length=30)
    func = models.ForeignKey(FilterFunction, on_delete=models.RESTRICT, related_name='filter_configs')
    value = models.CharField(max_length=15, default='', blank=True)

    def __str__(self):
        return f'{self.field}_{self.func}, {self.value}'

    class Meta:
        db_table = "service_filter_configs"


class Service(models.Model):

    service_id = models.AutoField(primary_key=True, verbose_name='Service ID')
    service = models.CharField(max_length=20, verbose_name='Service group')
    stype = models.CharField(max_length=20, verbose_name='Service type', null=True, blank=True)
    desc_bg = models.CharField(max_length=255, verbose_name='Description BG')
    desc_en = models.CharField(max_length=255, verbose_name='Description EN')
    tu_cost = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name='TU cost')
    usage_based = models.BooleanField(default=False, verbose_name='Transaction based')
    skip_service_render = models.BooleanField(default=False, verbose_name='Hide in reports')
    filter = models.ForeignKey(
        Filter, on_delete=models.RESTRICT, null=True, blank=True, related_name='filter_services')
    service_order = models.IntegerField(unique=True)

    def __str__(self):
        return f'{self.service} - {self.desc_en} - ({self.service_id})'

    class Meta:
        db_table = "services"
        ordering = ('service_order',)
