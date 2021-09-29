import os
from pygdpr.models.dpa.ireland import *
from pygdpr.models.dpa.united_kingdom import *
from pygdpr.models.dpa.austria import *
#path = "./united-kingdom"
#dpa = UnitedKingdom(path)
#path = "./ireland"

path = "/austria"
dpa = Austria(path)
dpa.get_docs_Decisions()


