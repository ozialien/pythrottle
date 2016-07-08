import sys
from setuptools import setup
from setuptools.command.test import test as TestCommand

class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def run(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

# setuptools requires README.rst for standards
try:
    from pypandoc import convert
    read_md = lambda f: convert(f, 'rst')
except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")
    read_md = lambda f: open(f, 'r').read()


setup(
    name='throttle',
    version='0.0.1',
    url='https://github.com/ozialien/pythrottle',
    license='Apache License 2.0',
    author='Ernest Rider',
    author_email='ozialienr@gmail.com',
    description='Throttling algorithms',
    long_description=__doc__,
    packages=['pythrottle'],
    zip_safe=False,
    platforms='any',
    install_requires=[],
    cmdclass={'test': PyTest},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: OpenStack',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'rogramming Language :: Python',
        'Programming Language :: Python :: 2.7'
    ]
)
