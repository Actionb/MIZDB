import datetime, re
#TODO: remove the ZRAUM_ID,DUPLETTEN_ID constants
# ID für den Lagerort, der den Zeitschriftenraum darstellt
ZRAUM_ID = 6

# ID für den Lagerort, der das Duplettenlager darstellt
DUPLETTEN_ID = 5

# Model.CharField args
CF_ARGS = {'max_length': 200}
CF_ARGS_B = {'max_length': 200, 'blank': True}

# attrs specifications for TextArea Formfield
ATTRS_TEXTAREA = {'rows': 3, 'cols': 90}

# Maximum string length for a concatenated list of M2M values.
M2M_LIST_MAX_LEN = 50

# Maximum string length for a concatenated list of M2M values to displayed on the changelist.
LIST_DISPLAY_MAX_LEN = int(M2M_LIST_MAX_LEN / 2)

CUR_JAHR = datetime.datetime.now().year
MAX_JAHR = CUR_JAHR + 1  # TODO: Remove MAX_JAHR and MIN_JAHR constants
MIN_JAHR = 1899

# regex for discogs id validation
DISCOGS_RELEASE_ID_REGEX = r'discogs.com/.*release/(\d+)'
discogs_release_id_pattern = re.compile(DISCOGS_RELEASE_ID_REGEX)
