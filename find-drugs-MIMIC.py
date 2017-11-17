#!/usr/bin/python

#--------------------------------
# Written by Marzyeh Ghassemi, CSAIL, MIT 
# Sept 21, 2012
# Updated for Python 3, added Notebook, db connection
# by Tom J. Pollard 13 Nov, 2017
# Please contact the author with errors found. 
# mghassem {AT} mit {DOT} edu
#--------------------------------

from __future__ import with_statement
import nltk
import os
import os.path
import re
import string
import sys
import time

def addToDrugs(line, drugs, listing, genList):
    """
    ###### function addToDrugs 
    #   line:    line of text to search
    #   drugs:   array to modify
    #   listing: list of search terms in (generic:search list) form
    #   genList: list of all generic keys being searched for
    #
    #   Searches the provided line for drugs that are listed. Inserts 
    #   a 1 in the drugs array provided at the location which maps 
    #   the found key to the generics list
    """
    genList = dict(enumerate(genList))
    genList = dict((v,k) for k, v in genList.items())

    for (generic, names) in listing.items():
        if re.search(names, line, re.I):
            drugs[genList[generic]] = 1
    return drugs

def readDrugs(f, genList):
    """
    ###### function readDrugs 
    #   f:       file
    #   genList: list of search terms in (generic:search list) form
    #
    #   Converts lines of the form "generic|brand1|brand2" to a
    #   dictionary keyed by "generic" with value "generic|brand1|brand2
    """
    lines = f.read()
    generics = re.findall("^(.*?)\|", lines, re.MULTILINE)
    generics = [x.lower() for x in generics]
    lines = lines.split("\n")
    lines = [x.lower() for x in lines]
    genList.append(generics)
    return dict(zip(generics, lines))

