Execution
=========

.. currentmodule:: dagster

Execution Functions
-------------------

.. autofunction:: execute_pipeline

.. autofunction:: execute_pipeline_iterator

Results
-------

.. autoclass:: InProcessExecutorConfig
   :members:

.. autoclass:: MultiprocessExecutorConfig
   :members:

.. autoclass:: PipelineExecutionResult
   :members:

.. autoclass:: SolidExecutionResult
   :members:

Configuration
-------------

.. autoclass:: RunConfig
   :members:

.. autoclass:: RunStorageMode 
   :members:

.. autoclass:: SolidExecutionResult
   :members:

**Environment Dict Schema**
  The ``environment_dict`` used by ``execute_pipeline`` and
  ``execute_pipeline_iterator`` has the following schema:
  ::
    {
      # configuration for Solids
      'solids': {

        # these keys align with the names of the solids, or their alias in this pipeline
        '_solid_name_': {

          # pass any data that was defined via config_field
          'config': _,

           # materialize input values, keyed by input name
           'inputs': {
             '_input_name_': {'value': _value_}
            }
          }
        },

        # configuration for PipelineContextDefinitions
        'context': {

          # these keys align with the names defined via context_definitions on PipelineDefinition
          '_context_name_': {

            # pass any config data that was defined via config_field
            'config': _,

            # configuration for ResourceDefinitions
            'resources': {

              # these keys align with the names defined via resources on PipelineContextDefinitions
              '_resource_name_': {

                # pass any data that was defined via config_field
                'config': _
              }
            }
          }
        }
      }
    }



