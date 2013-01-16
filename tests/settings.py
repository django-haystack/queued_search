import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'notes.db'
    }
}

INSTALLED_APPS = [
    'haystack',
    'queued_search',
    'notes',
]

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index')
    }
}
HAYSTACK_SIGNAL_PROCESSOR = 'queued_search.signals.QueuedSignalProcessor'

QUEUE_BACKEND = 'dummy'

# Specific to queued_search.
import logging
SEARCH_QUEUE_LOG_LEVEL = logging.DEBUG
