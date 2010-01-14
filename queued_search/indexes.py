from queues import queues
from django.conf import settings
from haystack import indexes
from haystack.utils import get_identifier
from queued_search import get_queue_name


class QueuedSearchIndex(indexes.SearchIndex):
    """
    A ``SearchIndex`` subclass that enqueues updates/deletes for later
    processing.
    
    This allows page loads to remain snappy (as appending to a queue is a
    very fast operation) and background updating of the index, allowing you
    to maintain near real-time results without impacting user experience.
    
    Make the fast, go go go.
    """
    # We override the built-in _setup_* methods to connect the enqueuing
    # operation.
    def _setup_save(self, model):
        signals.post_save.connect(self.enqueue_save, sender=model)
    
    def _setup_delete(self, model):
        signals.post_delete.connect(self.enqueue_delete, sender=model)
    
    def _teardown_save(self, model):
        signals.post_save.disconnect(self.enqueue_save, sender=model)
    
    def _teardown_delete(self, model):
        signals.post_delete.disconnect(self.enqueue_delete, sender=model)
    
    def enqueue_save(self, instance, **kwargs):
        return self.enqueue('save', instance)
    
    def enqueue_delete(self, instance, **kwargs):
        return self.enqueue('delete', instance)
    
    def enqueue(self, action, instance):
        """
        Shoves a message about how to update the index into the queue.
        
        This is a standardized string, resembling something like::
        
            ``update:notes.note.23``
            # ...or...
            ``delete:weblog.entry.8``
        """
        message = "%s:%s" % (action, get_identifier(instance))
        queue = queues.Queue(get_queue_name())
        return queue.write(message)
