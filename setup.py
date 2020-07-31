import setuptools

setuptools.setup(
    name="mcscript",
    version="0.1.1",
    author="Mark A. Caprio, Patrick J. Fasano, University of Notre Dame",
    description=("Scripting setup, utilities, and task control for cluster runs"),
    license="MIT",
#    packages=['mcscript'],
    packages=setuptools.find_packages(),
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
