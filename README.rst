=============
queued_search
=============

Allows you to utilize a queue and shove updates/deletes for search into it,
keeping your pages fast and your index fresh.

For use with Haystack (http://haystacksearch.org/).

**WARNING!!!**

This project has been updated to be compatible with Haystack 2.0.x!
If you need ``queued_search`` for Haystack 1.2.X, please use the 1.0.4 tag
or ``pip install queued_search==1.0.4``!


Requirements
============

* Python 2.6+ or Python 3.3+
* Django 1.5+
* Haystack 2.0.X (http://github.com/toastdriven/django-haystack)
* Queues (http://code.google.com/p/queues/)

You also need to install your choice of one of the supported search engines for
Haystack and one of the supported queue backends for Queues.


Setup
=====

#. Add ``queued_search`` to ``INSTALLED_APPS``.
#. Alter all of your ``SearchIndex`` subclasses to inherit from ``queued_search.indexes.QueuedSearchIndex`` (as well as ``indexes.Indexable``).
#. Ensure your queuing solution of choice is running.
#. Setup a cron job to run the ``process_search_queue`` management command.
#. PROFIT!
