# GDPRxiv crawler

![](https://github.com/GDPRxiv/crawler)

### Package Testing Notes:
Removed google-cloud-translate==2.0.1 from requirements. This package was conflicting with textract==1.6.3, as 
google-cloud-translate requires package six==1.13.0 while textract requires package six==1.12.0. This error occurs
when downloading GDPRxiv crawler as a package (tested using virtual env).

### Requirements
To be included...


### Installing
To install this CLI tool you can run the below command
```
pip3 install "GDPRxiv crawler"
```

### Usage
Scrape desired documents:
```
gdprCrawler scrape --country <desired country> --document_type <type of document> --path <Directory to store documents>
```
<pre>
SUPPORTED COUNTRIES:     DOCUMENTS TYPES:

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
</pre>