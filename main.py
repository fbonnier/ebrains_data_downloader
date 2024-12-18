import os
import sys
import argparse
import json as json
import warnings
import urllib.request
import zipfile
import tarfile
import rarfile
import shutil
import re
import traceback
# from nilsimsa import Nilsimsa

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
        with urllib.request.urlopen(url) as response, open(filepath, 'wb') as out_file:
            data = response.read() # a `bytes` object
            out_file.write(data)
    except Exception as e:
        print (str("".join(traceback.format_exception(e))))

# def compute_hash (filepath: str) -> str:
#     filehash = None
#     try:
#         all_info = os.path.basename(filepath) + str(os.path.getsize(filepath))
#         filehash = Nilsimsa(all_info).hexdigest()
#     except Exception as e:
#         print (e)

#     return filehash


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Download and extract data from HBP metadata JSON file. Only code will be extracted")

    parser.add_argument("--json", type=argparse.FileType('r'), metavar="JSON Metadata file", nargs=1, dest="json", default="",\
    help="JSON File that contains Metadata of the HBP model to run", required=True)
    
    ## Reference report location for regressions test
    ## The output report will be compared to this reference report
    parser.add_argument("--test", type=str, metavar="Reference report", nargs=1, dest="test", default="", help="Reference report for regression tests. The output report will be compared to this reference report. JSON file")


    args = parser.parse_args()
    test = None
    # Load JSON data
    json_file = args.json[0]
    if not json_file:
        print ("Fatal Error:  Invalid JSON File, please give a valid JSON file using \"--json <path-to-file>\"")
        exit(1)
    json_data = json.load(json_file)

    # Load workdir
    workdir = json_data["Metadata"]["workdir"]

    # Create directories
    os.mkdir(workdir + "/code/")
    os.mkdir(workdir + "/inputs/")
    os.mkdir(workdir + "/outputs/")

    # Load workflow
    workflow_run_file = json_data["Metadata"]["workflow"]["run"]
    workflow_data_file = json_data["Metadata"]["workflow"]["data"]
    # Download workflow runfile
    if workflow_run_file["url"] and workflow_run_file["filepath"]:
        download_data(workflow_run_file["url"], workflow_run_file["filepath"])
    # Download workflow datafile
    if workflow_data_file["url"] and workflow_data_file["filepath"]:
        download_data(workflow_data_file["url"], workflow_data_file["filepath"])
    
    # Load inputs
    inputs = json_data["Metadata"]["run"]["inputs"]
    # Download inputs
    for iinput in inputs:
        if iinput["url"] and iinput["filepath"]:
            download_data(iinput["url"], iinput["filepath"])

    # Load outputs
    outputs = json_data["Metadata"]["run"]["outputs"]
    # Download outputs
    for ioutput in outputs:
        if ioutput["url"] and ioutput["filepath"]:
            download_data(ioutput["url"], ioutput["filepath"])

    # Load code
    # Download code
    for icode in json_data["Metadata"]["run"]["code"]:
        assert(icode["url"] != None)

        if icode["url"] and icode["filepath"]:
            download_data(url=icode["url"], filepath=icode["filepath"])
        try:
            # Unpack code to run
            shutil.unpack_archive(icode["filepath"], icode["path"])
        except Exception as e:
            print ("Shutil failed: " + str(e))
            print ("Trying Archiver")
            os.system("arc -overwrite unarchive " + icode["filepath"] + " " + icode["path"])

        # Control code as output
        control_foler = icode["path"].replace("code", "outputs")
        try:
            # Unpack control code as outputs
            shutil.unpack_archive(icode["filepath"], control_foler)
        except Exception as e:
            print ("Shutil failed for control group: " + str(e))
            print ("Trying Archiver")
            os.system("arc -overwrite unarchive " + icode["filepath"] + " " + control_foler)

        # Add all files of code as potential outputs/results
        try:
            for current_dir, subdirs, files in os.walk( control_foler ):
                for filename in files:
                    relative_path = os.path.join( current_dir, filename )
                    absolute_path = os.path.abspath( relative_path )
                    json_data["Metadata"]["run"]["outputs"].append({"url": None,  "path": str(absolute_path), "filepath": absolute_path + filename, "hash": None})
                    # print (absolute_path)
        except Exception as e:
            print (e)

    # Compute filenames and size of outputs
    for ioutput in json_data["Metadata"]["run"]["outputs"]:
        ioutput["filename"] = os.path.basename(ioutput["filepath"])
        ioutput["size"] = os.path.getsize(ioutput["filepath"])

    with open(str(json_data["Metadata"]["workdir"] + "/data-report.json"), "w") as f:
        json.dump(json_data, f, indent=4) 
    # Exit Done ?
    if "data-report.json" in os.listdir(json_data["Metadata"]["workdir"]):
        print ("Download data report File created successfully")
    
    # Regression tests
    if test:
        run_test(test=test)
    
    
    sys.exit()
