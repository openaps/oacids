#!/usr/bin/python

from setuptools import setup, find_packages

import oacids
def readme():
    with open("README.md") as f:
        return f.read()

setup(name='oacids',
    version='0.0.0', # http://semver.org/
    description='open aps continuous I D system.',
    long_description=readme(),
    author="Ben West",
    author_email="bewest+openaps@gmail.com",
    # url="https://github.com/openaps/oacids",
    url="https://openaps.org/",
    packages=find_packages( ),
    include_package_data = True,
    install_requires = [
      'recurrent',
      'openaps > 0.0.9',
    ],
    dependency_links = [
    ],
    scripts = [
      'bin/openaps-dbus',
      'bin/openaps-schedule',
    ],
    entry_points = {
      'openaps.importable': [
        'schedules = oacids.schedules',
        # 'aliases = oacids.schedules',
        # 'triggers = oacids.triggers',
      ],
    },
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Libraries'
    ],
    zip_safe=False,
)

#####
# EOF
