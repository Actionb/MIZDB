This is just a dummy app to force Django admin to use jQuery version 3.5.1 for django autocomplete light.

In `INSTALLED_APPS`, put `jquery_351` before any other apps that would collect the jQuery version provided by Django admin. 
```python

INSTALLED_APPS = [
    'jquery_downgrade',
    'dal',
    'dal_select2',
    ...
```

The downgrade is necessary due to a bug with later versions of jQuery:  
https://github.com/select2/select2/issues/5993
https://github.com/yourlabs/django-autocomplete-light/issues/1283

Note that the issue is fixed with jQuery 3.7.0, but Django 4.2 still uses 3.6.4 as of this moment.
