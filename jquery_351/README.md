This is just a dummy app to force Django admin to use jQuery version 3.5.1.

In `INSTALLED_APPS`, put `jquery_351` before any other apps that would collect the jQuery version provided by Django admin. 
```python

INSTALLED_APPS = [
    'jquery_downgrade',
    'dal',
    'dal_select2',
    ...
```

The downgrade is necessary due to a bug with later versions of jQuery:  
[Search not auto focusing in jQuery 3.6.0](https://github.com/select2/select2/issues/5993) 
