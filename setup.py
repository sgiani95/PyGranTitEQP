from setuptools import setup, find_packages

setup(
    name="granted",
    version="0.9.2",
    description="GranTED: Gran/Schwartz Titration Analysis Tool",
    author="Samuele Giani",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "numpy>=1.21",
        "pandas>=1.3",
        "scipy>=1.7",
        "matplotlib>=3.5",
        "seaborn>=0.11",
    ],
    entry_points={
        "console_scripts": [
            "granted = granted.main:main",
        ],
    },
    python_requires=">=3.8",
)
