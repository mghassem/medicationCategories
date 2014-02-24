medicationCategories
====================

Quick script to parse out medications from discharge summaries in MIMIC format. 

Note that this approach is brute force: it uses minimal NLP, and can be vastly improved. (hint, hint)

The script is set up to use a specific export of the MIMIC notes database. Essentially, this is a directory with a file per patient, and within that file the patient notes separated by a _*:-:*_ delimiter. So you'll need to modify to suit the format you export to. 
