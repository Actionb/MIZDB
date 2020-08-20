from django.dispatch import receiver
# TODO: delete signals.py (multi_sender isn't used anywhere)

def multi_sender(signal, senders, **kwargs):
    """A decorator that adds a reciever for every sender in senders."""
    def _decorator(func):
        for s in senders:
            receiver(signal, sender=s, **kwargs)(func)
        return func
    return _decorator
