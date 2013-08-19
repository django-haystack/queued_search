import logging
from optparse import make_option
from queues import queues, QueueException
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.management.base import NoArgsCommand
from django.db.models.loading import get_model
from haystack import connections
from haystack.constants import DEFAULT_ALIAS
from haystack.exceptions import NotHandled
from queued_search.utils import get_queue_name


DEFAULT_BATCH_SIZE = None
LOG_LEVEL = getattr(settings, 'SEARCH_QUEUE_LOG_LEVEL', logging.ERROR)

logging.basicConfig(
    level=LOG_LEVEL
)

class Command(NoArgsCommand):
    help = "Consume any objects that have been queued for modification in search."
    can_import_settings = True
    base_options = (
        make_option('-b', '--batch-size', action='store', dest='batchsize',
            default=None, type='int',
            help='Number of items to index at once.'
        ),
        make_option("-u", "--using", action="store", type="string", dest="using", default=DEFAULT_ALIAS,
            help='If provided, chooses a connection to work with.'
        ),
    )
    option_list = NoArgsCommand.option_list + base_options

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.log = logging.getLogger('queued_search')
        self.actions = {
            'update': set(),
            'delete': set(),
        }
        self.processed_updates = set()
        self.processed_deletes = set()

    def handle_noargs(self, **options):
        self.batchsize = options.get('batchsize', DEFAULT_BATCH_SIZE) or 1000
        self.using = options.get('using')
        # Setup the queue.
        self.queue = queues.Queue(get_queue_name())

        # Check if enough is there to process.
        if not len(self.queue):
            self.log.info("Not enough items in the queue to process.")

        self.log.info("Starting to process the queue.")

        # Consume the whole queue first so that we can group update/deletes
        # for efficiency.
        try:
            while True:
                message = self.queue.read()

                if not message:
                    break

                self.process_message(message)
        except QueueException:
            # We've run out of items in the queue.
            pass

        self.log.info("Queue consumed.")

        try:
            self.handle_updates()
            self.handle_deletes()
        except Exception as e:
            self.log.error('Exception seen during processing: %s' % e)
            self.requeue()
            raise e

        self.log.info("Processing complete.")

    def requeue(self):
        """
        On failure, requeue all unprocessed messages.
        """
        self.log.error('Requeuing unprocessed messages.')
        update_count = 0
        delete_count = 0

        for update in self.actions['update']:
            if not update in self.processed_updates:
                self.queue.write('update:%s' % update)
                update_count += 1

        for delete in self.actions['delete']:
            if not delete in self.processed_deletes:
                self.queue.write('delete:%s' % delete)
                delete_count += 1

        self.log.error('Requeued %d updates and %d deletes.' % (update_count, delete_count))

    def process_message(self, message):
        """
        Given a message added by the ``QueuedSearchIndex``, add it to either
        the updates or deletes for processing.
        """
        self.log.debug("Processing message '%s'..." % message)

        if not ':' in message:
            self.log.error("Unable to parse message '%s'. Moving on..." % message)
            return

        action, obj_identifier = message.split(':')
        self.log.debug("Saw '%s' on '%s'..." % (action, obj_identifier))

        if action == 'update':
            # Remove it from the delete list if it's present.
            # Since we process the queue in order, this could occur if an
            # object was deleted then readded, in which case we should ignore
            # the delete and just update the index.
            if obj_identifier in self.actions['delete']:
                self.actions['delete'].remove(obj_identifier)

            self.actions['update'].add(obj_identifier)
            self.log.debug("Added '%s' to the update list." % obj_identifier)
        elif action == 'delete':
            # Remove it from the update list if it's present.
            # Since we process the queue in order, this could occur if an
            # object was updated then deleted, in which case we should ignore
            # the update and just delete the document from the index.
            if obj_identifier in self.actions['update']:
                self.actions['update'].remove(obj_identifier)

            self.actions['delete'].add(obj_identifier)
            self.log.debug("Added '%s' to the delete list." % obj_identifier)
        else:
            self.log.error("Unrecognized action '%s'. Moving on..." % action)

    def split_obj_identifier(self, obj_identifier):
        """
        Break down the identifier representing the instance.

        Converts 'notes.note.23' into ('notes.note', 23).
        """
        bits = obj_identifier.split('.')

        if len(bits) < 2:
            self.log.error("Unable to parse object identifer '%s'. Moving on..." % obj_identifier)
            return (None, None)

        pk = bits[-1]
        # In case Django ever handles full paths...
        object_path = '.'.join(bits[:-1])
        return (object_path, pk)

    def get_model_class(self, object_path):
        """Fetch the model's class in a standarized way."""
        bits = object_path.split('.')
        app_name = '.'.join(bits[:-1])
        classname = bits[-1]
        model_class = get_model(app_name, classname)

        if model_class is None:
            self.log.error("Could not load model from '%s'. Moving on..." % object_path)
            return None

        return model_class

    def get_instance(self, model_class, pk):
        """Fetch the instance in a standarized way."""
        try:
            instance = model_class.objects.get(pk=pk)
        except ObjectDoesNotExist:
            self.log.error("Couldn't load model instance with pk #%s. Somehow it went missing?" % pk)
            return None
        except MultipleObjectsReturned:
            self.log.error("More than one object with pk #%s. Oops?" % pk)
            return None

        return instance

    def get_index(self, model_class):
        """Fetch the model's registered ``SearchIndex`` in a standarized way."""
        try:
            return connections['default'].get_unified_index().get_index(model_class)
        except NotHandled:
            self.log.error("Couldn't find a SearchIndex for %s." % model_class)
            return None

    def handle_updates(self):
        """
        Process through all updates.

        Updates are grouped by model class for maximum batching/minimized
        merging.
        """
        # For grouping same model classes for efficiency.
        updates = {}
        previous_path = None
        current_index = None

        for obj_identifier in self.actions['update']:
            (object_path, pk) = self.split_obj_identifier(obj_identifier)

            if object_path is None or pk is None:
                self.log.error("Skipping.")
                continue

            if object_path not in updates:
                updates[object_path] = []

            updates[object_path].append(pk)

        # We've got all updates grouped. Process them.
        for object_path, pks in updates.items():
            model_class = self.get_model_class(object_path)

            if object_path != previous_path:
                previous_path = object_path
                current_index = self.get_index(model_class)

            if not current_index:
                self.log.error("Skipping.")
                continue

            instances = [self.get_instance(model_class, pk) for pk in pks]

            # Filter out what we didn't find.
            instances = [instance for instance in instances if instance is not None]

            # Update the batch of instances for this class.
            # Use the backend instead of the index because we can batch the
            # instances.
            total = len(instances)
            self.log.debug("Indexing %d %s." % (total, object_path))

            for start in range(0, total, self.batchsize):
                end = min(start + self.batchsize, total)
                batch_instances = instances[start:end]

                self.log.debug("  indexing %s - %d of %d." % (start+1, end, total))
                current_index._get_backend(self.using).update(current_index, batch_instances)

                for updated in batch_instances:
                    self.processed_updates.add("%s.%s" % (object_path, updated.pk))

            self.log.debug("Updated objects for '%s': %s" % (object_path, ", ".join(pks)))

    def handle_deletes(self):
        """
        Process through all deletes.

        Deletes are grouped by model class for maximum batching.
        """
        deletes = {}
        previous_path = None
        current_index = None

        for obj_identifier in self.actions['delete']:
            (object_path, pk) = self.split_obj_identifier(obj_identifier)

            if object_path is None or pk is None:
                self.log.error("Skipping.")
                continue

            if object_path not in deletes:
                deletes[object_path] = []

            deletes[object_path].append(obj_identifier)

        # We've got all deletes grouped. Process them.
        for object_path, obj_identifiers in deletes.items():
            model_class = self.get_model_class(object_path)

            if object_path != previous_path:
                previous_path = object_path
                current_index = self.get_index(model_class)

            if not current_index:
                self.log.error("Skipping.")
                continue

            pks = []

            for obj_identifier in obj_identifiers:
                current_index.remove_object(obj_identifier, using=self.using)
                pks.append(self.split_obj_identifier(obj_identifier)[1])
                self.processed_deletes.add(obj_identifier)

            self.log.debug("Deleted objects for '%s': %s" % (object_path, ", ".join(pks)))
