import logging
from queues import queues, QueueException
from django.core.management import call_command
from django.test import TestCase
from haystack import backend, site
from haystack.query import SearchQuerySet
from queued_search import get_queue_name
from queued_search.management.commands.process_search_queue import Command as ProcessSearchQueueCommand
from notes.models import Note


class AssertableHandler(logging.Handler):
    stowed_messages = []
    
    def emit(self, record):
        AssertableHandler.stowed_messages.append(record.getMessage())


assertable = AssertableHandler()
logging.getLogger('queued_search').addHandler(assertable)


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
    def setUp(self):
        super(ProcessSearchQueueTestCase, self).setUp()
        
        # Nuke the queue.
        queues.delete_queue(get_queue_name())
        
        # Nuke the index.
        back = backend.SearchBackend()
        back.clear()
        
        # Get a queue connection so we can poke at it.
        self.queue = queues.Queue(get_queue_name())
        
        # Clear out and capture log messages.
        AssertableHandler.stowed_messages = []
        
        self.psqc = ProcessSearchQueueCommand()
    
    def test_process_mesage(self):
        self.assertEqual(self.psqc.actions, {'update': set([]), 'delete': set([])})
        
        self.psqc.process_message('update:notes.note.1')
        self.assertEqual(self.psqc.actions, {'update': set(['notes.note.1']), 'delete': set([])})
        
        self.psqc.process_message('delete:notes.note.2')
        self.assertEqual(self.psqc.actions, {'update': set(['notes.note.1']), 'delete': set(['notes.note.2'])})
        
        self.psqc.process_message('update:notes.note.2')
        self.assertEqual(self.psqc.actions, {'update': set(['notes.note.1', 'notes.note.2']), 'delete': set([])})
        
        self.psqc.process_message('delete:notes.note.1')
        self.assertEqual(self.psqc.actions, {'update': set(['notes.note.2']), 'delete': set(['notes.note.1'])})
        
        self.psqc.process_message('wtfmate:notes.note.1')
        self.assertEqual(self.psqc.actions, {'update': set(['notes.note.2']), 'delete': set(['notes.note.1'])})
        
        self.psqc.process_message('just plain wrong')
        self.assertEqual(self.psqc.actions, {'update': set(['notes.note.2']), 'delete': set(['notes.note.1'])})
    
    def test_split_obj_identifier(self):
        self.assertEqual(self.psqc.split_obj_identifier('notes.note.1'), ('notes.note', '1'))
        self.assertEqual(self.psqc.split_obj_identifier('myproject.notes.note.73'), ('myproject.notes.note', '73'))
        self.assertEqual(self.psqc.split_obj_identifier('wtfmate.1'), ('wtfmate', '1'))
        self.assertEqual(self.psqc.split_obj_identifier('wtfmate'), (None, None))
    
    def test_processing(self):
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
        
        self.assertEqual(AssertableHandler.stowed_messages, [])
        
        # Call the command.
        call_command('process_search_queue')
        
        self.assertEqual(AssertableHandler.stowed_messages, [
            'Starting to process the queue.',
            u"Processing message 'update:notes.note.1'...",
            u"Saw 'update' on 'notes.note.1'...",
            u"Added 'notes.note.1' to the update list.",
            u"Processing message 'update:notes.note.2'...",
            u"Saw 'update' on 'notes.note.2'...",
            u"Added 'notes.note.2' to the update list.",
            u"Processing message 'delete:notes.note.1'...",
            u"Saw 'delete' on 'notes.note.1'...",
            u"Added 'notes.note.1' to the delete list.",
            u"Processing message 'update:notes.note.3'...",
            u"Saw 'update' on 'notes.note.3'...",
            u"Added 'notes.note.3' to the update list.",
            u"Processing message 'update:notes.note.3'...",
            u"Saw 'update' on 'notes.note.3'...",
            u"Added 'notes.note.3' to the update list.",
            u"Processing message 'delete:notes.note.3'...",
            u"Saw 'delete' on 'notes.note.3'...",
            u"Added 'notes.note.3' to the delete list.",
            'Queue consumed.',
            u'Indexing 1 notes.note.',
            '  indexing 1 - 1 of 1.',
            u"Updated objects for 'notes.note': 2",
            u"Deleted objects for 'notes.note': 1, 3",
            'Processing complete.'
        ])
        self.assertEqual(SearchQuerySet().all().count(), 1)
    
    def test_requeuing(self):
        self.assertEqual(len(self.queue), 0)
        
        note1 = Note.objects.create(
            title='A test note',
            content='Because everyone loves test data.',
            author='Daniel'
        )
        
        self.assertEqual(len(self.queue), 1)
        
        # Write a failed message.
        self.queue.write('update:notes.note.abc')
        self.assertEqual(len(self.queue), 2)
        
        self.assertEqual(AssertableHandler.stowed_messages, [])
        
        try:
            # Call the command, which will fail.
            call_command('process_search_queue')
            self.fail("The command ran successfully, which is incorrect behavior in this case.")
        except:
            # We don't care that it failed. We just want to examine the state
            # of things afterward.
            pass
        
        self.assertEqual(len(self.queue), 2)
        
        # Pull the whole queue.
        messages = []
        
        try:
            while True:
                messages.append(self.queue.read())
        except QueueException:
            # We're out of queued bits.
            pass
        
        self.assertEqual(messages, [u'update:notes.note.1', 'update:notes.note.abc'])
        self.assertEqual(len(self.queue), 0)
        
        self.assertEqual(AssertableHandler.stowed_messages, [
            'Starting to process the queue.',
            u"Processing message 'update:notes.note.1'...",
            u"Saw 'update' on 'notes.note.1'...",
            u"Added 'notes.note.1' to the update list.",
            "Processing message 'update:notes.note.abc'...",
            "Saw 'update' on 'notes.note.abc'...",
            "Added 'notes.note.abc' to the update list.",
            'Queue consumed.',
            "Exception seen during processing: invalid literal for int() with base 10: 'abc'",
            'Requeuing unprocessed messages.',
            'Requeued 2 updates and 0 deletes.'
        ])
        
        # Start over.
        note1 = Note.objects.create(
            title='A test note',
            content='Because everyone loves test data.',
            author='Daniel'
        )
        
        self.assertEqual(len(self.queue), 1)
        
        note2 = Note.objects.create(
            title='Another test note',
            content='Because everyone loves test data.',
            author='Daniel'
        )
        
        self.assertEqual(len(self.queue), 2)
        
        # Now delete it.
        note2.delete()
        
        # Write a failed message.
        self.queue.write('delete:notes.note.abc')
        self.assertEqual(len(self.queue), 4)
        
        AssertableHandler.stowed_messages = []
        self.assertEqual(AssertableHandler.stowed_messages, [])
        
        try:
            # Call the command, which will fail again.
            call_command('process_search_queue')
            self.fail("The command ran successfully, which is incorrect behavior in this case.")
        except:
            # We don't care that it failed. We just want to examine the state
            # of things afterward.
            pass
        
        # Everything but the bad bit of data should have processed.
        self.assertEqual(len(self.queue), 1)
        
        # Pull the whole queue.
        messages = []
        
        try:
            while True:
                messages.append(self.queue.read())
        except QueueException:
            # We're out of queued bits.
            pass
        
        self.assertEqual(messages, ['delete:notes.note.abc'])
        self.assertEqual(len(self.queue), 0)
        
        self.assertEqual(AssertableHandler.stowed_messages, [
            'Starting to process the queue.',
            u"Processing message 'update:notes.note.2'...",
            u"Saw 'update' on 'notes.note.2'...",
            u"Added 'notes.note.2' to the update list.",
            u"Processing message 'update:notes.note.3'...",
            u"Saw 'update' on 'notes.note.3'...",
            u"Added 'notes.note.3' to the update list.",
            u"Processing message 'delete:notes.note.3'...",
            u"Saw 'delete' on 'notes.note.3'...",
            u"Added 'notes.note.3' to the delete list.",
            "Processing message 'delete:notes.note.abc'...",
            "Saw 'delete' on 'notes.note.abc'...",
            "Added 'notes.note.abc' to the delete list.",
            'Queue consumed.',
            u'Indexing 1 notes.note.',
            '  indexing 1 - 1 of 1.',
            u"Updated objects for 'notes.note': 2",
            "Exception seen during processing: Provided string 'notes.note.abc' is not a valid identifier.",
            'Requeuing unprocessed messages.',
            'Requeued 0 updates and 1 deletes.'
        ])
