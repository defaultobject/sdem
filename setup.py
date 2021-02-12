import setuptools



setuptools.setup(
    name="sdem", 
    version="0.1.1",
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
    install_requires=[
        'typer==0.3.2',
        'loguru==0.5.3',
        'slurmjobs==0.0.15',
        'sacred==0.8.1',
        'seml==0.2.4',
        'scikit-learn==0.23.2'
    ],
    scripts=["cli/sdem"],
)
