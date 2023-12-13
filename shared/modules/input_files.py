from typing import Union, Iterator, NamedTuple, List
from django.conf import settings

from pandas import DataFrame
import pandas as pd


class UnsupportedExtensionError(Exception):
    """Exception raised for unsupported file extensions."""
    def __init__(self, extension, message="Unsupported file extension"):
        self.extension = extension
        self.message = f"{message}: {extension}"
        super().__init__(self.message)


class InputFilesMixin:
    """ Mixing adding methods to load vendor input files into DataFrames.
        This class should be used for any operations that requires reading and using information from raw input files.
        This mixin class should be updated any time there are changes to the structure or type of the input files.
    """

    _INPUT_FILES_ALLOWED_EXTENSIONS = ('xlsx', 'xls', 'csv')
    _FILE_NUMERIC_COLS = ['Vendor ID', 'Status', 'Type', 'Signing type', 'Cost', 'Cost EUR', 'TransValue']
    _FILE_PID_COLS = ['PID receiver', 'PID sender']

    def load_data(self, filename: str) -> Union[DataFrame, None]:
        """ Returns a DataFrame given vendor input filename """

        ext = filename.split('.')[-1]
        if ext not in self._INPUT_FILES_ALLOWED_EXTENSIONS:
            raise UnsupportedExtensionError(ext)

        if ext in ('xlsx', 'xls'):
            return pd.read_excel(filename, keep_default_na=False, dtype=str)
        return pd.read_csv(filename, keep_default_na=False, low_memory=False, dtype=str)

    def load_data_multiple(self, filenames: Iterator) -> Union[DataFrame, None]:
        """ Load multiple Vendor report files and concatenates them in one DataFrame.
            Returns the dataframe.
        """
        if not hasattr(filenames, '__iter__'):
            raise TypeError(f"The provided input of type {type(filenames)} is not iterable.")

        df = None
        for filename in filenames:
            try:
                input_filepath = str(settings.BASE_DIR / filename)
                if df is None:
                    df = self.load_data(input_filepath)
                df = pd.concat([df, self.load_data(input_filepath)], axis=0, ignore_index=True)
            except UnsupportedExtensionError:
                pass
        return df

    def load_data_for_service_usage(self, filename: Union[str, Iterator], skip_status_five=False)\
            -> Union[DataFrame, None]:
        """ Loads data from a given filename or list of filenames.
            Prepares the data for service usage calculations.
            Returns a DataFrame with the prepared data.
            :param filename: filename or list with filenames
            :param skip_status_five: if True will remove rows where Status field equals 5
        """

        if type(filename) == str:
            df = self.load_data(filename)
        else:
            df = self.load_data_multiple(filename)

        if not df.empty:
            return self.prep_df_for_service_usage_calc(df, skip_status_five)

    def load_data_for_uq_countries(self, filename, skip_status_five=True) -> Iterator[NamedTuple]:
        df = self.load_data(filename)
        if 'Status' in df.columns and skip_status_five:
            df = df[df.Status != '5'][["Country receiver", "PID receiver"]].drop_duplicates()
        else:
            df = df[["Country receiver", "PID receiver"]].drop_duplicates()
        return df.itertuples(index=False)

    def load_data_for_uq_users(self, filename: str) -> List[str]:
        """ Returns the list of unique PID Receiver in an vendor file"""

        df = self.load_data(filename)
        if 'Status' in df.columns:
            return list(df[df.Status != '5']['PID receiver'].unique())
        return list(df['PID receiver'].unique())

    def prep_df_for_service_usage_calc(self, df: DataFrame, skip_status_five=False) -> DataFrame:
        """ Takes a dataframe, replaces n/a with blank string, removes rows with status 5
        and converts specific columns from string to numeric representation.
        """

        df.fillna('', inplace=True)
        if skip_status_five and 'Status' in df.columns:
            df.drop(df[df['Status'] == '5'].index, inplace=True)

        for c_name in df.columns:
            if c_name in self._FILE_NUMERIC_COLS:
                df[c_name] = pd.to_numeric(df[c_name])
        return df
