import os
import sys
import argparse
import json as json
import urllib.request
import shutil
import traceback

file_default_value = {"url": None, "path": None, "filepath": None, "hash": None, "filename": None, "size": None}


def get_dataset_from_local_file(output_local_file):
    return

def isarchive(filepath:str) -> bool :
    toreturn = False
    for iformat in shutil.get_unpack_formats():
        try:
            if filepath.rsplit('.', 1)[1] in iformat:
                toreturn = True
        except:
            toreturn = False
    return toreturn
    
def extract_archive(filepath:str, destpath:str) -> str :
    try:
        shutil.unpack_archive(filepath, destpath)
    except Exception as e:
        print ("Shutil failed: " + str(e))
        print ("Trying Archiver")
        status = os.WEXITSTATUS(os.system("arc -overwrite unarchive " + filepath + " " + destpath))
        if not status:
            destpath = None
            print("Unabled to extract " + filepath)
    return destpath

def collect_files(path):
    newfiles = []

    # Collect files in folder and subfolders
    try:
        for current_dir, subdirs, files in os.walk( path ):
            for filename in files:
                relative_file_path = os.path.join( current_dir, filename )
                # absolute_path = os.path.abspath( relative_file_path )
                newfiles.append({   "url": None,\
                                "path": str(current_dir),\
                                "filepath": str(relative_file_path),\
                                "filename": os.path.basename(filename),\
                                "size": os.path.getsize(relative_file_path)})
    except Exception as e:
        print (e)

    return newfiles

# Compare report files for regression tests
def compare_reports (test_report=None, reference_report=None):
    # Test if reports are not None
    if (not test_report and not reference_report):
        print("ERROR: reference test failure: " + str(reference_report))
        exit (1)

    try:
        with open(test_report, 'r') as test_report_file, open (reference_report, 'r') as reference_report_file:
            test_items = json.load(test_report_file)
            reference_items = json.load(reference_report_file)

            # Compare the dictionnaries
            if sorted(test_items) != sorted(reference_items):
                print("ERROR Test: reports are not equal. Failure")
                exit(1)
            else:
                print ("Regression test SUCCESS for " + str(test_items["Metadata"]["id"]))
                exit(0)

    except Exception as e:
        print (str("".join(traceback.format_exception(e))))
        exit (1)
    

# Run requested test
# Download Metadata and compare output report to reference report
def run_test (test=None):
    compare_reports(test_report="./data-report.json", reference_report=test)


def download_data (url: str, filepath: str):
    
    try:
        with urllib.request.urlopen(url) as response, open(filepath, 'wb+') as out_file:
            print ("Downloading " + str(url) + " to " + str(filepath) + "\n")
            data = response.read() # a `bytes` object
            out_file.write(data)
            print ("Download completed: " + str(filepath) + "\n")
    except Exception as e:
        print (str("".join(traceback.format_exception(e))))



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Download and extract data from HBP metadata JSON file. Only code will be extracted")

    parser.add_argument("--json", type=argparse.FileType('r'), metavar="JSON Metadata file", nargs=1, dest="json", default="",\
    help="JSON File that contains Metadata of the HBP model to run", required=True)

    parser.add_argument("--outputs", type=str, metavar="Local output file", nargs=1, dest="outputs", default="",\
    help="JSON File that contains Metadata of the HBP model to run", required=True)
    
    ## Reference report location for regressions test
    ## The output report will be compared to this reference report
    parser.add_argument("--test", type=str, metavar="Reference report", nargs=1, dest="test", default="", help="Reference report for regression tests. The output report will be compared to this reference report. JSON file")

    parsed, args = parser.parse_known_args()

    test = str(parsed.test[0]) if parsed.test else None
    outputs_local = str(parsed.outputs[0]) if parsed.outputs else None

    # Load JSON data
    json_file = parsed.json[0]
    if not json_file:
        print ("Fatal Error:  Invalid JSON File, please give a valid JSON file using \"--json <path-to-file>\"")
        exit(1)
    json_data = json.load(json_file)

    # Load workdir
    workdir = json_data["Metadata"]["workdir"]

    # # Create directories
    # os.mkdir(workdir + "/code/")
    # os.mkdir(workdir + "/inputs/")
    # os.mkdir(workdir + "/outputs/")

    # Load workflow
    workflow_run_file = json_data["Metadata"]["workflow"]["run"]
    workflow_data_file = json_data["Metadata"]["workflow"]["data"]
    # Download workflow runfile
    if workflow_run_file["url"] and workflow_run_file["filepath"]:
        download_data(workflow_run_file["url"], workflow_run_file["filepath"])
        workflow_run_file["path"] = workflow_run_file["filepath"]
    # Download workflow datafile
    if workflow_data_file["url"] and workflow_data_file["filepath"]:
        download_data(workflow_data_file["url"], workflow_data_file["filepath"])
        workflow_data_file["path"] = workflow_data_file["filepath"]
    
