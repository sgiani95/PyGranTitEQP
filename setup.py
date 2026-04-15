from setuptools import setup, find_packages

setup(
    name="GranTED",
    version="0.9.4",
    description="GranTED: Gran-Schwartz Titration Analysis Tool",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="sgiani95",
    author_email="samuele.giani@gmail.com",        # ← change this
    url="https://github.com/sgiani95/GranTED",
    license="Apache-2.0",
    
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
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Chemistry",
    ],
)
