
def add_cls_attrs(view_cls):
    def wrap(func):
        if not hasattr(func, 'short_description') and hasattr(view_cls, 'short_description'):
            func.short_description = view_cls.short_description
        if not hasattr(func, 'perm_required') and hasattr(view_cls, 'perm_required'):
            func.perm_required = view_cls.perm_required
        return func
    return wrap
