from django.forms import Media

def ensure_jquery(media):
    """
    Ensure that jquery is loaded first and in the right order (jquery.js -> jquery.init.js).
    Can be called with a media object or be used as a method decorator.
    """
    def _ensure_jquery(_media):
        from django.conf import settings
        jquery_base = 'admin/js/vendor/jquery/jquery%s.js' % ('' if settings.DEBUG else '.min')
        jquery_init = 'admin/js/jquery.init.js' 
        if not _media._js_lists:
            _media._js_lists.append([jquery_base, jquery_init])
            return _media

        for js_list in _media._js_lists:
            # insert jquery_base at the beginning and jquery_init right after; remove pre-existing entries if necessary
            # Cast the iterable js_list into a list for easier operations; if it's a tuple, change it back to that after we're done.
            is_tuple = isinstance(js_list, (tuple))
            js_list = list(js_list) if is_tuple else js_list
            if jquery_base in js_list:
                js_list.remove(jquery_base)
            js_list.insert(0, jquery_base)
            if jquery_init in js_list:
                js_list.remove(jquery_init)
            js_list.insert(1, jquery_init)
            js_list = tuple(js_list) if not is_tuple else js_list
        return _media

    def wrapper(attr):
        # Use the closure, Luke!
        def decorator(instance):
            return _ensure_jquery(getattr(media, attr)(instance))
        return decorator

    if isinstance(media, Media):
        # Directly working on the media object
        return _ensure_jquery(media)
    elif isinstance(media, property):
        # Decorating the media property; decorator will try media.__get__(instance)
        return property(wrapper('__get__'))
    else:
        # Decorating the media func; decorator will try media.__call__(instance)
        return wrapper('__call__')

