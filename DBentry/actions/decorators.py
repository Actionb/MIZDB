
def add_cls_attrs(view_cls):
    """
    A decorator for an action view function that adds view class attributes.

    Adds the following attributes to the view function if it doesn't already
    have these set:
        - 'short_description' (str) which is used as label for the action in
            the changelist drop down menu.
        - 'perm_required', list of permission codewords required to access
            the action.
            See DBentry.admin.base.MIZModelAdmin.get_actions().
    """
    def wrap(func):
        if (not hasattr(func, 'short_description') and
                hasattr(view_cls, 'short_description')):
            func.short_description = view_cls.short_description
        if (not hasattr(func, 'perm_required') and
                hasattr(view_cls, 'perm_required')):
            func.perm_required = view_cls.perm_required
        return func
    return wrap
