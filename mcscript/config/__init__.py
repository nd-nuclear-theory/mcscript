"""config -- parse user configuration and load cluster configuration

  Language: Python 3

  Patrick J. Fasano
  Department of Physics, University of Notre Dame

  + 07/30/20 (pjf): Created.

"""

import configparser
import importlib
import os
import xdg

# if adding a new configuration, add to registry here:
_configs = {
    "nersc": ".slurm_nersc",
    "oak": ".torque_oak",
    "ndcrc": ".uge_ndcrc",
    "ompi": ".ompi",
}

################################################################
# user configuration parsing
################################################################
class UserConfig(object):
    """Configuration for mcscript from user config file.

    Loads configuration from $XDG_CONFIG_HOME/mcscript.conf

    Attributes:
        cluster (str): cluster configuration name
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

    def __init__(self):
        """Initialize from user's config file."""
        from ..utils import expand_path
        config = configparser.ConfigParser()
        config_file = os.path.join(xdg.XDG_CONFIG_HOME, "mcscript.conf")
        if not os.path.exists(config_file):
            raise FileNotFoundError("cannot find configuration file: {:s}".format(config_file))
        config.read(config_file)

        # mandatory fields
        self.cluster = config["mcscript"]["cluster"]
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


################################################################
# cluster configuration (dynamic) loading
################################################################

# 07/30/20 (pjf): importlib magic from https://stackoverflow.com/q/43059267
if user_config.cluster in _configs:
    module = importlib.import_module(_configs[user_config.cluster], package=__name__)
else:
    raise ValueError("Unrecognized cluster configuration: {:s}".format(user_config.cluster))

if "__all__" in module.__dict__:
    globals().update({k: getattr(module, k) for k in module.__dict__["__all__"]})
else:
    raise ValueError("Configuration for cluster '{:s}' does not set `__all__`.")
