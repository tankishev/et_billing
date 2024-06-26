from django.contrib.postgres.search import SearchVector, TrigramSimilarity
from django.core.exceptions import ValidationError
from django.core.validators import validate_integer
from django.db.models import RestrictedError, Count
from django.db import transaction
from django.shortcuts import redirect

from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from celery_tasks.models import FileProcessingTask
from clients.models import Client, ClientCountry, Industry
from contracts.models import Contract, Order, OrderPrice, OrderService, PaymentType, Currency
from services.models import Service
from stats.modules.usage_calculations import recalc_vendor
from reports.models import ReportFile, Report, ReportSkipColumnConfig, ReportLanguage
from reports.modules import gen_report_for_client, gen_report_by_id
from reports.modules.report import health_check as hc
from vendors.models import Vendor, VendorService, VendorFilterOverride

from . import serializers
import logging

logger = logging.getLogger(f'et_billing.{__name__}')


# REST Framework calls

# Vendors (Accounts)
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

        report_id = request.query_params.get('report_id', '')
        if report_id and report_id.isnumeric():
            try:
                report = Report.objects.get(pk=int(report_id))
                report_vendors = report.values_list('vendors__vendor_id', flat=True)
                vendors = vendors.filter(vendor_id__in=report_vendors)
            except Report.DoesNotExist:
                pass

        exclude_client_id = request.query_params.get('exclude_client_id', '')
        if exclude_client_id and exclude_client_id.isnumeric():
            vendors = vendors.exclude(client_id=int(exclude_client_id))

        description_filter = request.query_params.get('description', None)
        if description_filter:
            vendors = vendors.filter(description__icontains=description_filter)

        serializer = serializers.VendorSerializer(vendors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
def vendor_calculate_usage(request: Request):
    if request.method == 'POST':
        logger.info('Received a POST request')

        serializer = serializers.VendorPeriodSerializer(data=request.data)
        if serializer.is_valid():
            period = serializer.validated_data.get('period').strftime('%Y-%m')
            vendor = serializer.validated_data.get('vendor')
            logger.info(f"Starting usage calculation task for period {period} and account {vendor.vendor_id}")

            async_result = recalc_vendor.delay(period, vendor.vendor_id)
            logger.info(f"Report generation task queued with task_id {async_result.id}")

            return Response({'taskId': async_result.id}, status=status.HTTP_202_ACCEPTED)

        logger.warning(f"Serialization errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
            existing_ids = VendorService.objects.filter(vendor=vendor, service_id__in=ids) \
                .values_list('service_id', flat=True)
            objs = [VendorService(vendor=vendor, service_id=el) for el in ids if el not in list(existing_ids)]
            if objs:
                VendorService.objects.bulk_create(objs)
            return redirect('get_vendor_services', pk=pk)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
            vs_to_delete = VendorService.objects.filter(pk__in=ids) \
                .annotate(orderservices_count=Count('orderservice')).filter(orderservices_count=0)
            services_to_delete_filters = list(vs_to_delete.values_list('service_id', flat=True))
            vs_to_delete.delete()
            VendorFilterOverride.objects.filter(vendor=vendor, service_id__in=services_to_delete_filters).delete()
            return redirect('get_vendor_services', pk=pk)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
@api_view(['GET', 'POST'])
def clients_list(request: Request):
    """
    Retrieve list of Clients or Creates new client.
    """

    if request.method == 'GET':
        clients = Client.objects.all().order_by('reporting_name')

        search_value = request.query_params.get('search', None)
        try:
            validate_integer(search_value)
            search_value_is_integer = True
        except ValidationError:
            search_value_is_integer = False

        if search_value_is_integer:
            clients = clients.filter(pk=search_value)
        else:
            threshold = 0.2
            clients = clients.annotate(
                similarity=TrigramSimilarity('legal_name', search_value) +
                           TrigramSimilarity('reporting_name', search_value)
            ).filter(similarity__gt=threshold)

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

    if request.method == 'POST':
        serializer = serializers.VendorsListSerializer(data=request.data)
        if serializer.is_valid():
            vendor_ids = serializer.data.get('ids', [])
            Vendor.objects.filter(vendor_id__in=vendor_ids).update(client=client)
            vendors = Vendor.objects.filter(client=client)
            serializer = serializers.VendorSerializer(vendors, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
            client_active_orders = Order.objects \
                .filter(is_active=True, contract__client=client)
            assigned_services = VendorService.objects \
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
@api_view(['POST'])
def orders_list(request: Request):
    """ Create a new Order """

    if request.method == 'POST':
        serializer = serializers.OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
                    end_date=order.end_date,
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
        services = OrderService.objects.filter(order=order) \
            .order_by('service__service__service_order', 'service__vendor_id')
        serializer = serializers.OrderServiceSerializerVerbose(services, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
@api_view(['GET'])
def client_reports_list(request: Request, pk):
    """ Returns a list of Reports for a given Client """

    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        err_message = f'Client {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        reports = Report.objects.filter(client=client, is_active=True)
        reports_serializer = serializers.ClientReportListSerializer(reports, many=True)
        return Response(reports_serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def client_report_files_list(request: Request, pk):
    """ Returns a list of report files for the client """

    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        err_message = f'Client {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        report_files = ReportFile.objects \
            .filter(report__client=client, report__is_active=True).order_by('-period', 'report__file_name')
        rf_serializer = serializers.ReportFileSerializer(report_files, many=True)
        return Response(rf_serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
def client_create_report(request: Request, pk):
    """
    Creates a new Report for a given Client
    """

    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        err_message = f'Client {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        data = request.data.copy()
        if 'client' not in data:
            data['client'] = client.pk

        serializer = serializers.ReportSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
def report_details(request: Request, pk):
    """
    Retrieves or updates the details for a given Report.
    Deletes the Report record.
    """

    try:
        report = Report.objects.get(pk=pk)
    except Report.DoesNotExist:
        err_message = f'Report {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = serializers.ReportSerializer(report)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'PATCH':
        serializer = serializers.ReportSerializer(instance=report, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        try:
            report.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except RestrictedError as err:
            message = f'Cannot delete report {report} ' \
                      f'because it has {len(err.restricted_objects)} related objects assigned to it. ' \
                      f'Mark it as inactive instead.'
            return Response({'message': message}, status=status.HTTP_409_CONFLICT)


@api_view(['PUT'])
def report_update_vendors(request: Request, pk):
    """
    Updates the list of vendors for a given Report.
    """

    try:
        report = Report.objects.get(pk=pk)
    except Report.DoesNotExist:
        err_message = f'Report {pk} does not exist.'
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        serializer = serializers.ReportVendorUpdateSerializer(report, data=request.data)
        if serializer.is_valid():
            serializer.save()
            vendors = report.vendors.values('vendor_id', 'description')
            vendors_list_serializer = serializers.VendorSerializerBasic(vendors, many=True)
            return Response(vendors_list_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def report_render_period_client(request: Request):
    if request.method == 'POST':

        logger.info('Received a POST request')

        serializer = serializers.ClientPeriodSerializer(data=request.data)
        if serializer.is_valid():
            period = serializer.validated_data.get('period').strftime('%Y-%m')
            client = serializer.validated_data.get('client')
            logger.info(f"Starting report generation task for period {period} and client {client.pk}")

            async_result = gen_report_for_client.delay(period, client.client_id)
            logger.info(f"Report generation task queued with task_id {async_result.id}")

            return Response({'taskId': async_result.id}, status=status.HTTP_202_ACCEPTED)

        logger.warning(f"Serialization errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def report_render_period_report(request: Request):
    if request.method == 'POST':

        logger.info('Received a POST request')

        serializer = serializers.ReportPeriodSerializer(data=request.data)
        if serializer.is_valid():
            period = serializer.validated_data.get('period').strftime('%Y-%m')
            report = serializer.validated_data.get('report')
            logger.info(f"Starting report generation task for period {period} and report {report.pk}")

            async_result = gen_report_by_id.delay(period, report.pk)
            logger.info(f"Report generation task queued with task_id {async_result.id}")

            return Response({'taskId': async_result.id}, status=status.HTTP_202_ACCEPTED)

        logger.warning(f"Serialization errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Metadata
@api_view(['GET'])
def get_metadata(request: Request):
    """ Returns global configs """

    if request.method == 'GET':
        pmt_types = PaymentType.objects.all()
        ccy_types = Currency.objects.all()
        services = Service.objects.all().order_by('service_order')
        countries = ClientCountry.objects.all().order_by('country')
        industries = Industry.objects.all().order_by('industry')
        skip_columns = ReportSkipColumnConfig.objects.all()
        report_language = ReportLanguage.objects.all()

        pmt_serializer = serializers.PaymentTypeSerializer(pmt_types, many=True)
        ccy_serializer = serializers.CurrencySerializer(ccy_types, many=True)
        services_serializer = serializers.ServiceSerializer(services, many=True)
        industries_serializer = serializers.IndustrySerializer(industries, many=True)
        countries_serializer = serializers.CountrySerializer(countries, many=True)
        skip_columns_serializer = serializers.ReportSkipColumnsSerializer(skip_columns, many=True)
        report_language_serializer = serializers.ReportLanguageSerializer(report_language, many=True)

        data = {
            'pmtTypes': pmt_serializer.data,
            'ccyTypes': ccy_serializer.data,
            'services': services_serializer.data,
            'industries': industries_serializer.data,
            'countries': countries_serializer.data,
            'skipColumns': skip_columns_serializer.data,
            'reportLanguages': report_language_serializer.data
        }
        return Response(data, status=status.HTTP_200_OK)


# HealthCheck
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
        vs_qs = hc.get_duplicated_account_services_in_active_orders(client.client_id)
        if vs_qs.exists():
            retval.append({
                'description': 'Account services present in more than one active orders',
                'values': [f'Account {el.vendor_id}: service {el.service_id}' for el in vs_qs]
            })

        # VendorServices not in orders
        vs_qs = hc.get_account_service_not_in_active_orders(client.client_id)
        if vs_qs.exists():
            retval.append({
                'description': 'Account services not included in active orders',
                'values': [f'Account {el.vendor_id}: service {el.service_id}' for el in vs_qs]
            })

        # Active contracts with no active orders
        contracts_qs = hc.get_active_contracts_without_active_orders(client.client_id)
        if contracts_qs.exists():
            retval.append({
                'description': 'Active contracts with no active orders',
                'values': [str(el) for el in contracts_qs]
            })

        # Usage data with no accounts service
        unmatched_us = hc.get_usage_data_without_account_service(client.client_id)
        if unmatched_us.exists():
            values = [f'{el.period}: account {el.vendor_id} service {el.service_id}' for el in unmatched_us]
            retval.append({
                'description': 'Service usage without associated account',
                'values': values
            })

        # Usage data with no OrderService
        report_data = hc.get_usage_without_orders(client.client_id)
        if report_data:
            report_data = sorted(report_data, key=lambda x: x[0])
            values = [f'{el[0]}: account {el[1][0]} service {el[1][1]}' for el in report_data]
            retval.append({
                'description': 'Service usage not included in active orders',
                'values': values
            })

        return Response(data=retval, status=status.HTTP_200_OK)


# Celery Tasks
@api_view(['GET'])
def get_task_list(request: Request):
    """ Gets the list of celery tasks in the DB """

    if request.method == 'GET':
        logger.info('Received a GET request')

        tasks = FileProcessingTask.objects.filter(status='COMPLETE')
        serializer = serializers.CeleryTaskSerializer(tasks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_task_progress(request: Request, task_id: str):
    """ Gets the status of a Celery task provided its task_id """
    logger.info(f'Received a {request.method} request for task {task_id}')

    try:
        task = FileProcessingTask.objects.get(task_id=task_id)
    except FileProcessingTask.DoesNotExist:
        err_message = f'No records for file processing task {task_id}. ' \
                      f'Server might be busy. Please wait before you resubmit the request.'
        logger.warning(err_message)
        return Response({'message': err_message}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = serializers.CeleryTaskSerializer(task, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)
