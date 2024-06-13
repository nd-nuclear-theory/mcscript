from setuptools import setup, find_namespace_packages

setup(
    name="mcscript",
    version="2.0.0",
    author="Mark A. Caprio, Patrick J. Fasano, University of Notre Dame",
    description=("Scripting setup, utilities, and task control for cluster runs"),
    license="MIT",
    packages=find_namespace_packages(include=['mcscript*']),
    entry_points={
        "console_scripts": [
            "qsubm = mcscript.qsubm:main",
        ],
    },
    package_data={
        "mcscript": [
            "job_wrappers/*",
        ]
    },
    classifiers=[],
)
