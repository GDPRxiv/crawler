from pygdpr.models.dpa.ireland import *
from pygdpr.models.dpa.united_kingdom import *
from pygdpr.models.dpa.austria import *
from pygdpr.models.dpa.belgium import *
from pygdpr.models.dpa.bulgaria import *
from pygdpr.models.dpa.czech_republic import *
from pygdpr.models.dpa.croatia import *
from pygdpr.models.dpa.cyprus import *
from pygdpr.models.dpa.denmark import *
from pygdpr.models.dpa.estonia import *
from pygdpr.models.dpa.france import *
from pygdpr.models.dpa.hungary import *
from pygdpr.models.dpa.latvia import *
from pygdpr.models.dpa.greece import *
from pygdpr.models.dpa.finland import *
from pygdpr.models.dpa.italy import *
from pygdpr.models.dpa.luxembourg import *
from pygdpr.models.dpa.malta import *
from pygdpr.models.dpa.portugal import *
from pygdpr.models.dpa.slovenia import *
from pygdpr.models.dpa.spain import*
from pygdpr.models.dpa.lithuania import *
from pygdpr.models.dpa.netherlands import *
from pygdpr.models.dpa.poland import *
from pygdpr.models.dpa.edpb import *
from pygdpr.models.dpa.romania import *
from pygdpr.models.dpa.slovakia import *
from pygdpr.models.dpa.sweden import *

import click


print("\n")
print("  ________________ ____________________        .__        _________                      .__")
print(" /  _____/\______ \\\\______   \______   \___  __|__|__  __ \_   ___ \____________ __  _  _|  |   ___________")
print("/   \  ___ |    |  \|     ___/|       _/\  \/  /  \  \/ / /    \  \/\_  __ \__  \\\\ \/ \/ /  | _/ __ \_  __ \\")
print("\    \_\  \|    `   \    |    |    |   \ >    <|  |\   /  \     \____|  | \// __ \\\\     /|  |_\  ___/|  | \/")
print(" \______  /_______  /____|    |____|_  //__/\_ \__| \_/    \______  /|__|  (____  /\/\_/ |____/\___  >__|")
print("        \/        \/                 \/       \/                  \/            \/                 \/")
print("\n")


@click.command()
@click.option('--country', default='EDPB', help='The country to obtain document from.')
@click.option('--document_type', default='Docs', help='The type of documents to include.')


def scrape(country, document_type):

    """
        \b
        SUPPORTED COUNTRIES:     DOCUMENTS TYPES:

        \b
        Austria                  Decisions
        Belgium                  Annual Reports, Decisions, Opinions
        Bulgaria                 Annual Reports, Opinions
        Croatia                  Decisions
        Cyprus                   Annual Reports, Decisions
        Czech Republic           Annual Reports, Completed Inspections, Court Rulings, Decisions, Opinions, Press Releases
        Denmark                  Annual Reports, Decisions, Permissions
        EDPB (Agency)            Annual Reports, Decisions, Guidelines, Letters, Opinions, Recommendations
        Estonia                  Annual Reports, Instructions, Prescriptions
        Finland                  Advice, Decisions, Guides, Notices
        France                   FUTURE UPDATE
        Germany                  N/A
        Greece                   Annual Reports, Decisions, Guidelines, Opinions, Recommendations
        Hungary                  Annual Reports, Decisions, Notices, Recommendations, Resolutions
        Ireland                  Decisions, Judgements, News
        Italy                    Annual Reports, Hearings, Injunctions, Interviews, Newsletters, Publications
        Latvia                   Annual Reports, Decisions, Guidances, Opinions, Violations
        Lithuania                Decisions, Guidelines, Inspection Reports
        Luxembourg               Annual Reports, Opinions
        Malta                    Guidelines, News Articles
        Netherlands              Decisions, Opinions, Public Disclosures, Reports
        Poland                   Decisions, Tutorials
        Portugal                 Decisions, Guidelines, Reports
        Romania                  Decisions, Reports
        Slovakia                 Fines, Opinions, Reports
        Slovenia                 Blogs, Guidelines, Infographics, Opinions, Reports
        Spain                    Blogs, Decisions, Guides, Infographics, Reports
        Sweden                   Decisions, Guidances, Judgements, Publications
        United Kingdom           Decisions, Judgements, Notices
    """

    # Determine country, path, and instantiate the DPA
    if country == "Austria":
        path = "/austria"
        dpa = Austria(path)
    elif country == "Belgium":
        path = "/belgium"
        dpa = Belgium(path)
    elif country == "Bulgaria":
        path = "/bulgaria"
        dpa = Bulgaria(path)
    elif country == "Croatia":
        path = "/croatia"
        dpa = Croatia(path)
    elif country == "Cyprus":
        path = "/cyrpus"
        dpa = Cyprus(path)
    elif country == "Czech Republic":
        path = "/czech_republic"
        dpa = CzechRepublic(path)
    elif country == "Denmark":
        path = "/denmark"
        dpa = Denmark(path)
    elif country == "EDPB":
        path = "/edpb"
        dpa = EDPB(path)
    elif country == "Estonia":
        path = "/estonia"
        dpa = Estonia(path)
    elif country == "Finland":
        path = "/finland"
        dpa = Finland(path)
    elif country == "France":
        path = "/france"
        dpa = France(path)
    elif country == "Greece":
        path = "/greece"
        dpa = Greece(path)
    elif country == "Hungary":
        path = "/hungary"
        dpa = Hungary(path)
    elif country == "Ireland":
        path = "ireland"
        dpa = Ireland(path)
    elif country == "Italy":
        path = "/italy"
        dpa = Italy(path)
    elif country == "Latvia":
        path = "/latvia"
        dpa = Latvia(path)
    elif country == "Lithuania":
        path = "/lithuania"
        dpa = Lithuania(path)
    elif country == "Luxembourg":
        path = "/luxembourg"
        dpa = Luxembourg(path)
    elif country == "Malta":
        path = "/malta"
        dpa = Malta(path)
    elif country == "Netherlands":
        path = "/netherlands"
        dpa = Netherlands(path)
    elif country == "Poland":
        path = "/poland"
        dpa = Poland(path)
    elif country == "Portugal":
        path = "/portugal"
        dpa = Portugal(path)
    elif country == "Romania":
        path = "/romania"
        dpa = Romania(path)
    elif country == "Slovakia":
        path = "/slovakia"
        dpa = Slovakia(path)
    elif country == "Slovenia":
        path = "/slovenia"
        dpa = Slovenia(path)
    elif country == "Spain":
        path = "/spain"
        dpa = Spain(path)
    elif country == "Sweden":
        path = "/sweden"
        dpa = Sweden(path)
    else:
        path = "/united_kingdom"
        dpa = UnitedKingdom(path)


    # Call appropriate method for desired document type (Note that these are all encompassing, but DPA type will
    # differentiate)
    if document_type == "Decisions":
        dpa.get_docs_Decisions()
    elif document_type == "Guidelines":
        dpa.get_docs_Guidelines()
    else:
        pass


if __name__ == '__main__':
    scrape()













