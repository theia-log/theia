import setuptools


with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name="theia",
    version="0.9.1",
    author="Pavle Jonoski",
    author_email="jonoski.pavle@gmail.com",
    description="Theia is a lightweight log aggregator.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/theia-log/theia",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Internet :: Log Analysis",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Logging",
        "Topic :: Utilities",
    ),
    install_requires=[
        "pathtools==0.1.2",
        "picotui==0.9.1",
        "PyYAML==3.12",
        "watchdog==0.8.3",
        "websockets==3.3",
    ]
)