####################################################################################################
    # Load inputs                                                                                  #
####################################################################################################
    inputs = json_data["Metadata"]["run"]["inputs"]
    # Download inputs
    for iinput in inputs:
        if iinput["url"] and iinput["filepath"]:
            download_data(iinput["url"], iinput["filepath"])
    # Extract archived inputs
    for iinput in inputs:
        if iinput["filepath"] and isarchive(iinput["filepath"]):
            iinput["path"] = extract_archive(iinput["filepath"], iinput["path"])
    # and collect extracted inputs
    new_inputs = []
    for iinput in inputs:
        if iinput["filepath"] and isarchive(iinput["filepath"]):
            new_inputs += collect_files(iinput["path"])
    # Add new collected inputs to report
    json_data["Metadata"]["run"]["inputs"] += new_inputs
    # Remove archived inputs
    for iinput in json_data["Metadata"]["run"]["inputs"]:
        if iinput["filepath"] and isarchive(iinput["filepath"]) and iinput not in new_inputs:
            json_data["Metadata"]["run"]["inputs"].remove(iinput)
    
####################################################################################################

####################################################################################################
    # Load outputs                                                                                 #
####################################################################################################
    outputs = json_data["Metadata"]["run"]["outputs"]
    # Load local outputs
    if outputs_local:
        #TODO support multiple local outputs
        if os.path.exists(str(outputs_local)):
            outputs.append ({"url": None,\
                             "path": "outputs/" + str(os.path.basename(outputs_local).split(".")[0]),\
                             "filepath": "outputs/" + str(os.path.basename(outputs_local)),\
                             "hash": None,\
                             "filename": str(os.path.basename(outputs_local)),\
                             "size": str(os.path.getsize(outputs_local))})
            # Move outputs_local to outputs
            shutil.copy(outputs_local, "outputs/" + str(os.path.basename(outputs_local)))
        else:
            print ("Local outputs do not exist, check path " + str(outputs_local))

    # Download outputs
    for ioutput in outputs:
        if ioutput["url"] and ioutput["filepath"]:
            download_data(ioutput["url"], ioutput["filepath"])
            # Complete metadata
            ioutput["filename"] = os.path.basename(ioutput["filepath"])
            ioutput["size"] = os.path.getsize(ioutput["filepath"])
        
    # Extract archived outputs
    for ioutput in outputs:
        if ioutput["filepath"] and isarchive(ioutput["filepath"]):
            ioutput["path"] = extract_archive(ioutput["filepath"], ioutput["path"])
    
    # and collect extracted outputs
    new_outputs = []
    for ioutput in outputs:
        if ioutput["filepath"] and isarchive(ioutput["filepath"]):
            new_outputs += collect_files(ioutput["path"])
    
    # Add new collected outputs to report
    json_data["Metadata"]["run"]["outputs"] += new_outputs

    # Remove archived outputs
    for ioutput in json_data["Metadata"]["run"]["outputs"]:
        if ioutput["filepath"] and isarchive(ioutput["filepath"]) and ioutput not in new_outputs:
            json_data["Metadata"]["run"]["outputs"].remove(ioutput)
    
    # Complete path as filepath for output files
    for ioutput in  json_data["Metadata"]["run"]["outputs"]:
        ioutput["path"] = ioutput["filepath"]

####################################################################################################


####################################################################################################
    # Load code                                                                                    #
####################################################################################################
    # Download code
    for icode in json_data["Metadata"]["run"]["code"]:
        assert icode["url"] != None

        if icode["url"] and icode["filepath"]:
            download_data(url=icode["url"], filepath=icode["filepath"])
        
        # Code must be archived
        assert isarchive(icode["filepath"]), str("Code " + icode["url"] + " is not an archive")
        
        # Unpack code to run
        icode["path"] = extract_archive(icode["filepath"], icode["path"])
        
        # Control code as output, if outputs are not provided
        # if not json_data["Metadata"]["run"]["outputs"]:
        #     control_foler = icode["path"].replace("code", "outputs")
        #     # Unpack code as output
        #     control_foler = extract_archive(icode["filepath"], control_foler)
            
        #     # Add all files of code as potential outputs/results
        #     new_outputs = collect_files(control_foler)
        #     json_data["Metadata"]["run"]["outputs"] += new_outputs
        
####################################################################################################

    # # Compute filenames and size of outputs
    # for ioutput in json_data["Metadata"]["run"]["outputs"]:
    #     ioutput["filename"] = os.path.basename(ioutput["filepath"])
    #     ioutput["size"] = os.path.getsize(ioutput["filepath"])

    # Write metadata to report
    with open(str("data-report.json"), "w") as f:
        json.dump(json_data, f, indent=4) 
    # Exit Done ?
    if "data-report.json" in os.listdir(json_data["Metadata"]["workdir"]):
        print ("Download data report File created successfully")
    
    # Regression tests
    if test:
        run_test(test=test)
    
    sys.exit()
