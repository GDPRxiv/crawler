import os
from pygdpr.models.dpa.ireland import *
from pygdpr.models.dpa.united_kingdom import *
from pygdpr.models.dpa.austria import *
from pygdpr.models.dpa.belgium import *
from pygdpr.models.dpa.bulgaria import *
from pygdpr.models.dpa.czech_republic import *
from pygdpr.models.dpa.croatia import *
from pygdpr.models.dpa.cyprus import *
from pygdpr.models.dpa.denmark import *
from pygdpr.models.dpa.finland import *


#path = "/united-kingdom"
#dpa = UnitedKingdom(path)
#dpa.get_docs()

#path = "/ireland"
#dpa = Ireland(path)


#path = "/bulgaria"
#dpa = Bulgaria(path)

'''
path = "/croatia"
dpa = Croatia(path)
dpa.get_docs()
'''

'''
path = '/czech_republic'
dpa = CzechRepublic(path)
dpa.get_docs_DecisionChecksControlActivites(
    page_url='https://www.uoou.cz/kontrolni%2Dcinnost%2Dv%2Doblasti%2Dochrany%2Dosobnich%2Dudaju%2D2%2Dpololeti/ds-6470/archiv=0&p1=1277',
    folder_title='Control Activities - 2nd half of Year')
'''

#path = "/croatia"
#dpa = Croatia(path)
#dpa.get_docs()

#path = "/cyprus"
#dpa = Cyprus(path)

'''
path = '/czech_republic'
dpa = CzechRepublic(path)
dpa.get_docs_CompletedInspections()
'''

path = '/finland'
dpa = Finland(path)
dpa.get_docs()