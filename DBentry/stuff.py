from django.contrib.admin.utils import get_fields_from_path
from .models import *

def stuff(m=ausgabe, n='m2m_audio_ausgabe_set-0-ausgabe__magazin'):
    while True:
        # Reducing k in hopes of getting something useful
        if n:
            try:
                # Test to see if k can be used to build a query
                get_fields_from_path(self.model, n)
                break
            except:
                # Slice off the first bit
                n = "__".join(n.split("__")[1:])
        else:
            break
    print('n:', n)
