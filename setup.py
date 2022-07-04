from setuptools import setup, find_packages

setup(
    name="mcscript",
    version="0.1.2",
    author="Mark A. Caprio, Patrick J. Fasano, University of Notre Dame",
    description=("Scripting setup, utilities, and task control for cluster runs"),
    license="MIT",
    packages=find_packages(include='mcscript*'),
    install_requires=[
        "xdg",
    ],
    entry_points={
        "console_scripts": [
            "qsubm = mcscript.qsubm:main",
        ],
    },
    package_data={
        "mcscript": [
            "job_wrappers/bash_job_wrapper.sh",
            "job_wrappers/csh_job_wrapper.csh",
        ]
    },
    classifiers=[],
)
