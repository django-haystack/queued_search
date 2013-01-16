from queues import queues
from django.db import models
from haystack.signals import BaseSignalProcessor
from haystack.utils import get_identifier
from queued_search.utils import get_queue_name


class QueuedSignalProcessor(BaseSignalProcessor):
    def setup(self):
        models.signals.post_save.connect(self.enqueue_save)
        models.signals.post_delete.connect(self.enqueue_delete)

    def teardown(self):
        models.signals.post_save.disconnect(self.enqueue_save)
        models.signals.post_delete.disconnect(self.enqueue_delete)

    def enqueue_save(self, sender, instance, **kwargs):
        return self.enqueue('update', instance)

    def enqueue_delete(self, sender, instance, **kwargs):
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
