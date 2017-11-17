=======
wsnsims
=======

This project provides simulations of several federation algorithms used in
wireless sensor networks (WSNs). At present, the implemented algorithms are,

* FLOWER
* TOCS
* FOCUS
* MINDS

Setup
=====

This project can be set up using standard Python tools. It relies on vanilla
Python 3.5+ as its interpreter. It is highly recommended that you install this
package in a virtual environment.::

    $ git clone https://<projecturl>/wsnsims.git
    $ pip install -e wsnsims

Testing
=======

We use tox to run all tests. To learn more about tox, visit https://tox.readthedocs.io.

From within the project directory (where the tox.ini file is) do the following::

    $ pip install tox # (if you don't have tox yet)
    $ tox

Running
=======

At present, running the simulations is an all-or-nothing affair. All results
will be placed in a local directory called ``results`` by default. From within
the ``wsnsims`` directory, execute the following.::

    $ python -m wsnsims.conductor.driver

For options, pass in the ``--help`` option::

    $ python -m wsnsims.conductor.driver --help

