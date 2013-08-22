from haystack import indexes
from .models import Note


# Simplest possible subclass that could work.
class NoteIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='content')

    def get_model(self):
        return Note
