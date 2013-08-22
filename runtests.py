#!/usr/bin/env python
import os
import sys
import logging

from django.conf import settings


settings.configure(
    DATABASES={
        'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory;'}
    },
    INSTALLED_APPS=[
        'haystack',
        'queued_search',
        'tests',
    ],
    HAYSTACK_CONNECTIONS={
        'default': {
            'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
            'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index')
        }
    },
    HAYSTACK_SIGNAL_PROCESSOR='queued_search.signals.QueuedSignalProcessor',
    QUEUE_BACKEND='dummy',
    SEARCH_QUEUE_LOG_LEVEL=logging.DEBUG
)


def runtests(*test_args):
    import django.test.utils

    runner_class = django.test.utils.get_runner(settings)
    test_runner = runner_class(verbosity=1, interactive=True, failfast=False)
    failures = test_runner.run_tests(['tests'])
    sys.exit(failures)


if __name__ == '__main__':
    runtests()
