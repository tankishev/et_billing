from datetime import datetime as dt
from .report import DBReport, DBReportFactory
from .renderer import ReportRenderer
from .layouts import LayoutFactory
from .report_layouts import layout as report_layout


def set_up(period: str) -> DBReportFactory:
    db_proxy = DBReport()
    renderer = ReportRenderer()
    layout_factory = LayoutFactory(report_layout, new_layout=True)
    return DBReportFactory(
        period=period,
        db_report=db_proxy,
        layout_factory=layout_factory,
        renderer=renderer
    )


def gen_report_by_id(period: str, report_id: int):
    start = dt.now()
    dbf = set_up(period)
    res = dbf.generate_report_by_report_id(report_id)
    dbf.close()
    print(dt.now() - start)
    return res


def gen_report_for_client(period, client):
    start = dt.now()
    dbf = set_up(period)
    res = dbf.generate_report_by_client(client)
    dbf.close()
    print(dt.now() - start)
    return res


def gen_reports(period):
    start = dt.now()
    dbf = set_up(period)
    res = dbf.generate_reports()
    dbf.close()
    print(dt.now() - start)
    return res
