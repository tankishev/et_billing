from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.postgres.search import SearchVector
from django.db.models import RestrictedError, Count, Subquery, Q, Exists, OuterRef
from django.db import transaction

from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from clients.models import Client, ClientCountry, Industry
from contracts.models import Contract, Order, OrderPrice, OrderService, PaymentType, Currency
from services.models import Service
from vendors.models import Vendor, VendorService, VendorFilterOverride
from reports.models import ReportFile
from stats.models import UsageStats

from . import serializers


# REST Framework calls
# Vendors (Accounts)
@csrf_exempt
@api_view(['GET'])
def vendors_list(request: Request):
    """
    Retrieves the list of all Vendors. Filters the list for given request params.
    """

    if request.method == 'GET':
        vendors = Vendor.objects.all().order_by('description')

        client_id = request.query_params.get('client_id', '')
        if client_id and client_id.isnumeric():
            vendors = vendors.filter(client_id=int(client_id))

        exclude_client_id = request.query_params.get('exclude_client_id', '')
        if exclude_client_id and exclude_client_id.isnumeric():
            vendors = vendors.exclude(client_id=int(exclude_client_id))

        description_filter = request.query_params.get('description', None)
        if description_filter:
            vendors = vendors.filter(description__icontains=description_filter)

        serializer = serializers.VendorSerializer(vendors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['GET', 'PATCH'])
