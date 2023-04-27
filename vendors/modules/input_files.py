# ADD UNIQUE COUNTRIES .. ADD LOGGER
from django.conf import settings

import pandas as pd


class InputFilesMixin:
    """ Mixing adding methods to load input files into DataFrames """

    _INPUT_FILES_ALLOWED_EXTENSIONS = ('xlsx', 'xls', 'csv')
    _FILE_NUMERIC_COLS = ['Vendor ID', 'Status', 'Type', 'Signing type', 'Cost', 'Cost EUR']
    _FILE_PID_COLS = ['PID receiver', 'PID sender']

    def load_data(self, filename) -> pd.DataFrame | None:
        """ Returns a DataFrame given vendor input filename """

        ext = filename.split('.')[-1]
        if ext in self._INPUT_FILES_ALLOWED_EXTENSIONS:
            if ext in ('xlsx', 'xls'):
                df = pd.read_excel(filename, keep_default_na=False, dtype=str)
            else:
                df = pd.read_csv(filename, keep_default_na=False, low_memory=False, dtype=str)
            return df

    def load_data_for_service_usage(self, filename, skip_status_five=False) -> pd.DataFrame | None:
        """ Returns a DataFrame given a filename or list of filenames
        :param filename: filename or list with filenames
        :param skip_status_five: if True will remove rows where Status field equals 5
        """

        if type(filename) == str:
            df = self.load_data(filename)
        else:
            df = self.load_multiple(filename)

        if not df.empty:
            return self.prep_df_for_service_usage_calc(df, skip_status_five)

    def load_multiple(self, filenames) -> pd.DataFrame:
        """ Load multiple Vendor report files and concatenates them in one DataFrame.
            Returns the dataframe.
        """

        df = None
        for filename in filenames:
            input_filepath = str(settings.BASE_DIR / filename)
            if df is None:
                df = self.load_data(input_filepath)
            df = pd.concat([df, self.load_data(input_filepath)], axis=0, ignore_index=True)
        return df

    # def load_data_for_uq_countries(self, filename, skip_status_five=True) -> pd.DataFrame:
    #     df = self.load_data(filename)
    #     if 'Status' in df.columns and skip_status_five:
    #         df = df[df.Status != '5'][["Country receiver", "PID receiver"]].drop_duplicates()
    #     else:
    #         df = df[["Country receiver", "PID receiver"]].drop_duplicates()
    #     return df

    def load_data_for_uq_users(self, filename) -> list:
        """ Returns the list of unique PID Receiver in an vendor file"""

        df = self.load_data(filename)
        if 'Status' in df.columns:
            return list(df[df.Status != '5']['PID receiver'].unique())
        return list(df['PID receiver'].unique())

    def prep_df_for_service_usage_calc(self, df, skip_status_five=False) -> pd.DataFrame:
        """ Takes a dataframe, replaces n/a with blank string, removes rows with status 5
        and converts preset list of columns from string to numeric representation.
        """

        df.fillna('', inplace=True)
        if skip_status_five and 'Status' in df.columns:
            df.drop(df[df['Status'] == '5'].index, inplace=True)
        for c_name in df.columns:
            if c_name in self._FILE_NUMERIC_COLS:
                df[c_name] = pd.to_numeric(df[c_name])
        return df
