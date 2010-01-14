from haystack import indexes
from haystack import site
from queued_search.indexes import QueuedSearchIndex
from notes.models import Note


# Simplest possible subclass that could work.
class NoteIndex(QueuedSearchIndex):
    text = indexes.CharField(document=True, model_attr='content')


site.register(Note, NoteIndex)
