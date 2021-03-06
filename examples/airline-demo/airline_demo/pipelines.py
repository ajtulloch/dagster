"""Pipeline definitions for the airline_demo."""
import logging

from dagster import (
    DependencyDefinition,
    ExecutionContext,
    PipelineContextDefinition,
    PipelineDefinition,
    SolidInstance,
)
from .resources import (
    postgres_db_info_resource,
    redshift_db_info_resource,
    spark_session_local,
    tempfile_resource,
    unsigned_s3_session,
    s3_download_manager,
)
from .solids import (
    average_sfo_outbound_avg_delays_by_destination,
    canonicalize_column_names,
    delays_by_geography,
    delays_vs_fares,
    delays_vs_fares_nb,
    download_from_s3,
    eastbound_delays,
    ingest_csv_to_spark,
    join_spark_data_frames,
    load_data_to_database_from_spark,
    normalize_weather_na_values,
    prefix_column_names,
    q2_sfo_outbound_flights,
    sfo_delays_by_destination,
    subsample_spark_dataset,
    tickets_with_destination,
    union_spark_data_frames,
    unzip_file,
    upload_to_s3,
    westbound_delays,
)


test_context = PipelineContextDefinition(
    context_fn=lambda _: ExecutionContext.console_logging(log_level=logging.DEBUG),
    resources={
        'spark': spark_session_local,
        's3': unsigned_s3_session,
        'db_info': redshift_db_info_resource,
        'tempfile': tempfile_resource,
        'download_manager': s3_download_manager,
    },
)


local_context = PipelineContextDefinition(
    context_fn=lambda _: ExecutionContext.console_logging(log_level=logging.DEBUG),
    resources={
        'spark': spark_session_local,
        's3': unsigned_s3_session,
        'db_info': postgres_db_info_resource,
        'tempfile': tempfile_resource,
        'download_manager': s3_download_manager,
    },
)


prod_context = PipelineContextDefinition(
    context_fn=lambda _: ExecutionContext.console_logging(log_level=logging.DEBUG),
    resources={
        'spark': spark_session_local,  # FIXME
        's3': unsigned_s3_session,
        'db_info': redshift_db_info_resource,
        'tempfile': tempfile_resource,
    },
)


CONTEXT_DEFINITIONS = {'test': test_context, 'local': local_context, 'prod': prod_context}


