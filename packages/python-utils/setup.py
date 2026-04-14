from setuptools import setup, find_packages

setup(
    name="facturia-utils",
    version="1.0.0",
    description="Shared Python utilities for FacturIA",
    author="FacturIA Team",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.5.0",
        "python-dotenv>=1.0.0",
    ],
)
