import os
from pygdpr.models.dpa.ireland import *
from pygdpr.models.dpa.united_kingdom import *
#path = "./united-kingdom"
#dpa = UnitedKingdom(path)
#path = "./ireland"

path = "/ireland"
dpa = Ireland(path)
dpa.get_docs()


