import os
from pygdpr.models.dpa.ireland import *
from pygdpr.models.dpa.united_kingdom import *
from pygdpr.models.dpa.austria import *
from pygdpr.models.dpa.belgium import *
from pygdpr.models.dpa.bulgaria import *

#path = "./united-kingdom"

#path = "/united-kingdom"

#dpa = UnitedKingdom(path)
#path = "./ireland"

#path = "/austria"
#dpa = Austria(path)
#dpa.get_docs_Decisions()

#path = "/ireland"
#dpa = Ireland(path)
#dpa.get_docs_Guidances_v1()

path = "/belgium"
dpa = Belgium(path)
dpa.get_docs_Opinions()


#path = "/ireland"
#dpa = Ireland(path)


#path = "/bulgaria"
#dpa = Bulgaria(path)
#dpa.get_docs()




