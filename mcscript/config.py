"""config -- parse user configuration and load cluster configuration

  Language: Python 3

  Patrick J. Fasano
  Department of Physics, University of Notre Dame

  + 07/03/22 (pjf): Created.
"""

from typing import MutableMapping, Union
import configparser
import importlib, importlib.util
import os
import xdg

################################################################
# user configuration parsing
################################################################
class UserConfig(object):
    """Configuration for mcscript from user config file.

    Loads configuration from $XDG_CONFIG_HOME/mcscript.conf, $HOME/.mcscriptrc.

    Attributes:
        cluster_config_file (str): cluster configuration module filename
        install_home (str): location of installed executables
        run_home (str): default location for run scripts
        work_home (str): default location for work directories
        launch_dir (str): default location for launching job
        python_executable (str): Python executable path
        run_prefix (str): run script prefix
        env_script (str): additional environment script for batch jobs
        config_filename (str): location of user config file
        config_dict (dict): parsed config file (for cluster-specific options)
    """
    cluster_config_file:Union[str,bytes,os.PathLike]
    install_home:Union[str,bytes,os.PathLike]
    run_home:Union[str,bytes,os.PathLike]
    work_home:Union[str,bytes,os.PathLike]
    launch_dir:Union[str,bytes,os.PathLike]
    python_executable:Union[str,bytes,os.PathLike]
    run_prefix:Union[str,bytes,os.PathLike]
    env_script:Union[str,bytes,os.PathLike]
    config_filename:Union[str,bytes,os.PathLike]
    config_dict:MutableMapping

    def __init__(self):
        """Initialize from user's config file."""
        from .utils import expand_path
        config = configparser.ConfigParser()
        config_paths = [
            os.path.join(xdg.xdg_config_home(), "mcscript.conf"),
            os.path.join(os.environ["HOME"], ".mcscriptrc"),
        ]
        config_file = None
        for file in config_paths:
            if os.path.exists(file):
                config_file = file
        if config_file is None:
            raise FileNotFoundError("cannot find configuration file: {:s}".format(config_paths))
        config.read(config_file)

        # mandatory fields
        self.cluster_config_file = expand_path(config["mcscript"]["cluster_config"])
        self.install_home = expand_path(config["mcscript"]["install_home"])  # MCSCRIPT_INSTALL_HOME
        self.run_home = expand_path(config["mcscript"]["run_home"])  # MCSCRIPT_RUN_HOME
        self.work_home = expand_path(config["mcscript"]["work_home"])  # MCSCRIPT_WORK_HOME

        # optional fields
        self.launch_dir = expand_path(config["mcscript"].get("launch_dir", self.work_home))  # MCSCRIPT_LAUNCH_DIR
        self.python_executable = expand_path(config["mcscript"].get("python_executable", "python3"))  # MCSCRIPT_PYTHON
        self.run_prefix = config["mcscript"].get("run_prefix", "run")  # MCSCRIPT_RUN_PREFIX
        self.env_script = expand_path(config["mcscript"].get("env_script", ""))  # MCSCRIPT_SOURCE

        # expose config file as dict (for cluster-specific options)
        self.config_filename = config_file
        self.config_dict = dict(config)

user_config = UserConfig()

# import cluster config module
if not os.path.exists(user_config.cluster_config_file):
    raise ModuleNotFoundError(
        f"cluster_config not found: {user_config.cluster_config_file}",
        name=user_config.cluster_config_file
    )

__spec = importlib.util.spec_from_file_location(
    "mcscript.config.cluster_config", user_config.cluster_config_file
)
cluster_config = importlib.util.module_from_spec(__spec)
__spec.loader.exec_module(cluster_config)

# delegate to cluster_config
def __getattr__(name:str):
    try:
        return globals()[name]
    except KeyError:
        return getattr(cluster_config, name)
