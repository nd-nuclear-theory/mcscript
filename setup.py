from setuptools import setup, find_packages

setup(
    name="mcscript",
    version="1.0.0",
    author="Mark A. Caprio, Patrick J. Fasano, University of Notre Dame",
    description=("Scripting setup, utilities, and task control for cluster runs"),
    license="MIT",
    packages=find_packages(include='mcscript*'),
    classifiers=[],
)
