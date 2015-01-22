from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(
    name='ckanext-notifications',
    version=version,
    description="provides enotify feature",
    long_description='''
    ''',
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Dominik Kapisinsky',
    author_email='kapisinsky@microcomp.sk',
    url='http://github.com/microcomp',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.notifications'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points='''
        [ckan.plugins]
        # Add plugins here, e.g.
        # myplugin=ckanext.notifications.plugin:PluginClass
    ''',
)
