from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='wsnsims',
    version='2.0.0.dev1',
    description='Simulations for various WSN federation algorithms',
    long_description=long_description,
    url='https://github.com/forgetfulyoshi/wsnsims',
    author='Ben Anglin',
    author_email='jama1@umbc.edu',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Scientific/Engineering',
    ],
    keywords='wsn federation flower focus minds tocs',
    packages=find_packages(exclude=['doc', 'test']),
    install_requires=[
        'ordered-set',
        'matplotlib',
        'numpy',
        'pillow',
        'pyclustering',
        'scipy',
    ],

)
