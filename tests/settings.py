import os

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'notes.db'

INSTALLED_APPS = [
    'haystack',
    'queued_search',
    'notes',
]

HAYSTACK_SITECONF = 'notes.search_sites'
HAYSTACK_SEARCH_ENGINE = 'whoosh'
HAYSTACK_WHOOSH_PATH = os.path.join(os.path.dirname(__file__), 'whoosh_index')

QUEUE_BACKEND = 'dummy'

# Specific to queued_search.
import logging
SEARCH_QUEUE_LOG_LEVEL = logging.DEBUG
