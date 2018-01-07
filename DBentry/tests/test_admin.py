from .base import *

class TestAdminsBase(TestBase):
    
    @classmethod
    def setUpTestData(cls):
        pass

class TestAdminPerson(TestAdminsBase):
    # X_string methods
    pass
class TestAdminMusiker(TestAdminsBase):
    # X_string methods
    # search_fields
    pass
class TestAdminGenre(TestAdminsBase):
    # X_string methods
    # search_fields + alias
    # ober?
    pass
class TestAdminSchlagwort(TestAdminsBase):
    # X_string methods
    # search_fields + alias
    # ober?
    pass
class TestAdminBand(TestAdminsBase):
    # X_string methods
    # search_fields + alias
    pass
class TestAdminAutor(TestAdminsBase):
    # __str__
    # X_string methods
    # search_fields
    pass
class TestAdminOrt(TestAdminsBase):
    # __str__
    # search_fields
    pass
class TestAdminLand(TestAdminsBase):
    # search_fields + alias
    pass
class TestAdminBundesland(TestAdminsBase):
    # search_fields
    pass
class TestAdminArtikel(TestAdminsBase):
    # __str__
    # X_string methods
    # search_fields
    pass
class TestAdminInstrument(TestAdminsBase):
    # __str__
    # search_fields + alias
    pass
class TestAdminAudio(TestAdminsBase):
    # save()
    # X_string methods
    pass
class TestAdminSender(TestAdminsBase):
    # search_fields + alias
    pass
class TestAdminSpielort(TestAdminsBase):
    # search_fields + alias
    pass
class TestAdminVeranstaltung(TestAdminsBase):
    # search_fields + alias
    pass
class TestAdminProvenienz(TestAdminsBase):
    # __str__
    # search_fields
    pass
class TestAdminLagerort(TestAdminsBase):
    # __str__
    pass
class TestAdminFormat(TestAdminsBase):
    # __str__
    # get_name
    # save()
    pass