def define_airline_demo_ingest_pipeline():
    solids = [
        canonicalize_column_names,
        download_from_s3,
        ingest_csv_to_spark,
        join_spark_data_frames,
        load_data_to_database_from_spark,
        normalize_weather_na_values,
        prefix_column_names,
        subsample_spark_dataset,
        union_spark_data_frames,
        unzip_file,
    ]
    dependencies = {
        SolidInstance('download_from_s3', alias='download_april_on_time_data'): {},
        SolidInstance('download_from_s3', alias='download_may_on_time_data'): {},
        SolidInstance('download_from_s3', alias='download_june_on_time_data'): {},
        SolidInstance('download_from_s3', alias='download_master_cord_data'): {},
        SolidInstance('download_from_s3', alias='download_q2_coupon_data'): {},
        SolidInstance('download_from_s3', alias='download_q2_market_data'): {},
        SolidInstance('download_from_s3', alias='download_q2_ticket_data'): {},
        SolidInstance('download_from_s3', alias='download_q2_sfo_weather'): {},
        SolidInstance('unzip_file', alias='unzip_april_on_time_data'): {
            'archive_file': DependencyDefinition('download_april_on_time_data')
        },
        SolidInstance('unzip_file', alias='unzip_may_on_time_data'): {
            'archive_file': DependencyDefinition('download_may_on_time_data')
        },
        SolidInstance('unzip_file', alias='unzip_june_on_time_data'): {
            'archive_file': DependencyDefinition('download_june_on_time_data')
        },
        SolidInstance('unzip_file', alias='unzip_master_cord_data'): {
            'archive_file': DependencyDefinition('download_master_cord_data')
        },
        SolidInstance('unzip_file', alias='unzip_q2_coupon_data'): {
            'archive_file': DependencyDefinition('download_q2_coupon_data')
        },
        SolidInstance('unzip_file', alias='unzip_q2_market_data'): {
            'archive_file': DependencyDefinition('download_q2_market_data')
        },
        SolidInstance('unzip_file', alias='unzip_q2_ticket_data'): {
            'archive_file': DependencyDefinition('download_q2_ticket_data')
        },
        SolidInstance('ingest_csv_to_spark', alias='ingest_april_on_time_data'): {
            'input_csv_file': DependencyDefinition('unzip_april_on_time_data')
        },
        SolidInstance('ingest_csv_to_spark', alias='ingest_may_on_time_data'): {
            'input_csv_file': DependencyDefinition('unzip_may_on_time_data')
        },
        SolidInstance('ingest_csv_to_spark', alias='ingest_june_on_time_data'): {
            'input_csv_file': DependencyDefinition('unzip_june_on_time_data')
        },
        SolidInstance('ingest_csv_to_spark', alias='ingest_q2_sfo_weather'): {
            'input_csv_file': DependencyDefinition('download_q2_sfo_weather')
        },
        SolidInstance('ingest_csv_to_spark', alias='ingest_q2_coupon_data'): {
            'input_csv_file': DependencyDefinition('unzip_q2_coupon_data')
        },
        SolidInstance('ingest_csv_to_spark', alias='ingest_q2_market_data'): {
            'input_csv_file': DependencyDefinition('unzip_q2_market_data')
        },
        SolidInstance('ingest_csv_to_spark', alias='ingest_q2_ticket_data'): {
            'input_csv_file': DependencyDefinition('unzip_q2_ticket_data')
        },
        SolidInstance('ingest_csv_to_spark', alias='ingest_master_cord_data'): {
            'input_csv_file': DependencyDefinition('unzip_master_cord_data')
        },
        SolidInstance('union_spark_data_frames', alias='combine_april_may_on_time_data'): {
            'left_data_frame': DependencyDefinition('ingest_april_on_time_data'),
            'right_data_frame': DependencyDefinition('ingest_may_on_time_data'),
        },
        SolidInstance('union_spark_data_frames', alias='combine_q2_on_time_data'): {
            'left_data_frame': DependencyDefinition('combine_april_may_on_time_data'),
            'right_data_frame': DependencyDefinition('ingest_june_on_time_data'),
        },
        SolidInstance('subsample_spark_dataset', alias='subsample_q2_on_time_data'): {
            'data_frame': DependencyDefinition('combine_q2_on_time_data')
        },
        SolidInstance('subsample_spark_dataset', alias='subsample_q2_ticket_data'): {
            'data_frame': DependencyDefinition('ingest_q2_ticket_data')
        },
        SolidInstance('subsample_spark_dataset', alias='subsample_q2_market_data'): {
            'data_frame': DependencyDefinition('ingest_q2_market_data')
        },
        SolidInstance('subsample_spark_dataset', alias='subsample_q2_coupon_data'): {
            'data_frame': DependencyDefinition('ingest_q2_coupon_data')
        },
        SolidInstance('normalize_weather_na_values', alias='normalize_q2_weather_na_values'): {
            'data_frame': DependencyDefinition('ingest_q2_sfo_weather')
        },
        SolidInstance('prefix_column_names', alias='prefix_dest_cord_data'): {
            'data_frame': DependencyDefinition('ingest_master_cord_data')
        },
        SolidInstance('prefix_column_names', alias='prefix_origin_cord_data'): {
            'data_frame': DependencyDefinition('ingest_master_cord_data')
        },
        SolidInstance('join_spark_data_frames', alias='join_q2_on_time_data_to_dest_cord_data'): {
            'left_data_frame': DependencyDefinition('subsample_q2_on_time_data'),
            'right_data_frame': DependencyDefinition('prefix_dest_cord_data'),
        },
        SolidInstance('join_spark_data_frames', alias='join_q2_on_time_data_to_origin_cord_data'): {
            'left_data_frame': DependencyDefinition('join_q2_on_time_data_to_dest_cord_data'),
            'right_data_frame': DependencyDefinition('prefix_origin_cord_data'),
        },
        SolidInstance('canonicalize_column_names', alias='canonicalize_q2_on_time_data'): {
            'data_frame': DependencyDefinition('join_q2_on_time_data_to_origin_cord_data')
        },
        SolidInstance('canonicalize_column_names', alias='canonicalize_q2_coupon_data'): {
            'data_frame': DependencyDefinition('subsample_q2_coupon_data')
        },
        SolidInstance('canonicalize_column_names', alias='canonicalize_q2_market_data'): {
            'data_frame': DependencyDefinition('subsample_q2_market_data')
        },
        SolidInstance('canonicalize_column_names', alias='canonicalize_q2_ticket_data'): {
            'data_frame': DependencyDefinition('subsample_q2_ticket_data')
        },
        SolidInstance('canonicalize_column_names', alias='canonicalize_q2_sfo_weather'): {
            'data_frame': DependencyDefinition('normalize_q2_weather_na_values')
        },
        SolidInstance('load_data_to_database_from_spark', alias='load_q2_on_time_data'): {
            'data_frame': DependencyDefinition('canonicalize_q2_on_time_data')
        },
        SolidInstance('load_data_to_database_from_spark', alias='load_q2_coupon_data'): {
            'data_frame': DependencyDefinition('canonicalize_q2_coupon_data')
        },
        SolidInstance('load_data_to_database_from_spark', alias='load_q2_market_data'): {
            'data_frame': DependencyDefinition('canonicalize_q2_market_data')
        },
        SolidInstance('load_data_to_database_from_spark', alias='load_q2_ticket_data'): {
            'data_frame': DependencyDefinition('canonicalize_q2_ticket_data')
        },
        SolidInstance('load_data_to_database_from_spark', alias='load_q2_sfo_weather'): {
            'data_frame': DependencyDefinition('canonicalize_q2_sfo_weather')
        },
    }

    return PipelineDefinition(
        name="airline_demo_ingest_pipeline",
        solids=solids,
        dependencies=dependencies,
        context_definitions=CONTEXT_DEFINITIONS,
    )


