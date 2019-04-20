import datetime
import pytest

import pandas as pd

from dagster import (
    solid,
    execute_pipeline,
    Bool,
    DependencyDefinition,
    InputDefinition,
    List,
    OutputDefinition,
    PipelineDefinition,
)
from dagster.core.types.evaluator import evaluate_config_value

from dagster_gcp import (
    BigQueryError,
    BigQuerySolidDefinition,
    BigQueryCreateDatasetSolidDefinition,
    BigQueryDeleteDatasetSolidDefinition,
    BigQueryLoadFromDataFrameSolidDefinition,
)

from dagster_pandas import DataFrame


def test_simple_queries():
    solid_inst = BigQuerySolidDefinition(
        'test',
        [
            # Toy example query
            'SELECT 1 AS field1, 2 AS field2;',
            # Test access of public BQ historical dataset (only processes ~2MB here)
            # pylint: disable=line-too-long
            '''SELECT *
            FROM `weathersource-com.pub_weather_data_samples.sample_weather_history_anomaly_us_zipcode_daily`
            ORDER BY postal_code ASC, date_valid_std ASC
            LIMIT 1''',
        ],
    )

    pipeline = PipelineDefinition(solids=[solid_inst])
    pipeline_result = execute_pipeline(pipeline)
    res = pipeline_result.result_for_solid(solid_inst.name)
    assert res.success

    values = res.transformed_value()
    for df in values:
        assert isinstance(df, pd.DataFrame)
    assert values[0].to_dict('list') == {'field1': [1], 'field2': [2]}
    assert values[1].to_dict('list') == {
        'postal_code': ['02101'],
        'country': ['US'],
        'date_valid_std': [datetime.date(2014, 1, 1)],
        'doy_std': [1],
        'avg_temperature_air_2m_f': [25.05],
        'avg_temperature_anomaly_air_2m_f': [-7.81],
        'tot_precipitation_in': [0.0],
        'tot_precipitation_anomaly_in': [-0.28],
        'tot_snowfall_in': [0.0],
        'tot_snowfall_anomaly_in': [-1.36],
        'avg_wind_speed_10m_mph': [7.91],
        'avg_wind_speed_10m_anomaly_mph': [-1.85],
    }


# pylint: disable=line-too-long
def test_bad_config():
    configs_and_expected_errors = [
        (
            # Create disposition must match enum values
            {'create_disposition': 'this is not a valid create disposition'},
            'Value not in enum type BQCreateDisposition',
        ),
        (
            # Dataset must be of form project_name.dataset_name
            {'default_dataset': 'this is not a valid dataset'},
            'Value at path root:solids:test:config:default_dataset is not valid. Expected "Dataset"',
        ),
        (
            # Table must be of form project_name.dataset_name.table_name
            {'destination': 'this is not a valid table'},
            'Value at path root:solids:test:config:destination is not valid. Expected "Table"',
        ),
        (
            # Priority must match enum values
            {'priority': 'this is not a valid priority'},
            'Value not in enum type BQPriority',
        ),
        (
            # Schema update options must be a list
            {'schema_update_options': 'this is not valid schema update options'},
            'Value at path root:solids:test:config:schema_update_options must be list. Expected: [BQSchemaUpdateOption]',
        ),
        (
            {'schema_update_options': ['this is not valid schema update options']},
            'Value not in enum type BQSchemaUpdateOption',
        ),
        (
            {'write_disposition': 'this is not a valid write disposition'},
            'Value not in enum type BQWriteDisposition',
        ),
    ]

    pipeline_def = PipelineDefinition(
        name='test_config_pipeline', solids=[BigQuerySolidDefinition('test', ['SELECT 1'])]
    )

    for config_fragment, error_message in configs_and_expected_errors:
        config = {'solids': {'test': {'config': config_fragment}}}
        result = evaluate_config_value(pipeline_def.environment_type, config)
        assert result.errors[0].message == error_message


def test_create_delete_dataset():
    create_solid = BigQueryCreateDatasetSolidDefinition('test')
    create_pipeline = PipelineDefinition(solids=[create_solid])
    config = {'solids': {'test': {'config': {'dataset': 'foo', 'exists_ok': True}}}}

    assert execute_pipeline(create_pipeline, config).result_for_solid(create_solid.name).success

    config = {'solids': {'test': {'config': {'dataset': 'foo', 'exists_ok': False}}}}
    with pytest.raises(BigQueryError) as exc_info:
        execute_pipeline(create_pipeline, config)
    assert 'Dataset "foo" already exists and exists_ok is false' in str(exc_info.value)

    delete_solid = BigQueryDeleteDatasetSolidDefinition('test')
    delete_pipeline = PipelineDefinition(solids=[delete_solid])
    config = {'solids': {'test': {'config': {'dataset': 'foo'}}}}

    # Delete should succeed
    assert execute_pipeline(delete_pipeline, config).result_for_solid(delete_solid.name).success

    # Delete non-existent with "not_found_ok" should succeed
    config = {'solids': {'test': {'config': {'dataset': 'foo', 'not_found_ok': True}}}}
    assert execute_pipeline(delete_pipeline, config).result_for_solid(delete_solid.name).success

    # Delete non-existent with "not_found_ok" False should fail
    config = {'solids': {'test': {'config': {'dataset': 'foo', 'not_found_ok': False}}}}
    with pytest.raises(BigQueryError) as exc_info:
        execute_pipeline(delete_pipeline, config)
    assert 'Dataset "foo" does not exist and not_found_ok is false' in str(exc_info.value)


def test_pd_df_load():
    test_df = pd.DataFrame({'num1': [1, 3], 'num2': [2, 4]})

    create_solid = BigQueryCreateDatasetSolidDefinition('create_solid')
    load_solid = BigQueryLoadFromDataFrameSolidDefinition('load_solid')
    query_solid = BigQuerySolidDefinition('query_solid', ['SELECT num1, num2 FROM foo.df'])
    delete_solid = BigQueryDeleteDatasetSolidDefinition('delete_solid')

    @solid(inputs=[InputDefinition('success', Bool)], outputs=[OutputDefinition(DataFrame)])
    def return_df(_context, success):  # pylint: disable=unused-argument
        return test_df

    @solid(inputs=[InputDefinition('df', List(DataFrame))], outputs=[OutputDefinition(Bool)])
    def barrier(_context, df):  # pylint: disable=unused-argument
        return True

    config = {
        'solids': {
            'create_solid': {'config': {'dataset': 'foo', 'exists_ok': True}},
            'load_solid': {'config': {'destination': 'foo.df'}},
            'delete_solid': {'config': {'dataset': 'foo', 'delete_contents': True}},
        }
    }
    pipeline = PipelineDefinition(
        solids=[return_df, create_solid, load_solid, query_solid, barrier, delete_solid],
        dependencies={
            'return_df': {'success': DependencyDefinition('create_solid')},
            'load_solid': {'df': DependencyDefinition('return_df')},
            'query_solid': {'input_ready_sentinel': DependencyDefinition('load_solid')},
            'barrier': {'df': DependencyDefinition('query_solid')},
            'delete_solid': {'input_ready_sentinel': DependencyDefinition('barrier')},
        },
    )
    result = execute_pipeline(pipeline, config)
    assert result.success

    values = result.result_for_solid(query_solid.name).transformed_value()
    assert values[0].to_dict() == test_df.to_dict()
