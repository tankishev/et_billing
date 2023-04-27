# CODE OK
from celery import shared_task
from celery_tasks.models import FileProcessingTask
from celery.utils.log import get_task_logger

from .layouts import LayoutFactory
from .renderer import ReportRenderer
from .report import DBReport, DBReportFactory
from .report_layouts import layout as report_layout

from datetime import datetime as dt

celery_logger = get_task_logger('reports.gen_reports')


def set_up(period: str) -> DBReportFactory:
    """ Create and return report factory """

    db_proxy = DBReport()
    renderer = ReportRenderer()
    layout_factory = LayoutFactory(report_layout, new_layout=True)
    return DBReportFactory(
        period=period,
        db_report=db_proxy,
        layout_factory=layout_factory,
        renderer=renderer
    )


@shared_task(bind=True)
def gen_report_by_id(self, period: str, report_id: int):
    """ Generate a single report for a given its report_id and a period """

    start = dt.now()
    celery_logger.info(f'Starting report generation for report_id {report_id}')

    # Create report processing task
    task_status = FileProcessingTask.objects.create(
        task_id=self.request.id, status='PROGRESS', progress=0, number_of_files=1)
    task_status.save()

    # Generate report
    dbf = set_up(period)
    dbf.generate_report_by_report_id(report_id)
    dbf.close()

    execution_time = dt.now() - start
    celery_logger.info(f'Execution time: {execution_time}')


@shared_task(bind=True)
def gen_report_for_client(self, period: str, client: int):
    """ Generate the report for a given client for a given period """

    start = dt.now()
    celery_logger.info(f'Starting report generation for client_id {client}')

    # Create report processing task
    task_status = FileProcessingTask.objects.create(
        task_id=self.request.id, status='PROGRESS', progress=0, number_of_files=1)
    task_status.save()

    # Generate reports
    dbf = set_up(period)
    dbf.generate_report_by_client(client)
    dbf.close()

    execution_time = dt.now() - start
    celery_logger.info(f'Execution time: {execution_time}')


@shared_task(bind=True)
def gen_reports(self, period: str):
    """ Creates a DBReportFactory instance and calls it to generate reports for a given period """

    start = dt.now()
    celery_logger.info(f"Starting billing report generation for ALL clients for {period}")

    # Create report processing task
    task_status = FileProcessingTask.objects.create(
        task_id=self.request.id, status='PROGRESS', progress=0, number_of_files=1)
    task_status.save()

    # Generate reports
    dbf = set_up(period)
    dbf.generate_reports()
    dbf.close()

    execution_time = dt.now() - start
    celery_logger.info(f'Execution time: {execution_time}')
