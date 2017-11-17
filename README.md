medicationCategories  
====================  

%--------------------------------  
Written by Marzyeh Ghassemi, CSAIL, MIT  
Sept 21, 2012 
Updated 13 Nov, 2017
Please contact the author with errors found.  
mghassem {AT} mit {DOT} edu  
%--------------------------------  

Quick script to parse out medications from discharge summaries in MIMIC format. Note that this approach is brute force: it uses minimal NLP, and can be vastly improved. (hint, hint)  

If you use this code, please cite the GitHub project (see below for Bibtex):  
@misc{Ghassemi2012,  
  author = {Ghassemi, Marzyeh},  
  title = {Discharge Summary Based Pre-Admission (Home) Medication Parser},  
  year = {2012},  
  publisher = {GitHub},  
  journal = {GitHub repository},  
  howpublished = {\url{https://github.com/mghassem/medicationCategories}},  
  commit = {PASTE THE COMMIT VERSION YOU'RE USING HERE}  
}  

The script is set up to run on the MIMIC `noteevents` table in a Postgres database. Please refer to the Jupyter Notebook (finddrugs.ipynb) for example usage. 

Thanks!  
Marzyeh
