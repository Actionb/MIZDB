import re
# TODO: remove the ZRAUM_ID,DUPLETTEN_ID constants  # noqa
# ID für den Lagerort, der den Zeitschriftenraum darstellt
ZRAUM_ID = 6

# ID für den Lagerort, der das Dublettenlager darstellt
DUPLETTEN_ID = 5  # noqa

# attrs specifications for TextArea Formfield
ATTRS_TEXTAREA = {'rows': 3, 'cols': 90}

# regex for discogs id validation
DISCOGS_RELEASE_ID_REGEX = r'discogs.com/.*release/(\d+)'
discogs_release_id_pattern = re.compile(DISCOGS_RELEASE_ID_REGEX)
