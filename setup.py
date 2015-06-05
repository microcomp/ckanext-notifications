from setuptools import setup, find_packages
import sys, os

version = '0.1'

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
        notifications=ckanext.notifications.plugin:NotificationPlugin
        
        [ckan.celery_task]
        tasks = ckanext.notifications.celery_import:task_imports
        
        [paste.paster_command]
        notifications-cmd = ckanext.notifications.notifications_cmd:NotificationsCmd
    ''',
)
