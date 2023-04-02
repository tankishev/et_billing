from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from ..models import VendorInputFile, Vendor
import zipfile as z
import os

TEMP_ZIP_FILENAME = settings.BASE_DIR / 'media/temp_upload.zip'


def clean_filename(name, clean=False):
    if clean:
        return name.encode('cp437').decode('utf-8')
    return name


def handle_uploaded_file(f):
    """ Saves uploaded files and list any CSV content """

    filepath = TEMP_ZIP_FILENAME
    with open(filepath, 'wb+') as temp_file:
        for chunk in f.chunks():
            temp_file.write(chunk)
    temp_file.close()
    z_file = validate_zip(filepath)
    if z_file:
        return z_file
    os.remove(filepath)


def list_archive() -> list or None:
    """ Lists the CSV files in last uploaded zip file located at /media/temp_upload.zip """

    f = validate_zip(TEMP_ZIP_FILENAME)
    if f:
        retval = []
        for name in f.namelist():
            clean_name = clean_filename(name)
            if not clean_name.startswith('__MACOSX/') and clean_name.endswith('.csv'):
                retval.append(clean_name)
        return sorted(retval)


def validate_zip(filepath) -> z.ZipFile or None:
    """ Tests that the file is a ZipFile and it is valid
        :returns ZipFile or None
    """

    if z.is_zipfile(filepath):
        z_file = z.ZipFile(filepath)
        if z_file.testzip() is None:
            return z_file


def handle_extract_zip(period):
    zip_archive = TEMP_ZIP_FILENAME
    z_file = validate_zip(zip_archive)
    retval = {
        (0, 'New vendors'): [],
        (1, 'Renamed vendors'): [],
        (2, 'No change'): []
    }
    processed_ids = []
    for z_obj in z_file.infolist():
        clean_name = clean_filename(z_obj.filename)
        if not clean_name.startswith('__MACOSX/') and clean_name.endswith('.csv'):
            vendor_id = get_vendor_id(clean_name)
            if vendor_id is None:
                continue
            processed_ids.append(vendor_id)
            vendor_name = get_vendor_name(clean_name)
            try:
                vendor = Vendor.objects.get(vendor_id=vendor_id)
                if vendor.iteco_name != vendor_name:
                    retval[(1, 'Renamed vendors')].append(f'{vendor}: {vendor.iteco_name} -> {vendor_name}')
                    vendor.iteco_name = vendor_name
                    vendor.save()
                else:
                    retval[(2, 'No change')].append(vendor)
            except Vendor.DoesNotExist:
                new_vendor = Vendor.objects.create(
                    vendor_id=vendor_id, client_id=0,
                    description=vendor_name, iteco_name=vendor_name, is_reconciled=False)
                new_vendor.save()
                retval[(0, 'New vendors')].append(vendor)
            try:
                existing_file = VendorInputFile.objects.get(period=period, vendor_id=vendor_id, is_active=True)
                existing_file.is_active = False
                existing_file.save()
            except VendorInputFile.DoesNotExist:
                pass
            finally:
                input_file = z_file.open(z_obj.filename)
                vendor_file = File(input_file)
                vendor_file.name = clean_name
                new_file = VendorInputFile.objects.create(period=period, vendor_id=vendor_id, file=vendor_file)
                new_file.save()

    unprocessed = Vendor.objects.exclude(vendor_id__in=processed_ids)
    retval[(3, 'Vendors not in archive')] = [el for el in unprocessed]
    return retval


def safe_open_wb(path):
    """Open "path" for writing, creating any parent directories as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return open(path, 'wb')


def get_vendor_id(clean_name):
    file_parts = clean_name.split('_')
    vendor_id = file_parts[0]
    return int(vendor_id)


def get_vendor_name(clean_name):
    dir_parts = clean_name.split('/')
    file_parts = dir_parts[0].split('_')
    return "_".join(el for el in file_parts[1:])


def delete_inactive_input_files():
    retval = []
    inactive_files = VendorInputFile.objects.filter(is_active=False)
    for file_obj in inactive_files:
        file = file_obj.file
        filepath = file.path

        file_obj.delete()
        default_storage.delete(filepath)
        retval.append(filepath)
    return retval
