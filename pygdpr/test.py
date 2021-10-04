import os
#from pygdpr.models.dpa.ireland import *
from pygdpr.models.dpa.united_kingdom import *
from pygdpr.models.dpa.austria import *
<<<<<<< HEAD
from pygdpr.models.dpa.belgium import *

#path = "./united-kingdom"
=======
#path = "/united-kingdom"
>>>>>>> 9e89c42072a5e6e089fb774b326bc3ed1e83f191
#dpa = UnitedKingdom(path)
#path = "./ireland"

#path = "/austria"
#dpa = Austria(path)
#dpa.get_docs_AnnualReports()

#path = "/ireland"
#dpa = Ireland(path)
#dpa.get_docs_Guidances_v1()

path = "/belgium"
dpa = Belgium(path)
dpa.get_docs_Decisions_v1()


#path = "/ireland"
#dpa = Ireland(path)


path = "/bulgaria"
dpa = Bulgaria(path)
dpa.get_docs()




