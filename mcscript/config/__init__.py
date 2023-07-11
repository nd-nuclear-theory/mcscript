"""config -- load cluster configuration

  Language: Python 3

  Patrick J. Fasano
  Physics Division, Argonne National Laboratory

  + 07/10/23 (pjf): Created.
"""

import importlib, importlib.util
import os
import sys


################################################################
# cluster configuration module
################################################################

# get cluster config parameter from environment
__cluster_config_name = os.environ.get("MCSCRIPT_CONFIG")
if not __cluster_config_name:
    raise RuntimeError("MCSCRIPT_CONFIG not defined")

# get ModuleSpec (either from explicit filename or from module name)
if os.path.exists(__cluster_config_name):
    __spec = importlib.util.spec_from_file_location(
        "mcscript.config.cluster_config", __cluster_config_name
    )
elif (__spec := importlib.util.find_spec(__cluster_config_name)) is not None:
    pass
else:
    raise ModuleNotFoundError(
        f"MCSCRIPT_CONFIG not found: {__cluster_config_name}",
        name=__cluster_config_name
    )

# import cluster config module
cluster_config = importlib.util.module_from_spec(__spec)
sys.modules["mcscript.config.cluster_config"] = cluster_config
__spec.loader.exec_module(cluster_config)


# delegate to cluster_config module
def __getattr__(name:str):
    try:
        return globals()[name]
    except KeyError:
        return getattr(cluster_config, name)
