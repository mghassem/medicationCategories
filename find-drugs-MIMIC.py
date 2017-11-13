#!/usr/bin/python

#--------------------------------
# Written by Marzyeh Ghassemi, CSAIL, MIT 
# Sept 21, 2012
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

# PATH TO DIRECTORY WITH NOTES
NOTES_PATH = "dir/Path/Needed"

# LIMIT FOR PARSING
NUM_FILES_LIMIT = None

# PATH TO FILES WITH DRUGS
#   Files should have a line for each distinct drug type, 
#   and drugs shld be separated by a vertical bar '|'
DRUGS_LIST_PATH = "dir/Path/Needed"
SSRI_FILE = os.path.join(DRUGS_LIST_PATH, "SSRI_list.txt")
MISC_FILE = os.path.join(DRUGS_LIST_PATH, "MISC_list.txt")

# OUTPUT
SUMMARY_FILE = "dir/output.csv"


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
    genList = dict((v,k) for k, v in genList.iteritems())

    for (generic, names) in listing.iteritems():
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

def main():
    # Print the variables being used for inputs
    print "Using %s notes from %s" % (NUM_FILES_LIMIT or "ALL", NOTES_PATH)
    print "Using drugs from %s" % (DRUGS_LIST_PATH)
    starttime = time.time()
    
    # Keep a list of all generics we are looking for
    genList = []

    # Get the drugs into a structure we can use
    with open(SSRI_FILE) as f:
        SSRI = readDrugs(f, genList)
    with open(MISC_FILE) as f:
        MISC = readDrugs(f, genList)
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
    
    # Get the list of filenames (unqualified)
    filenames = filter(lambda x: os.path.isfile(os.path.join(NOTES_PATH, x)), 
        os.listdir(NOTES_PATH))
    filenames = filenames[:NUM_FILES_LIMIT]

    # Write heads and notes to new doc
    with open(SUMMARY_FILE, 'w') as f_out:
        print >>f_out, "SUBJECT_ID|HIST_FOUND|DEPRESSION|ADMIT_FOUND|DIS_FOUND|GEN_DEPRESS_MEDS_FOUND|GROUP|SSRI|MISC|" + "|".join(flatList) + "\n"

        # Parse each patient record
        print "Reading documents..."
        for i, doc in enumerate(filenames):
            if i % 100 == 0:
                print "%d.. %s\n" % (i, doc),
                sys.stdout.flush()

            # Read heads and notes from doc
            with open(os.path.join(NOTES_PATH, doc)) as f:
                
                # Read in the headers
                nheads = f.readline().strip().split("_:-:_")
                heads = nheads[:-1]

                # Create a regex to match notes from the headers
                regex = "^" + "_:-:_".join("(?P<%s>.*?)" % (x) for x in heads) + "$"

                # Read the notes
                matches = re.finditer(regex, f.read(), re.MULTILINE | re.DOTALL)
                notes = [m.groupdict() for m in matches]
                
                # Find the first discharge summary
                for note in notes:
                    if re.search('discharge.*summary', note['CATEGORY'], re.I):
                        notes = note
                        break
                
                # Reset some per-patient variables
                section = ""
                newSection = ""
                admitFound = 0
                dischargeFound = 0
                histFound = 0
                depressionHist = 0;
                drugsAdmit = [0]*len(flatList)
                drugsDis = [0]*len(flatList)
                general_depression_drugs = 0
                m = re.search('NOTE-EVENTS-([0-9]+).txt', doc, re.I)
                sid = int(m.group(1))

                # Read through lines sequentially
                # If this looks like a section header, start looking for drugs
                for line in note['TEXT'].split("\n"):    

                    # Searches for a section header based on my heuristics
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
                        elif re.search('admission|admitting|home|nh|nmeds|pre(\-|\s)?(hosp|op)|current|previous|outpatient|outpt|outside|^[^a-zA-Z]*med(ication)?(s)?', line, re.I) and (section == "admit" or re.search('medication|meds', line, re.I)):
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
                        drugsAdmit = addToDrugs(line, drugsAdmit, MISC, flatList)
                        
                        ## Section just has something like 'Depression meds' 
                        if re.search('depression\s+med(ication)?(s)?', line, re.I):
                            general_depression_drugs = 1
                        
                    ## Already in meds section, look at each line for specific drugs
                    elif 'discharge' in section:
                        drugsDis = addToDrugs(line, drugsDis, SSRI, flatList)
                        drugsDis = addToDrugs(line, drugsDis, MISC, flatList)                        
                        
                    # A line with information which we are uncertain about... 
                    elif re.search('medication|meds', line, re.I) and re.search('admission|discharge|transfer', line, re.I):
                        print '?? ' + line

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
                print 'Uncertain about group type for ' + doc

            print 'group is ' + str(group) 

            # Combine the admit and discharge drugs lists
            combined = [w or x for w, x in zip(drugsAdmit, drugsDis)]
        
            # Count the types of each drug
            member = []
            member = [int(1 in drugsAdmit[s:e+1]) for s, e in zip(starts, ends)]

            # Print items for this patient into csv
            print >>f_out, str(sid) + "|" + str(histFound) + "|" + str(depressionHist) + "|" + str(admitFound) + "|" + str(dischargeFound) + "|" + str(general_depression_drugs) + "|" + str(group) + "|" + "|".join(map(str, member)) + "|" + "|".join(map(str, drugsAdmit)) + "\n"

    # Print analysis
    stoptime = time.time()
    print "Done analyzing %d documents in %.2f seconds (%.2f docs/sec)" % (i, stoptime - starttime, i / (stoptime - starttime))
    print "Summary file is in %s" % (DRUGS_LIST_PATH)
            
if __name__ == "__main__":
    main()

