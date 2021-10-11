import os
from pygdpr.models.dpa.ireland import *
from pygdpr.models.dpa.united_kingdom import *
from pygdpr.models.dpa.austria import *
from pygdpr.models.dpa.belgium import *
from pygdpr.models.dpa.bulgaria import *
from pygdpr.models.dpa.czech_republic import *
from pygdpr.models.dpa.bulgaria import *
from pygdpr.models.dpa.croatia import *


#path = "./united-kingdom"

#path = "/united-kingdom"

#dpa = UnitedKingdom(path)
#path = "./ireland"

#path = "/austria"
#dpa = Austria(path)
#dpa.get_docs_AnnualReports()

#path = "/ireland"
#dpa = Ireland(path)
#dpa.get_docs_Guidances_v1()

#path = "/belgium"
#dpa = Belgium(path)
#dpa.get_docs_AnnualReports()


#path = "/united-kingdom"
#dpa = UnitedKingdom(path)
#dpa.get_docs()

#path = "/ireland"
#dpa = Ireland(path)

#path = "/bulgaria"
#dpa = Bulgaria(path)
#dpa.get_docs()


path = "/croatia"
dpa = Croatia(path)
dpa.get_docs()

#path = "/czech_republic"
#dpa = CzechRepublic(path)
#dpa.get_docs()

