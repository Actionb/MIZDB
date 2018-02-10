from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver

from DBentry.utils import get_relations_between_models

def multi_sender(signal, senders, **kwargs):
    """
    Connects a signal handler (func) to models in senders.
    """
    def _decorator(func):
        for s in senders:
            receiver(signal, sender=s, **kwargs)(func)
        return func
    return _decorator


#@receiver(post_save)
@multi_sender((post_save, post_delete), ('DBentry.ausgabe_jahr','DBentry.ausgabe_monat', 'DBentry.ausgabe_num', 'DBentry.ausgabe_lnum', 'DBentry.magazin'))
def set_name_changed_flag_ausgabe(sender, **kwargs):
    instance = kwargs.get('instance', False)
    if instance:
        field, rel = get_relations_between_models(sender, 'ausgabe')
        if field.related_model == sender:
            # The relation field points to sender from ausgabe; get the reverse 'set'
            getattr(instance, rel.get_accessor_name()).update(_changed_flag=True)
        else:
            # The relation points to ausgabe, get the ausgabe instance
            getattr(instance, field.name).qs().update(_changed_flag=True)
