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

@click.group()

def cli():
    pass


@cli.command()
@click.option('--country', default='EDPB', help='The country to obtain document from.')
@click.option('--document_type', default='Docs', help='The type of documents to include.')
@click.option('--path', default=None, help='File path where scraped documents should be stored.')
@click.option('--overwrite', default=False, help='Set to True if scraper should overwrite existing documents.')


def scrape(country, document_type, path, overwrite):

    """
        \b
        SUPPORTED COUNTRIES:     DOCUMENTS TYPES:

        \b
        Austria                  Decisions
        Belgium                  Annual Reports, Decisions, Opinions
        Bulgaria                 Annual Reports, Opinions
        Croatia                  Decisions (Selenium)
        Cyprus                   Annual Reports (Selenium), Decisions
        Czech Republic           Annual Reports, Completed Inspections, Court Rulings, Decision Making Activities,
                                    Decision of President, Opinions, Press Releases
        Denmark                  Annual Reports, Decisions, Permissions (All Selenium)
        EDPB (Agency)            Annual Reports, Decisions, Guidelines, Letters, Opinions, Recommendations
        Estonia                  Annual Reports (Selenium), Instructions, Prescriptions
        Finland                  Docs (Advice, Decisions, Guides, Notices)
        France                   FUTURE UPDATE
        Germany                  N/A
        Greece                   Annual Reports, Decisions, Guidelines, Opinions, Recommendations
        Hungary                  Annual Reports, Decisions, Notices, Recommendations, Resolutions
        Ireland                  Blogs, Decisions, Judgements, News, Publications
        Italy                    Annual Reports, Hearings, Injunctions, Interviews, Newsletters, Publications
        Latvia                   Annual Reports, Decisions, Guidances, Opinions, Violations
        Lithuania                Decisions, Guidelines (Selenium), Inspection Reports (Selenium)
        Luxembourg               Annual Reports, Opinions
        Malta                    Guidelines, News Articles (Selenium)
        Netherlands              Decisions, Opinions, Public Disclosures, Reports
        Poland                   Decisions, Tutorials (Selenium)
        Portugal                 Decisions, Guidelines, Reports
        Romania                  Docs (Decisions, Reports)
        Slovakia                 Fines & Reports, Opinions (Selenium)
        Slovenia                 Blogs, Guidelines, Infographics, Opinions, Reports
        Spain                    Blogs, Decisions, Guides, Infographics, Reports
        Sweden                   Decisions & Judgements, Guidances (Selenium), Publications
        United Kingdom           Enforcements, Notices, Reports
    """

    # Path is where the user stores documents, something like: '/Users/evanjacobs/Desktop/test_scraper'
    # If no path is give, exit
    if path is None:
        sys.exit("No file path given.")

    try:
        os.makedirs(path)
    except FileExistsError:
        pass

    # Create visitedDocs.txt if it doesn't already exist
    try:
        hashFile = open(path + "/visitedDocs.txt", "x")
        hashFile.close()
    except FileExistsError:
        print('visitedDocs already exists')
        pass

    existing_docs = []
    # Open visitedDocs.txt and read the contents into existing_docs list
    # Change this to use .readlines() and get contents all at once into list
    with open(path + "/visitedDocs.txt") as file:
        for line in file:
            hash_n_stripped = line.rstrip('\n')
            # Add the hash's in visitedDocs.txt to existing_docs
            existing_docs.append(hash_n_stripped)

    # Open the file again (with 'append'), since it is closed after previous looping
    hashFile = open(path + "/visitedDocs.txt", "a")

    # Determine country, path, and instantiate the DPA
    if country == "Austria":
        #path = "/austria"
        dpa = Austria(path=path)
    elif country == "Belgium":
        #path = "/belgium"
        dpa = Belgium(path=path)
    elif country == "Bulgaria":
        #path = "/bulgaria"
        dpa = Bulgaria(path=path)
    elif country == "Croatia":
        #path = "/croatia"
        dpa = Croatia(path=path)
    elif country == "Cyprus":
        #path = "/cyrpus"
        dpa = Cyprus(path=path)
    elif country == "Czech Republic":
        #path = "/czech_republic"
        dpa = CzechRepublic(path=path)
    elif country == "Denmark":
        #path = "/denmark"
        dpa = Denmark(path=path)
    elif country == "EDPB":
        # path = "/edpb"
        dpa = EDPB(path=path)
    elif country == "Estonia":
        #path = "/estonia"
        dpa = Estonia(path=path)
    elif country == "Finland":
        #path = "/finland"
        dpa = Finland(path=path)
    elif country == "France":
        #path = "/france"
        dpa = France(path=path)
    elif country == "Greece":
        #path = "/greece"
        dpa = Greece(path=path)
    elif country == "Hungary":
        #path = "/hungary"
        dpa = Hungary(path=path)
    elif country == "Ireland":
        #path = "ireland"
        dpa = Ireland(path=path)
    elif country == "Italy":
        #path = "/italy"
        dpa = Italy(path=path)
    elif country == "Latvia":
        #path = "/latvia"
        dpa = Latvia(path=path)
    elif country == "Lithuania":
        #path = "/lithuania"
        dpa = Lithuania(path=path)
    elif country == "Luxembourg":
        #path = "/luxembourg"
        dpa = Luxembourg(path=path)
    elif country == "Malta":
        #path = "/malta"
        dpa = Malta(path=path)
    elif country == "Netherlands":
        #path = "/netherlands"
        dpa = Netherlands(path=path)
    elif country == "Poland":
        #path = "/poland"
        dpa = Poland(path=path)
    elif country == "Portugal":
        #path = "/portugal"
        dpa = Portugal(path=path)
    elif country == "Romania":
        #path = "/romania"
        dpa = Romania(path=path)
    elif country == "Slovakia":
        #path = "/slovakia"
        dpa = Slovakia(path=path)
    elif country == "Slovenia":
        #path = "/slovenia"
        dpa = Slovenia(path=path)
    elif country == "Spain":
        #path = "/spain"
        dpa = Spain(path=path)
    elif country == "Sweden":
        #path = "/sweden"
        dpa = Sweden(path=path)
    else:
        #path = "/united_kingdom"
        dpa = UnitedKingdom(path=path)


    # Call appropriate method for desired document type (Note that these are all encompassing, but DPA type will
    # differentiate)
    if document_type == "Decisions":
        added_docs = dpa.get_docs_Decisions(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Guidelines":
        added_docs = dpa.get_docs_Guidelines(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Annual Reports":
        # existing_docs contains document hashes from visitedDocs.txt
        # added_docs contains hashes of freshly downloaded documents
        added_docs = dpa.get_docs_AnnualReports(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Recommendations":
        added_docs = dpa.get_docs_Recommendations(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Opinions":
        added_docs = dpa.get_docs_Opinions(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Letters":
        added_docs = dpa.get_docs_Letters(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Guides":
        added_docs = dpa.get_docs_Guides(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Permissions":
        added_docs = dpa.get_docs_Permissions(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Instructions":
        added_docs = dpa.get_docs_Instructions(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Prescriptions":
        added_docs = dpa.get_docs_Prescriptions(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Notices":
        added_docs = dpa.get_docs_Notices(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Resolutions":
        added_docs = dpa.get_docs_Resolutions(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Interviews":
        added_docs = dpa.get_docs_Interviews(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Publications":
        added_docs = dpa.get_docs_Publications(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Newsletters":
        added_docs = dpa.get_docs_Newsletters(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Injunctions":
        added_docs = dpa.get_docs_Injunctions(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Hearings":
        added_docs = dpa.get_docs_Hearings(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Judgements":
        added_docs = dpa.get_docs_Judgements(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Reports":
        added_docs = dpa.get_docs_Reports(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Enforcements":
        added_docs = dpa.get_docs_Enforcements(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Guidances":
        added_docs = dpa.get_docs_Guidances(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Blogs":
        added_docs = dpa.get_docs_Blogs(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Infographics":
        added_docs = dpa.get_docs_Infographics(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Tutorials":
        added_docs = dpa.get_docs_Tutorials(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Public Disclosures":
        added_docs = dpa.get_docs_publicDisclosure(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "News Articles":
        added_docs = dpa.get_docs_NewsArticles(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Inspection Reports":
        added_docs = dpa.get_docs_InspectionReports(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Violations":
        added_docs = dpa.get_docs_Violations(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "News":
        added_docs = dpa.get_docs_News(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Press Releases":
        added_docs = dpa.get_docs_PressReleases(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Court Rulings":
        added_docs = dpa.get_docs_CourtRulings(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Completed Inspections":
        added_docs = dpa.get_docs_CompletedInspections(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Fines & Reports":
        added_docs = dpa.get_docs_fineAndReports(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Decisions & Judgements":
        added_docs = dpa.get_docs_decisionsAndJudgements(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Decision Of President":
        added_docs = dpa.get_docs_DecisionOfPresident(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Decision Making Activities":
        added_docs = dpa.get_docs_DecisionMakingActivites(existing_docs=existing_docs, overwrite=overwrite)
    elif document_type == "Docs":
        added_docs = dpa.get_docs(existing_docs=existing_docs, overwrite=overwrite)
    else:
        sys.exit("'document_type' argument doesn't match an existing document type. Use --help for more info.")
        pass

    # Iterate through added_docs and add hashes to visitedDocs.txt
    for document_hash in added_docs:
        # Document_hash isn't in visitedDocs.txt -> add it
        document_hash_newline = document_hash + "\n"
        hashFile.write(document_hash_newline)

    # Lets us see written contents during run time
    hashFile.flush()
    # Close visited docs when done scraping
    hashFile.close()

if __name__ == '__main__':
    scrape()