def search(NOTES, 
           SSRI_FILE = os.path.join(os.getcwd(), "SSRI_list.txt"), 
           MISC_FILE = os.path.join(os.getcwd(), "MISC_list.txt"),
           SUMMARY_FILE = "output.csv",
           VERBOSE = False):
    """
    ###### Search the notes
    # NOTES: dataframe loaded from the noteevents table
    # SSRI_FILE: list of SSRI drugs to search for
    # MISC_FILE: list of additional drugs to search for
    # 
    # NB: files should have a line for each distinct drug type, 
    #      and drugs should be separated by a vertical bar '|'
    # 
    # LIMIT FOR PARSING: max number of notes to search.
    # OUTPUT: name of the output file.
    """

    if os.path.isfile(SUMMARY_FILE):
        print('The output file already exists.\n\nRemove the following file or save with a different filename:')
        print(os.path.join(os.getcwd(), SUMMARY_FILE))
        return

    starttime = time.time()
    
    # Keep a list of all generics we are looking for
    genList = []

    # Get the drugs into a structure we can use
    with open(SSRI_FILE) as f:
        SSRI = readDrugs(f, genList)
        print("Using drugs from {}".format(SSRI_FILE))
    try: 
        with open(MISC_FILE) as f:
            MISC = readDrugs(f, genList)
            print("Using additional drugs from {}".format(MISC_FILE))
    except:
        MISC = None
    flatList = [item for sublist in genList for item in sublist]

    # Create indices for the flat list
    # This allows us to understand which "types" are being used
    lengths = [len(type) for type in genList]
    prevLeng = 0
    starts = []
    ends = []
    for leng in lengths:
        starts.append(prevLeng)
        ends.append(prevLeng + leng - 1)
        prevLeng = prevLeng + leng

    # Limit the analysis to discharge summaries
    # Comment out because limitation is now in SQL query
    # NOTES = NOTES[NOTES['category'] == 'Discharge summary']

    # Write heads and notes to new doc
    with open(SUMMARY_FILE, 'a') as f_out:
        f_out.write('"ROW_ID","SUBJECT_ID","HADM_ID","HIST_FOUND","DEPRESSION","ADMIT_FOUND","DIS_FOUND","GEN_DEPRESS_MEDS_FOUND","GROUP","SSRI","MISC","' \
            + '","'.join(flatList) + '"\n')

        # Parse each patient record
        print("Reading documents...")

        for note in NOTES.itertuples():
            if note.Index % 100 == 0:
                print("...index: {}. row_id: {}. subject_id: {}. hadm_id: {}. \n".format(note.Index, note.row_id, note.subject_id, note.hadm_id))
                sys.stdout.flush()
            
            # Reset some per-patient variables
            section = ""
            newSection = ""
            admitFound = 0 # admission note found
            dischargeFound = 0 # discharge summary found
            histFound = 0 # medical history found
            depressionHist = 0;
            drugsAdmit = [0]*len(flatList)
            drugsDis = [0]*len(flatList)
            general_depression_drugs = 0

            # Read through lines sequentially
            # If this looks like a section header, start looking for drugs
            for line in note.text.split("\n"): 

                # Searches for a section header based on heuristics
                m = re.search("""^((\d|[A-Z])(\.|\)))?\s*([a-zA-Z',\.\-\*\d\[\]\(\) ]+)(:| WERE | IS | ARE |INCLUDED|INCLUDING)""", line, re.I)
                if m:
                    newSection = ""
                    # Past Medical History Section
                    if re.search('med(ical)?\s+hist(ory)?', line, re.I):
                        newSection = "hist"
                        histFound = 1

                    # Discharge Medication Section                                                        
                    elif re.search('medication|meds', line, re.I) and re.search('disch(arge)?', line, re.I):
                        newSection = "discharge"
                        dischargeFound = 1

                    # Admitting Medication Section
                    elif re.search('admission|admitting|home|nh|nmeds|pre(\-|\s)?(hosp|op)|current|previous|outpatient|outpt|outside|^[^a-zA-Z]*med(ication)?(s)?', line, re.I) \
                    and (section == "admit" or re.search('medication|meds', line, re.I)):
                        newSection = "admit"
                        admitFound = 1                                         
                        
                    # Med section ended, now in non-meds section                        
                    if section != newSection:
                        section = newSection
                
                # If in history section, search for depression
                if 'hist' in section:
                    if re.search('depression', line, re.I):
                        depressionHist = 1

                # If in meds section, look at each line for specific drugs
                elif 'admit' in section:
                    drugsAdmit = addToDrugs(line, drugsAdmit, SSRI, flatList)
                    if MISC:
                        drugsAdmit = addToDrugs(line, drugsAdmit, MISC, flatList)
                    
                    ## Section just has something like 'Depression meds' 
                    if re.search('depression\s+med(ication)?(s)?', line, re.I):
                        general_depression_drugs = 1
                    
                ## Already in meds section, look at each line for specific drugs
                elif 'discharge' in section:
                    drugsDis = addToDrugs(line, drugsDis, SSRI, flatList)
                    if MISC:
                        drugsDis = addToDrugs(line, drugsDis, MISC, flatList)                        
                    
                # A line with information which we are uncertain about... 
                elif re.search('medication|meds', line, re.I) and re.search('admission|discharge|transfer', line, re.I):
                    if VERBOSE:
                        print('?? {}'.format(line))
                    pass

            group = 0
            # Group 0: Patient has no medications on admission section (or no targeted meds) 
            #          and medications on discharge from the list
            if dischargeFound == 1 and (1 in drugsDis) and (admitFound == 0 or not(1 in drugsAdmit)):        
                group = 0

            # Group 1: Patient has a medications on admission section with no targeted meds
            #          and no medications on discharge
            elif admitFound == 1 and not(1 in drugsAdmit) and (dischargeFound == 0) and general_depression_drugs == 0:
                group = 1

            # Group 2: Patient has medications on admission section, but none from the list
            #          and no medications on discharge from the list
            elif admitFound == 1 and not(1 in drugsAdmit) and dischargeFound == 1 and not(1 in drugsDis) and general_depression_drugs == 0:
                group = 2                                

            # Group 3: Patient has medications on admission (at least one from the list)
            elif (1 in drugsAdmit):
                group = 3
                                
            else:
                if VERBOSE:
                    print('Uncertain about group type for row_id = {}'.format(note.row_id))
                pass

            if VERBOSE:
                print('group is {}'.format(group))

            # Combine the admit and discharge drugs lists
            combined = [w or x for w, x in zip(drugsAdmit, drugsDis)]
        
            # Count the types of each drug
            member = []
            member = [int(1 in drugsAdmit[s:e+1]) for s, e in zip(starts, ends)]

            # save items to csv
            f_out.write(str(note.row_id) + "," + str(note.subject_id) + "," + str(note.hadm_id) + "," + str(histFound) + "," \
                + str(depressionHist) + "," + str(admitFound) + "," + str(dischargeFound) + "," \
                + str(general_depression_drugs) + "," + str(group) + "," + ",".join(map(str, member)) \
                + "," + ",".join(map(str, drugsAdmit)) + "\n")

    # Print summary of analysis
    stoptime = time.time()
    print("Done analyzing {} documents in {} seconds ({} docs/sec)".format(len(NOTES), 
        round(stoptime - starttime, 2), round(len(NOTES) / (stoptime - starttime), 2)))
    print("Summary file is in {}".format(os.getcwd()))
