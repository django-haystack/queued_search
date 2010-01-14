from django.conf import settings


def get_queue_name():
    return getattr(settings, 'SEARCH_QUEUE_NAME', 'haystack_search_queue'):
