from shared.modules import DBProxy
from vendors.models import VendorInputFile


class DBQueries(DBProxy):
    """ A DBProxy object used to execute complex queries """

    def create_temp_data_table(self, period: str) -> None:
        """ Generate a temporary table with data for all reports

        :param period: period for which the reports are created (e.g. '2023-01')
        :return:
        """

        sql = """
            create temp table if not exists tmp_report_data as
            select distinct
                r.id report_id, r.file_name, r.report_type, r.language_id, rl.language
                , rsc.skip_columns, r.include_details, r.show_pids
                ,cd.client_id, cd.legal_name, cd.reporting_name, c.contract_id contract_id, c.start_date contract_date
                ,os.order_id, o.description order_descr, o.ccy_type, p.type payment_type, o.tu_price
                ,vs.service_id, s.service service_group
                ,case when s.stype isnull then '' else stype end service_type
                ,case when r.language_id = 1 then s.desc_bg else s.desc_en end service_descr
                ,s.desc_en s_desc_rept
                ,su.unit_count, op.unit_price, s.skip_service_render
                ,vs.vendor_id, vif.id vif_id, s.service_order
            from reports r
            join report_languages rl on r.language_id = rl.id
            join report_skip_columns rsc on r.skip_columns = rsc.id
            join report_vendors rv on r.id = rv.report_id
            join vendor_services vs on rv.vendor_id = vs.vendor_id
            join stats_usage su on vs.vendor_id = su.vendor_id and vs.service_id = su.service_id
            join order_services os on vs.id = os.vendor_service_id
            join order_prices op on os.order_id = op.order_id and op.service_id = su.service_id
            join client_data cd on r.client_id = cd.client_id
            join orders o on os.order_id = o.order_id
            join payment_types p on o.payment_type = p.id
            join contracts c on o.contract_id = c.contract_id
            left join services s on su.service_id = s.service_id
            left join vendor_input_files vif on vif.vendor_id = vs.vendor_id and vif.period = su.period
            where r.is_active = 1 and o.is_active = 1 and su.period = ? and vif.is_active = True;
        """
        self.exec(sql, (period,)).close()

    def drop_temp_data_table(self) -> None:
        """ Drops the temp table """

        sql = "drop table if exists tmp_report_data"
        self.exec(sql).close()

    def get_report_data_by_client(self, client_id: int) -> tuple or None:
        """ Returns the reports data for the given client_id

        :return: None or tuple with elements:
            report_id,
            file_name,
            report_type: 1:generic,
            language_id: 1:BG, 2:EN,
            skip_columns,
            include_details: 0:false, 1:true"
            client_id, legal_name, contract_id, contract_date
        """

        sql = "select distinct report_id, file_name, report_type, language, skip_columns, include_details, show_pids, "
        sql += "client_id, legal_name, contract_id, contract_date from tmp_report_data where client_id = ?"
        res = self.exec(sql, (client_id,))
        data = res.fetchall()
        res.close()
        if data:
            return data

    def get_report_data_by_report_id(self, report_id: int) -> tuple or None:
        """ Returns the data for the given report_id

        :return: None or tuple with elements:
            report_id,
            file_name,
            report_type: 1:generic,
            language_id: 1:BG, 2:EN,
            skip_columns,
            include_details: 0:false, 1:true"
            client_id, legal_name, contract_id, contract_date
        """

        sql = "select distinct report_id, file_name, report_type, language, skip_columns, include_details, show_pids, "
        sql += "client_id, legal_name, contract_id, contract_date from tmp_report_data where report_id = ?"
        res = self.exec(sql, (report_id,))
        data = res.fetchall()
        res.close()
        if data:
            return data

    def get_report_data(self) -> tuple or None:
        """ Returns the reports data for all reports

        :return: None or tuple with elements:
            report_id,
            file_name,
            report_type: 1:generic,
            language_id: 1:BG, 2:EN,
            skip_columns,
            include_details: 0:false, 1:true"
            client_id, legal_name
        """

        sql = "select distinct report_id, file_name, report_type, language, skip_columns, include_details, show_pids,"
        sql += " client_id, legal_name, contract_id, contract_date from tmp_report_data"
        res = self.exec(sql)
        data = res.fetchall()
        res.close()
        if data:
            return data

    def get_report_details(self, report_id: int) -> tuple or None:
        """ Get the details for a given report

        :return: tuple including (order_id, order_descr, ccy_type, payment_type, tu_price)
        """

        sql = "select distinct"
        sql += " order_id, order_descr, ccy_type, payment_type, tu_price"
        sql += " from tmp_report_data where report_id = ?"
        res = self.exec(sql, (report_id,))
        data = res.fetchall()
        res.close()
        if data:
            return data

    def get_report_order_services(self, report_id: int, order_id: int) -> tuple or None:
        """ Get the details for the respective order_id in the report.

        :return: None or tuple containing:
            (service_order, service_group, service_type, service_descr,
            unit_price, skip_service_render, unit_count)
        """
        sql = "select service_order, service_group, service_type, service_descr, unit_price, skip_service_render,"
        sql += " sum(unit_count) unit_count"
        sql += " from tmp_report_data where report_id = ? and order_id = ?"
        sql += " group by service_order, service_group, service_type, service_descr, unit_price, skip_service_render"
        res = self.exec(sql, (report_id, order_id))
        data = res.fetchall()
        res.close()
        if data:
            return data

    def get_service_types(self) -> list or None:
        """Returns the list of services"""

        sql = "select service_id, service, stype from services order by service_order"
        res = self.exec(sql)
        data = res.fetchall()
        res.close()
        if data:
            return data

    def get_vendor_files_by_report_id(self, report_id):
        """Return the vendor filenames for a given report from the temp_data table"""
        sql = "select distinct vif_id"
        sql += " from tmp_report_data where report_id = ?"
        res = self.exec(sql, (report_id,))
        data = res.fetchall()
        res.close()
        if data:
            ids = [el[0] for el in data]
            vendor_input_files = VendorInputFile.objects.filter(pk__in=ids)
            return vendor_input_files

    # def get_report_temp_data_filenames_by_report_id(self, report_id):
    #     """Return the vendor filenames for a given report from the temp_data table"""
    #     sql = "select distinct vendor_id, vif_id"
    #     sql += " from tmp_report_data where report_id = ?"
    #     res = self.exec(sql, (report_id,))
    #     data = res.fetchall()
    #     res.close()
    #     if data:
    #         return data
