from haystack import indexes
from queued_search.indexes import QueuedSearchIndex
from notes.models import Note


# Simplest possible subclass that could work.
class NoteIndex(QueuedSearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='content')
    
    def get_model(self):
        return Note
