from datetime import datetime as dt
from clients.models import Client
from vendors.modules.input_files import InputFilesMixin
from vendors.models import VendorInputFile, Vendor
from ..models import UniqueUser, UquStatsPeriodClient, UquStatsPeriodVendor, UquStatsPeriod


def store_unique_users():
    mx = InputFilesMixin()
    vfs = VendorInputFile.objects.all().order_by('period', 'vendor_id')
    uqu_data = UniqueUser.objects.values('month', 'vendor_id').distinct()
    retval = []
    for vf in vfs:
        vendor_id = vf.vendor_id
        period = dt.strptime(vf.period, "%Y-%m").date()
        if len(uqu_data.filter(month=period, vendor_id=vendor_id)) == 0:
            unique_pids = mx.load_data_for_uq_users(vf.file.path)
            if len(unique_pids) > 0:
                unique_users = [
                    UniqueUser(month=period, vendor_id=vendor_id, user_id=pid)
                    for pid in unique_pids if pid != '']
                if len(unique_users) > 0:
                    UniqueUser.objects.bulk_create(unique_users)
                    retval.append(f'{vf.file.path} - processed')
                    print(f'{vf.file.path} - processed')
    return retval


def store_uqu_client():

    sql = "select distinct c.client_id " \
          "from client_data c " \
          "join vendors v on c.client_id = v.client_id " \
          "join stats_uq_users suu on v.vendor_id = suu.vendor_id;"

    clients = Client.objects.raw(sql)
    UquStatsPeriodClient.objects.all().delete()

    for client in clients:
        vendors = list(Vendor.objects.filter(client=client).values_list('vendor_id', flat=True))
        months = list(UniqueUser.objects
                      .filter(vendor_id__in=vendors).order_by('month')
                      .values_list('month', flat=True).distinct())
        first_month = months[0]
        prior_month = first_month
        for month in months:
            print(f'{client.client_id}: {month}')
            cumulative = len(UniqueUser.objects
                             .filter(vendor_id__in=vendors, month__range=[first_month, month])
                             .values_list('user_id', flat=True).distinct())
            period_count = len(UniqueUser.objects
                               .filter(vendor_id__in=vendors, month=month)
                               .values_list('user_id', flat=True).distinct())
            prior_count = 0
            if month != first_month:
                prior_record = UquStatsPeriodClient.objects.get(period=prior_month, client=client)
                prior_count = prior_record.cumulative
            new_count = cumulative - prior_count

            UquStatsPeriodClient.objects.create(
                period=month,
                client=client,
                cumulative=cumulative,
                uqu_month=period_count,
                uqu_new=new_count
            ).save()
            prior_month = month


def store_uqu_vendors():

    vendors = UniqueUser.objects.all().values_list('vendor_id', flat=True).distinct()
    UquStatsPeriodVendor.objects.all().delete()

    for vendor_id in vendors:
        months = list(UniqueUser.objects
                      .filter(vendor_id=vendor_id).order_by('month')
                      .values_list('month', flat=True).distinct())
        first_month = months[0]
        prior_month = first_month
        for month in months:
            print(f'{vendor_id}: {month}')
            cumulative = len(UniqueUser.objects
                             .filter(vendor_id=vendor_id, month__range=[first_month, month])
                             .values_list('user_id', flat=True).distinct())
            period_count = len(UniqueUser.objects
                               .filter(vendor_id=vendor_id, month=month)
                               .values_list('user_id', flat=True).distinct())
            prior_count = 0
            if month != first_month:
                prior_record = UquStatsPeriodVendor.objects.get(period=prior_month, vendor_id=vendor_id)
                prior_count = prior_record.cumulative
            new_count = cumulative - prior_count

            UquStatsPeriodVendor.objects.create(
                period=month,
                vendor_id=vendor_id,
                cumulative=cumulative,
                uqu_month=period_count,
                uqu_new=new_count
            ).save()
            prior_month = month


def store_uqu_periods():
    UquStatsPeriod.objects.all().delete()
    months = list(UniqueUser.objects.all().order_by('month').values_list('month', flat=True).distinct())
    first_month = months[0]
    prior_month = first_month
    for month in months:
        print(f'{month}')
        cumulative = len(UniqueUser.objects.filter(month__range=[first_month, month])
                         .values_list('user_id', flat=True).distinct())
        period_count = len(UniqueUser.objects.filter(month=month)
                           .values_list('user_id', flat=True).distinct())
        prior_count = 0
        if month != first_month:
            prior_record = UquStatsPeriod.objects.get(period=prior_month)
            prior_count = prior_record.cumulative
        new_count = cumulative - prior_count

        UquStatsPeriod.objects.create(
            period=month,
            cumulative=cumulative,
            uqu_month=period_count,
            uqu_new=new_count
        ).save()
        prior_month = month
