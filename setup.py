import setuptools



setuptools.setup(
    name="sdem", 
    version="0.2.2",
    author="O Hamelijnck",
    author_email="ohamelijnck@gmail.com",
    description="Sacred Experiment Manager",
    long_description="",
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    scripts=["cli/sdem"],
    install_requires = [
        "typer",
        "loguru",
        "slurmjobs",
        "git+https://github.com/IDSIA/sacred",
        "seml",
        "scikit-learn",
        "tabulate",
        "jupyter",
        "black",
        "rich",
        "dvc",
        "pandas ",
        "numpy",
        "PyYAML"
    ]
)
