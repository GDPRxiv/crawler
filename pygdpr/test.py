import os
#from pygdpr.models.dpa.ireland import *
from pygdpr.models.dpa.united_kingdom import *
from pygdpr.models.dpa.bulgaria import *

path = "/united-kingdom"
dpa = UnitedKingdom(path)
dpa.get_docs()

#path = "/ireland"
#dpa = Ireland(path)


path = "/bulgaria"
dpa = Bulgaria(path)
dpa.get_docs()




