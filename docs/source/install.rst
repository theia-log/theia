Installation Guide
==================

Theia runs on python3, so before installing, please make sure that you have the 
latest version of python3 and pip (for python3).
Use your package manager to install python3 and pip.

Installing with pip
-------------------

To install with pip, just run:

    .. code-block:: shell
    
        pip install theia

Note that you may require ``sudo`` so it will install theia globally.

Installing from source
----------------------

**Prerequisites**: you'll need ``git`` installed.

If you want to hack around in theia's code, you can install the source package.

You can install it with ``pip``, or clone it with ``git`` in a virtual environment.

    .. code-block:: shell
        
        python -m venv dev

Then activate the environment:
    .. code-block:: shell
        
        source dev/bin/activate


Install with git
^^^^^^^^^^^^^^^^^
    
First cd to the directory where you want to checkout the source code, and clone 
the repository:

    .. code-block:: shell
    
        cd ~/projects/workspace
        git clone https://github.com/theia-log/theia

Then cd to the theia directory and create the virtual environment:

    .. code-block:: shell
    
        cd theia
        python -m venv ENV/dev
        source ENV/dev/bin/activate

Then install the requirements:

    .. code-block:: shell
        
        pip install -r requirements.txt


Install with pip
^^^^^^^^^^^^^^^^

First make sure you have your virtual environment set up and activated:

    .. code-block:: shell
    
        cd ~/projects/workspace
        python -m venv ENV/dev
        source ENV/dev/bin/activate
    

Go to the directory where you want to checkout the source code, install with pip
from the Github repository:

    .. code-block:: shell
        
        pip install -e "git+https://github.com/theia-log/theia#egg=theia"

Confirm you've have the package properly installed:

    .. code-block:: shell
        
        python -m theia.cli --help

You should see the help message.

Then cd to the source directory in your ENV:

    .. code-block:: shell
        
        cd ENV/dev/src/theia

And you're ready to go.
