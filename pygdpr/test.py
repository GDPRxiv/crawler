import os
from pygdpr.models.dpa.ireland import *
from pygdpr.models.dpa.united_kingdom import *
#path = "./united-kingdom"
#dpa = UnitedKingdom(path)
path = "./ireland"
dpa = Ireland(path)
print('--------------News--------------- \n')
dpa.get_docs_News()
#print('--------------Decisions--------------- \n')
#dpa.get_docs_Decisions() # https://www.dataprotection.ie/en/dpc-guidance/law/decisions-exercising-corrective-powers-made-under-data-protection-act-2018
#print('--------------Judgements--------------- \n')
#dpa.get_docs_Judgements() # https://www.dataprotection.ie/en/dpc-guidance/law/judgments
#print(existed_date)
