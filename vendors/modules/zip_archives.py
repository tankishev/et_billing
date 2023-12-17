from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage

from ..models import VendorInputFile, Vendor

import zipfile as z
import os
import logging

logger = logging.getLogger(f'et_billing.{__name__}')
CLEAN_FILE_ENCODING = False  # Set to true if running in Windows environment
TEMP_ZIP_FILENAME = settings.BASE_DIR / 'media/temp_upload.zip'


def delete_inactive_input_files() -> list:
    """ Removes VendorInputFiles that are marked as inactive """

    inactive_files = VendorInputFile.objects.filter(is_active=False)
    logger.info(f'Removing {len(inactive_files)} files')
    retval = []

    for file_obj in inactive_files:
        # Get filepath
        file = file_obj.file
        filepath = file.path
        logger.debug(f'Removing {filepath}')

        # Remove file
        file_obj.delete()
        default_storage.delete(filepath)
        retval.append(filepath)

    logger.info(f'Complete removal of {len(inactive_files)} files')
    return retval


def handle_extract_zip(period: str) -> dict:
    """ Extract files from ZIP archive and creates VendorInputFile objects.
        If an objects already exists for this vendor then it is marked as inactive.
    """

    logger.info(f'Start extracting files from ZIP archive for {period}')

    # Set-up
    zip_archive = TEMP_ZIP_FILENAME
    z_file = validate_zip(zip_archive)
    retval = {
        (0, 'New vendors'): [],
        (1, 'Renamed vendors'): [],
        (2, 'No change'): []
    }
    processed_ids = []

    # Process zip archive one file at a time
    for z_obj in z_file.infolist():
        # Clean filename
        clean_name = clean_filename(z_obj.filename, clean=CLEAN_FILE_ENCODING)

        if not clean_name.startswith('__MACOSX/') and clean_name.endswith('.csv'):
            logger.debug(f'Processing {clean_name}')

            # Get vendor_id and vendor_name
            vendor_id = get_vendor_id(clean_name)
            if vendor_id is None:
                continue
            processed_ids.append(vendor_id)
            vendor_name = get_vendor_name(clean_name)

            # Check if vendor exists and update name if changed
            try:
                vendor = Vendor.objects.get(vendor_id=vendor_id)
                if vendor.iteco_name != vendor_name:
                    retval[(1, 'Renamed vendors')].append(f'{vendor}: {vendor.iteco_name} -> {vendor_name}')
                    vendor.iteco_name = vendor_name
                    vendor.save()
                else:
                    retval[(2, 'No change')].append(vendor)

            # If vendor does not exist create new vendor
            except Vendor.DoesNotExist:
                new_vendor = Vendor.objects.create(
                    vendor_id=vendor_id, client_id=0,
                    description=vendor_name, iteco_name=vendor_name, is_reconciled=False)
                new_vendor.save()
                retval[(0, 'New vendors')].append(new_vendor)

            # Check for existing VendorInputFile and mark it inactive
            try:
                existing_file = VendorInputFile.objects.get(period=period, vendor_id=vendor_id, is_active=True)
                existing_file.is_active = False
                existing_file.save()
            except VendorInputFile.DoesNotExist:
                pass

            # Create new VendorInputFile and save it
            finally:
                input_file = z_file.open(z_obj.filename)
                vendor_file = File(input_file)
                vendor_file.name = clean_name
                new_file = VendorInputFile.objects.create(period=period, vendor_id=vendor_id, file=vendor_file)
                new_file.save()

    # Add Vendors that were not in the archive in the return value
    unprocessed = Vendor.objects.exclude(vendor_id__in=processed_ids)
    retval[(3, 'Vendors not in archive')] = [el for el in unprocessed]

    logger.info(f'{len(processed_ids)} files extracted')

    return retval


def handle_uploaded_file(f) -> z.ZipFile | None:
    """ Saves uploaded file and checks if it is a valid ZIP. If valid returns ZipFile object. """

    # Save file
    filepath = TEMP_ZIP_FILENAME
    with open(filepath, 'wb+') as temp_file:
        for chunk in f.chunks():
            temp_file.write(chunk)
    temp_file.close()

    # Validate file and remove if invalid
    z_file = validate_zip(filepath)
    if z_file:
        return z_file
    os.remove(filepath)


def list_archive() -> list | None:
    """ Lists the CSV files in last uploaded zip file located at /media/temp_upload.zip """

    f = validate_zip(TEMP_ZIP_FILENAME)
    if f:
        retval = []
        for name in f.namelist():
            clean_name = clean_filename(name, clean=CLEAN_FILE_ENCODING)
            if not clean_name.startswith('__MACOSX/') and clean_name.endswith('.csv'):
                retval.append(clean_name)
        return sorted(retval)


# SUPPORTING METHODS
def clean_filename(name, clean=False) -> str:
    """ Change encoding from cp437 to utf-8"""

    if clean:
        return name.encode('cp437').decode('utf-8')
    return name


def get_vendor_id(clean_name) -> int:
    """ Get vendor id from directory name """
    file_parts = clean_name.split('_')
    vendor_id = file_parts[0]
    return int(vendor_id)


def get_vendor_name(clean_name) -> str:
    """ Generate vendor name from directory name """

    dir_parts = clean_name.split('/')
    file_parts = dir_parts[0].split('_')
    return "_".join(el for el in file_parts[1:])


def safe_open_wb(path):
    """Open "path" for writing, creating any parent directories as needed."""

    os.makedirs(os.path.dirname(path), exist_ok=True)
    return open(path, 'wb')


def validate_zip(filepath) -> z.ZipFile | None:
    """ Tests that the file is a ZipFile, and it is valid """

    if z.is_zipfile(filepath):
        z_file = z.ZipFile(filepath)
        if z_file.testzip() is None:
            return z_file
