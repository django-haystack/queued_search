import logging
from queues import queues, QueueException
from django.core.management import call_command
from django.test import TestCase
from haystack import backend, site
from haystack.query import SearchQuerySet
from queued_search import get_queue_name
from notes.models import Note


class QueuedSearchIndexTestCase(TestCase):
    def setUp(self):
        super(QueuedSearchIndexTestCase, self).setUp()
        
        # Nuke the queue.
        queues.delete_queue(get_queue_name())
        
        # Nuke the index.
        back = backend.SearchBackend()
        back.clear()
        
        # Get a queue connection so we can poke at it.
        self.queue = queues.Queue(get_queue_name())
    
    def test_update(self):
        self.assertEqual(len(self.queue), 0)
        
        note1 = Note.objects.create(
            title='A test note',
            content='Because everyone loves test data.',
            author='Daniel'
        )
        
        self.assertEqual(len(self.queue), 1)
        
        note2 = Note.objects.create(
            title='Another test note',
            content='More test data.',
            author='Daniel'
        )
        
        self.assertEqual(len(self.queue), 2)
        
        note3 = Note.objects.create(
            title='Final test note',
            content='The test data. All done.',
            author='Joe'
        )
        
        self.assertEqual(len(self.queue), 3)
        
        note3.title = 'Final test note FOR REAL'
        note3.save()
        
        self.assertEqual(len(self.queue), 4)
        
        # Pull the whole queue.
        messages = []
        
        try:
            while True:
                messages.append(self.queue.read())
        except QueueException:
            # We're out of queued bits.
            pass
        
        self.assertEqual(messages, [u'update:notes.note.1', u'update:notes.note.2', u'update:notes.note.3', u'update:notes.note.3'])
    
    def test_delete(self):
        note1 = Note.objects.create(
            title='A test note',
            content='Because everyone loves test data.',
            author='Daniel'
        )
        note2 = Note.objects.create(
            title='Another test note',
            content='More test data.',
            author='Daniel'
        )
        note3 = Note.objects.create(
            title='Final test note',
            content='The test data. All done.',
            author='Joe'
        )
        
        # Dump the queue in preparation for the deletes.
        queues.delete_queue(get_queue_name())
        self.queue = queues.Queue(get_queue_name())
        
        self.assertEqual(len(self.queue), 0)
        note1.delete()
        self.assertEqual(len(self.queue), 1)
        note2.delete()
        self.assertEqual(len(self.queue), 2)
        note3.delete()
        self.assertEqual(len(self.queue), 3)
        
        # Pull the whole queue.
        messages = []
        
        try:
            while True:
                messages.append(self.queue.read())
        except QueueException:
            # We're out of queued bits.
            pass
        
        self.assertEqual(messages, [u'delete:notes.note.1', u'delete:notes.note.2', u'delete:notes.note.3'])
    
    def test_complex(self):
        self.assertEqual(len(self.queue), 0)
        
        note1 = Note.objects.create(
            title='A test note',
            content='Because everyone loves test data.',
            author='Daniel'
        )
        
        self.assertEqual(len(self.queue), 1)
        
        note2 = Note.objects.create(
            title='Another test note',
            content='More test data.',
            author='Daniel'
        )
        
        self.assertEqual(len(self.queue), 2)
        
        note1.delete()
        self.assertEqual(len(self.queue), 3)
        
        note3 = Note.objects.create(
            title='Final test note',
            content='The test data. All done.',
            author='Joe'
        )
        
        self.assertEqual(len(self.queue), 4)
        
        note3.title = 'Final test note FOR REAL'
        note3.save()
        
        self.assertEqual(len(self.queue), 5)
        
        note3.delete()
        self.assertEqual(len(self.queue), 6)
        
        # Pull the whole queue.
        messages = []
        
        try:
            while True:
                messages.append(self.queue.read())
        except QueueException:
            # We're out of queued bits.
            pass
        
        self.assertEqual(messages, [u'update:notes.note.1', u'update:notes.note.2', u'delete:notes.note.1', u'update:notes.note.3', u'update:notes.note.3', u'delete:notes.note.3'])


class ProcessSearchQueueTestCase(TestCase):
    def test_processing(self):
        pass
