from django.conf import settings


def get_queue_name():
    """
    Standized way to fetch the queue name.
    
    Can be overridden by specifying ``SEARCH_QUEUE_NAME`` in your settings.
    
    Given that the queue name is used in disparate places, this is primarily
    for sanity.
    """
    return getattr(settings, 'SEARCH_QUEUE_NAME', 'haystack_search_queue'):
