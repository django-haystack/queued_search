=============
queued_search
=============

Allows you to utilize a queue and shove updates/deletes for search into it,
keeping your pages fast and your index fresh.

For use with Haystack (http://haystacksearch.org/).


Requirements
============

* Django 1.1+ (May work on 1.0.X but untested)
* Haystack 1.X (http://github.com/toastdriven/django-haystack)
* Queues (http://code.google.com/p/queues/)

You also need to install your choice of one of the supported search engines for
Haystack and one of the supported queue backends for Queues.


Setup
=====

#. Add ``queued_search`` to ``INSTALLED_APPS``.
#. Alter all of your ``SearchIndex`` subclasses to inherit from ``queued_seearch.indexes.QueuedSearchIndex``.
#. Ensure your queuing solution of choice is running.
#. Setup a cron job to run the ``process_search_queue`` management command.
#. PROFIT!
