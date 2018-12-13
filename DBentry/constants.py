import re
import datetime

from django.core.validators import *
from django.utils.six.moves.urllib.parse import quote, unquote

# ID für den Lagerort, der den Zeitschriftenraum darstellt
ZRAUM_ID = 6

# ID für den Lagerort, der das Duplettenlager darstellt
DUPLETTEN_ID = 5

# Wenn wahr: besitzt eine Ausgabe, der über die Admin Aktionen einen Zeitschriftenraum-Bestand hinzugefügt werden soll, 
# bereits über einen Zeitschriftenraum-Bestand, so wird stattdessen ein Dupletten-Bestand hinzugefügt.
AUTO_ASSIGN_DUPLICATE = True

# Model.CharField args
CF_ARGS = {'max_length' : 200}
CF_ARGS_B = {'max_length' : 200, 'blank' : True}

# Model.yearfield args
YF_ARGS = { 
    'null' : True,
    'blank' : True, 
    'validators' : [MinValueValidator(1900), MaxValueValidator(datetime.datetime.now().year+1)]
}

# attrs specifications for TextArea Formfield
ATTRS_TEXTAREA = {'rows': 3,'cols': 90}


# Admin-Site search_term constants 

# Seperator for entire search_term segments (e.g. magazin=Good Times-->,<---jahr=2011)
SEARCH_SEG_SEP = ','
COMMA_HTML = quote(SEARCH_SEG_SEP)
SEARCH_SEG_SEP_HTML = unquote(SEARCH_SEG_SEP)                               #'%2C'

# Seperator for separating individual search_term segments into 'column'---> = <--- 'to_search'
SEARCH_TERM_SEP = '='
EQUAL_HTML = quote(SEARCH_TERM_SEP)
SEARCH_TERM_SEP_HTML = unquote(SEARCH_TERM_SEP)                             #'%3D'

# m2m list max len
M2M_LIST_MAX_LEN = 50

# list_display max len
LIST_DISPLAY_MAX_LEN = int(M2M_LIST_MAX_LEN/2)

CUR_JAHR = datetime.datetime.now().year
MAX_JAHR = CUR_JAHR+1
MIN_JAHR = 1899

PERM_DENIED_MSG = 'Sie haben nicht die erforderliche Berechtigung diese Seite zu sehen.'

RELEASE_ID_REGEX = r'discogs.com/.*release/(\d+)'
discogs_release_id_pattern = re.compile(RELEASE_ID_REGEX)