def vendor_details(request: Request, pk):
    """
    Retrieves or updates the details for a given Vendor.
    """

    try:
        vendor = Vendor.objects.get(pk=pk)
    except Vendor.DoesNotExist:
        err_message = f'Account {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = serializers.VendorSerializer(vendor)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'PATCH':
        serializer = serializers.VendorSerializer(instance=vendor, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET'])
def vendor_services(request: Request, pk):

    """
    Retrieves or updates the list of Services assigned to a given Vendor.
    """

    try:
        vendor = Vendor.objects.get(pk=pk)
    except Vendor.DoesNotExist:
        err_message = f'Account {pk} does not exist.'
        return Response(data={'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        vs_objects = VendorService.objects.filter(vendor=vendor)
        vs_serializer = serializers.VendorServiceSerializer(vs_objects, many=True)
        return Response(vs_serializer.data, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
def vendor_services_add(request: Request, pk):
    """
    Assigns Services to a given Vendor.
    """

    try:
        vendor = Vendor.objects.get(pk=pk)
    except Vendor.DoesNotExist:
        err_message = f'Account {pk} does not exist.'
        return Response(data={'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        serializer = serializers.ServiceIDListSerializer(data=request.data)
        if serializer.is_valid():
            ids = serializer.data.get('ids', [])
            existing_ids = VendorService.objects.filter(vendor=vendor, service_id__in=ids)\
                .values_list('service_id', flat=True)
            objs = [VendorService(vendor=vendor, service_id=el) for el in ids if el not in list(existing_ids)]
            if objs:
                VendorService.objects.bulk_create(objs)
            return redirect('get_vendor_services', pk=pk)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
def vendor_services_remove(request: Request, pk):

    """
    Removes Services from a given Vendor.
    """

    try:
        vendor = Vendor.objects.get(pk=pk)
    except Vendor.DoesNotExist:
        err_message = f'Account {pk} does not exist.'
        return Response(data={'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        serializer = serializers.VendorServiceIDsSerializer(data=request.data)
        if serializer.is_valid():
            ids = serializer.data.get('ids', [])
            vs_to_delete = VendorService.objects.filter(pk__in=ids)\
                .annotate(orderservices_count=Count('orderservice')).filter(orderservices_count=0)
            services_to_delete_filters = list(vs_to_delete.values_list('service_id', flat=True))
            vs_to_delete.delete()
            VendorFilterOverride.objects.filter(vendor=vendor, service_id__in=services_to_delete_filters).delete()
            return redirect('get_vendor_services', pk=pk)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET'])
def vendor_services_duplicate(request: Request, pk):
    """
    Replicate the VendorServices & VendorServiceOverride from another vendor
    :return: Details for the new services
    """

    if request.method == 'GET':
        try:
            target_vendor = Vendor.objects.get(pk=pk)
        except Vendor.DoesNotExist:
            err_message = f'Target account account does not exist.'
            return Response(data={'message': err_message}, status=status.HTTP_404_NOT_FOUND)

        target_os = OrderService.objects.filter(service__vendor=target_vendor)
        if not target_os:
            source_id = request.query_params.get('source_id', None)
            if source_id and source_id.isnumeric():
                try:
                    source_vendor = Vendor.objects.get(pk=int(source_id))
                except Vendor.DoesNotExist:
                    err_message = f'Source account does not exist.'
                    return Response(data={'message': err_message}, status=status.HTTP_404_NOT_FOUND)

                VendorFilterOverride.objects.filter(vendor=target_vendor).delete()
                VendorService.objects.filter(vendor=target_vendor).delete()

                source_vs = VendorService.objects.filter(vendor=source_vendor)
                for vs in source_vs:
                    VendorService.objects.create(vendor=target_vendor, service=vs.service)
                    source_vfo = VendorFilterOverride.objects.filter(vendor=source_vendor, service=vs.service)
                    if source_vfo.exists():
                        vfo = source_vfo.first()
                        VendorFilterOverride.objects.create(
                            vendor=target_vendor, service=vs.service, filter=vfo.filter)
                target_vs = VendorService.objects.filter(vendor=target_vendor)
                serializer = serializers.VendorServiceSerializer(target_vs, many=True)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            err_message = f'Invalid or missing source_id.'
            return Response(data={'message': err_message}, status=status.HTTP_400_BAD_REQUEST)

        err_message = f'Account {pk} has services associated with orders.'
        return Response(data={'message': err_message}, status=status.HTTP_400_BAD_REQUEST)


# Clients
@csrf_exempt
@api_view(['GET', 'POST'])
def clients_list(request: Request):

    """
    Retrieve list of Clients or Creates new client.
    """

    if request.method == 'GET':
        clients = Client.objects.all().order_by('reporting_name')

        search_value = request.query_params.get('search', None)
        if search_value:
            search_vector = SearchVector('client_id', 'legal_name', 'reporting_name')
            clients = clients.annotate(search=search_vector).filter(search=search_value)

        serializer = serializers.ClientSerializer(clients, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'POST':
        serializer = serializers.ClientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET', 'PUT', 'DELETE'])
def client_details(request: Request, pk):

    """
    Retrieves, updates or deletes a Client record.
    """

    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        err_message = f'Client {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = serializers.ClientSerializer(client)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        data = request.data
        serializer = serializers.ClientSerializer(client, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        try:
            client.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except RestrictedError as err:
            err_message = f'Cannot delete client {client} ' \
                      f'because it has {len(err.restricted_objects)} restricted objects assigned to it.'
            return Response({'message': err_message}, status=status.HTTP_409_CONFLICT)


@csrf_exempt
@api_view(['GET', 'POST'])
def client_vendors(request: Request, pk):

    """
    Retrieve the Vendors list for a given Client.
    Assigns a list of vendors to the given Client.
    """

    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        err_message = f'Client {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        vendors = Vendor.objects.filter(client=client)
        serializer = serializers.VendorSerializer(vendors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method in ['POST']:
        serializer = serializers.VendorsListSerializer(data=request.data)
        if serializer.is_valid():
            vendor_ids = serializer.data.get('ids', [])
            Vendor.objects.filter(vendor_id__in=vendor_ids).update(client=client)
            vendors = Vendor.objects.filter(client=client)
            serializer = serializers.VendorSerializer(vendors, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET'])
def client_services(request: Request, pk):

    """
    Retrieves the list of Services associated with a given Client.
    Can filter the ones already associated with active Orders.
    """

    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        err_message = f'Client {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        services = VendorService.objects.filter(vendor__client=client)

        exclude_assigned = request.query_params.get('exclude_assigned', False)
        if exclude_assigned == 'true':
            client_active_orders = Order.objects\
                .filter(is_active=True, contract__client=client)
            assigned_services = VendorService.objects\
                .filter(orderservice__order__in=client_active_orders).values_list('id', flat=True)
            services = services.exclude(pk__in=assigned_services)

        order_id = request.query_params.get('order_id', None)
        if order_id:
            try:
                order = Order.objects.get(pk=order_id)
                services = services.filter(orderservice__order=order)
            except Order.DoesNotExist:
                err_message = f'Order {pk} does not exist.'
                return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

            except ValueError as err:
                err_message = f'Value error: {err}'
                return Response({'message': err_message}, status=status.HTTP_400_BAD_REQUEST)

        paginator = PageNumberPagination()
        paginator.page_size = 20
        results_page = paginator.paginate_queryset(services, request)
        serializer = serializers.VendorServiceSerializer(results_page, many=True)
        return paginator.get_paginated_response(serializer.data)
        # serializer = serializers.VendorServiceSerializer(services, many=True)
        # return Response(serializer.data, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['GET', 'POST'])
def contracts_list(request: Request):

    """
    Retrieve the list of a Contracts or creates a new one.
    """

    if request.method == 'GET':
        contracts = Contract.objects.all()
        serializer = serializers.ContractListSerializer(contracts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'POST':
        serializer = serializers.ContractSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET', 'PATCH', 'DELETE'])
def contract_details(request: Request, pk):

    """
    Retrieve the details of a Contract including list of associated orders.
    Updates the details of the Contract or deletes the Contract instance.
    """

    try:
        contract = Contract.objects.get(pk=pk)
    except Contract.DoesNotExist:
        err_message = f'Contract {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = serializers.ContractSerializer(contract)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'PATCH':
        serializer = serializers.ContractSerializer(instance=contract, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        try:
            contract.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except RestrictedError as err:
            message = f'Cannot delete contract {contract} ' \
                      f'because it has {len(err.restricted_objects)} orders assigned to it.'
            return Response({'message': message}, status=status.HTTP_409_CONFLICT)


@csrf_exempt
@api_view(['GET'])
def contract_orders(request: Request, pk):

    """
    Retrieves the list of Orders associated with a Contract.
    """

    try:
        contract = Contract.objects.get(pk=pk)
    except Contract.DoesNotExist:
        err_message = f'Contract {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        orders = contract.orders.order_by('-is_active', '-start_date')
        serializer = serializers.OrderSerializerVerbose(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Orders
@csrf_exempt
@api_view(['POST'])
def orders_list(request: Request):

    """ Create a new Order """

    if request.method == 'POST':
        serializer = serializers.OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET', 'PATCH', 'DELETE'])
def order_details(request: Request, pk):

    """
    Retrieves or updates the details for a given Order.
    Deletes the Order record.
    """

    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        err_message = f'Order {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = serializers.OrderRelated(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'PATCH':
        serializer = serializers.OrderSerializer(instance=order, data=request.data, partial=True)
        if serializer.is_valid():
            if serializer.validated_data.get('is_active') and not order.contract.is_active:
                message = f'Cannot activate Order {pk} because Contract {order.contract.contract_id} is not active'
                return Response({'message': message}, status=status.HTTP_409_CONFLICT)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        try:
            order.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except RestrictedError as err:
            message = f'Cannot delete order {order} ' \
                      f'because it has {len(err.restricted_objects)} packages assigned to it.'
            return Response({'message': message}, status=status.HTTP_409_CONFLICT)


@csrf_exempt
@api_view(['GET'])
def order_duplicate(request: Request, pk):

    """ Duplicates an existing order if it is inactive
    """

    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        err_message = f'Order {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        try:
            with transaction.atomic():
                # Duplicate the order
                new_order = Order.objects.create(
                    contract=order.contract,
                    start_date=order.start_date,
                    description=order.description,
                    ccy_type=order.ccy_type,
                    tu_price=order.tu_price,
                    payment_type=order.payment_type,
                    is_active=order.is_active
                )

                # Duplicate OrderService
                new_services = [
                    OrderService(
                        order=new_order,
                        service=os.service
                    ) for os in OrderService.objects.filter(order=order)
                ]
                if new_services:
                    OrderService.objects.bulk_create(new_services)

                # Prepare OrderPrice for bulk creation
                new_prices = [
                    OrderPrice(
                        order=new_order,
                        service=op.service,
                        unit_price=op.unit_price
                    ) for op in OrderPrice.objects.filter(order=order)
                ]
                if new_prices:
                    OrderPrice.objects.bulk_create(new_prices)

            serializer = serializers.OrderSerializerVerbose(new_order)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


@csrf_exempt
@api_view(['GET'])
def order_service_prices(request: Request, pk):

    """
    Retrieve data for OrderPrice objects associated with a given Order.
    """

    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        err_message = f'Order {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        order_prices = OrderPrice.objects.filter(order=order)
        serializer = serializers.OrderPriceSerializer(order_prices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['PATCH'])
def order_service_edit(request: Request, pk):

    try:
        op = OrderPrice.objects.get(pk=pk)
    except OrderPrice.DoesNotExist:
        err_message = f'OrderPrice object {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PATCH':
        serializer = serializers.OrderPriceSerializer(instance=op, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET'])
def order_services(request: Request, pk):

    """
    Retrieve data for the OrderService objects assigned to a given Orders.
    """

    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        err_message = f'Order {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        services = OrderService.objects.filter(order=order)\
            .order_by('service__service__service_order', 'service__vendor_id')
        serializer = serializers.OrderServiceSerializerVerbose(services, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
def order_services_add(request: Request, pk):

    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        err_message = f'Order {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST' and order.is_active:
        serializer = serializers.VendorServiceIDsSerializer(data=request.data)
        if serializer.is_valid():
            services = serializer.data.get('ids', [])
            for vs_id in services:
                try:
                    vs = VendorService.objects.get(pk=vs_id)
                    os = OrderService.objects.filter(service=vs, order=order)
                    if not os.exists():
                        OrderService.objects.create(service=vs, order=order)
                        OrderPrice.objects.get_or_create(order=order, service=vs.service, unit_price=0)
                except VendorService.DoesNotExist:
                    pass
            request.method = 'GET'
            return redirect('get_order_services', pk=pk)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return Response({'message': 'Cannot make changes to inactive Orders.'}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
def order_services_remove(request: Request, pk):

    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        err_message = f'Order {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST' and order.is_active:
        serializer = serializers.VendorServiceIDsSerializer(data=request.data)
        if serializer.is_valid():
            services = serializer.data.get('ids', [])
            for vs_id in services:
                try:
                    vs = VendorService.objects.get(pk=vs_id)
                    os = OrderService.objects.filter(order=order, service=vs)
                    os.delete()
                except VendorService.DoesNotExist:
                    pass
                except OrderService.DoesNotExist:
                    pass
            os_ids = OrderService.objects.filter(order=order).values_list('service__service__service_id', flat=True)
            for op in OrderPrice.objects.filter(order=order):
                if op.service_id not in os_ids:
                    op.delete()
            return redirect('get_order_services', pk=pk)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return Response({'message': 'Cannot make changes to inactive Orders.'}, status=status.HTTP_400_BAD_REQUEST)


# Reports
@csrf_exempt
@api_view(['GET'])
def client_reports_list(request: Request, pk):

    """ Returns a list of report files for the client """

    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        err_message = f'Client {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        report_files = ReportFile.objects\
            .filter(report__client=client, report__is_active=True).order_by('-period', 'report__file_name')
        rf_serializer = serializers.ReportFileSerializer(report_files, many=True)
        return Response(rf_serializer.data, status=status.HTTP_200_OK)


# Metadata
@csrf_exempt
@api_view(['GET'])
def get_metadata(request: Request):

    """ Returns global configs """

    if request.method == 'GET':
        pmt_types = PaymentType.objects.all()
        ccy_types = Currency.objects.all()
        services = Service.objects.all().order_by('service_order')
        countries = ClientCountry.objects.all().order_by('country')
        industries = Industry.objects.all().order_by('industry')

        pmt_serializer = serializers.PaymentTypeSerializer(pmt_types, many=True)
        ccy_serializer = serializers.CurrencySerializer(ccy_types, many=True)
        services_serializer = serializers.ServiceSerializer(services, many=True)
        industries_serializer = serializers.IndustrySerializer(industries, many=True)
        countries_serializer = serializers.CountrySerializer(countries, many=True)

        data = {
            'pmtTypes': pmt_serializer.data,
            'ccyTypes': ccy_serializer.data,
            'services': services_serializer.data,
            'industries': industries_serializer.data,
            'countries': countries_serializer.data
        }
        return Response(data, status=status.HTTP_200_OK)


# HealthCheck
@csrf_exempt
@api_view(['GET'])
def health_check(request: Request, pk):

    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        err_message = f'Client {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    retval = []

    if request.method == 'GET':

        # Same vendorService in more than one active order
        vs = VendorService.objects\
            .filter(orderservice__order__is_active=True, vendor__client=client)\
            .annotate(num_count=Count('orderservice')).filter(num_count__gt=1)\
            .order_by('vendor_id', 'service_id')
        if vs.exists():
            retval.append({
                'description': 'Account services present in more than one active orders',
                'values': [f'Account {el.vendor_id}: service {el.service_id}' for el in vs]
            })

        # VendorServices not in orders
        os_to_exclude = OrderService.objects.filter(order__contract__client=client, order__is_active=True).values('pk')
        vs = VendorService.objects.filter(vendor__client=client)\
            .exclude(orderservice__in=Subquery(os_to_exclude))\
            .order_by('vendor_id', 'service_id')
        if vs.exists():
            retval.append({
                'description': 'Account services not included in active orders',
                'values': [f'Account {el.vendor_id}: service {el.service_id}' for el in vs]
            })

        # Active contracts with no active orders
        c = Contract.objects.filter(client=client, is_active=True)\
            .annotate(active_order_count=Count(
                'orders',
                filter=Q(orders__is_active=True),
                distinct=True
            )
        ).filter(active_order_count=0)
        if c.exists():
            retval.append({
                'description': 'Active contracts with no active orders',
                'values': [str(el) for el in c]
            })

        # Usage data with no accounts service
        vs_set = VendorService.objects.filter(
            vendor=OuterRef('vendor'),
            service=OuterRef('service')
        )
        unmatched_us = UsageStats.objects.filter(vendor__client=client).exclude(
            Exists(vs_set)
        ).order_by('period', 'vendor_id', 'service_id')
        if unmatched_us.exists():
            values = [f'{el.period}: account {el.vendor_id} service {el.service_id}' for el in unmatched_us]
            retval.append({
                'description': 'Service usage without associated account',
                'values': values
            })

        return Response(data=retval, status=status.HTTP_200_OK)
