from django.db import models


class Industry(models.Model):
    industry = models.CharField(max_length=30, verbose_name='Industry', unique=True)

    def __str__(self):
        return self.industry

    class Meta:
        db_table = 'client_industries'
        verbose_name_plural = 'Industries'
        ordering = ('industry', )


class ClientCountry(models.Model):
    code = models.CharField(max_length=3)
    country = models.CharField(max_length=30)

    def __str__(self):
        return self.country

    class Meta:
        db_table = 'client_countries'
        ordering = ('country', )
        verbose_name_plural = 'Countries'


class Client(models.Model):
    client_id = models.IntegerField(primary_key=True, verbose_name='Client ID')
    legal_name = models.CharField(max_length=100, verbose_name='Legal name')
    reporting_name = models.CharField(max_length=100, verbose_name='Reporting name')
    client_group = models.CharField(max_length=100, verbose_name='Client group', blank=True, null=True)
    is_billable = models.BooleanField(default=False, verbose_name='Is billable')
    is_validated = models.BooleanField(default=False, verbose_name='Is validated')
    industry = models.ForeignKey(
        Industry, on_delete=models.RESTRICT, verbose_name='Client industry', related_name='clients')
    country = models.ForeignKey(
        ClientCountry, on_delete=models.RESTRICT, related_name='clients')

    def __str__(self):
        return f'{self.client_id}_{self.reporting_name}'

    class Meta:
        db_table = 'client_data'