def define_airline_demo_warehouse_pipeline():
    return PipelineDefinition(
        name="airline_demo_warehouse_pipeline",
        solids=[
            average_sfo_outbound_avg_delays_by_destination,
            delays_by_geography,
            delays_vs_fares,
            delays_vs_fares_nb,
            eastbound_delays,
            q2_sfo_outbound_flights,
            sfo_delays_by_destination,
            tickets_with_destination,
            upload_to_s3,
            westbound_delays,
        ],
        dependencies={
            'q2_sfo_outbound_flights': {},
            'tickets_with_destination': {},
            'westbound_delays': {},
            'eastbound_delays': {},
            'average_sfo_outbound_avg_delays_by_destination': {
                'q2_sfo_outbound_flights': DependencyDefinition('q2_sfo_outbound_flights')
            },
            'delays_vs_fares': {
                'tickets_with_destination': DependencyDefinition('tickets_with_destination'),
                'average_sfo_outbound_avg_delays_by_destination': DependencyDefinition(
                    'average_sfo_outbound_avg_delays_by_destination'
                ),
            },
            'fares_vs_delays': {'table_name': DependencyDefinition('delays_vs_fares')},
            'sfo_delays_by_destination': {
                'table_name': DependencyDefinition('average_sfo_outbound_avg_delays_by_destination')
            },
            'delays_by_geography': {
                'eastbound_delays': DependencyDefinition('eastbound_delays'),
                'westbound_delays': DependencyDefinition('westbound_delays'),
            },
            SolidInstance('upload_to_s3', alias='upload_outbound_avg_delay_pdf_plots'): {
                'file_obj': DependencyDefinition('sfo_delays_by_destination')
            },
            SolidInstance('upload_to_s3', alias='upload_delays_vs_fares_pdf_plots'): {
                'file_obj': DependencyDefinition('fares_vs_delays')
            },
            SolidInstance('upload_to_s3', alias='upload_delays_by_geography_pdf_plots'): {
                'file_obj': DependencyDefinition('delays_by_geography')
            },
        },
        context_definitions=CONTEXT_DEFINITIONS,
    )
