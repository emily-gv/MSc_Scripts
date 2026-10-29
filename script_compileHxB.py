"""
Created on Fri Oct 23 13:21 2026

@author: Emily Garcia-Volk
"""

import os
import shutil

target_subfolder = "HxB" # name of subfolders containing filtered values
output_folder_name = "HxB_Compiled" # where all EDF and CSV files will be put
ignore_folders = [ # Based on manual verification of problem folders from script_batchSortEDF
    # "BIM 1022_P2,"
]

parent_folder = ""

def get_hxb_files(parent_folder):
    if not os.path.exists(parent_folder):
        print("Parent folder does not exist")
        return

    subfolders = [f.path for f in os.scandir(parent_folder) if f.is_dir()] 
    subfolders_filtered = [f for f in subfolders if 'BIM' in os.path.basename(f) and os.path.basename(f) not in ignore_folders] 

    # Report ignored folders
    ignored_found = [
        os.path.basename(f) for f in subfolders
        if os.path.basename(f) in ignore_folders
    ]

    print(f"Folders ignored: {len(ignored_found)}")
    for folder in ignored_found:
        print(f"  - {folder}")

    output_folder = os.path.join(parent_folder, output_folder_name)
    os.makedirs(output_folder, exist_ok=True)

    flagged_folders = []

    for s in subfolders_filtered:
        print(f"\nProcessing folder: {os.path.basename(s)}")

        hxb_folder = os.path.join(s, target_subfolder)

        # Find .edf and .csv files in each BIM folder
        input_files = [f for f in os.scandir(hxb_folder) if f.is_file() and f.name.lower().endswith(("filtered.edf", ".csv"))]

        csv_files = [f for f in input_files if f.name.lower().endswith(".csv")]
        edf_files = [f for f in input_files if f.name.lower().endswith(".edf")]

        # Ensure exactly one CSV and one EDF file
        if len(csv_files) != 1 or len(edf_files) != 1:
            message = (f"WARNING: {os.path.basename(s)}: expected 1 .csv and 1 filtered.edf, found {len(csv_files)} CSV and {len(edf_files)} EDF. Folder skipped.")
            flagged_folders.append(message)
            continue

        for f in input_files: 
            copied_path = os.path.join(output_folder, f.name)
            if not os.path.exists(copied_path):
                try: 
                    shutil.copy2(f.path, copied_path)
                    print(f"\tCopied: {f.name}")
                except Exception as e:
                    message = (f"WARNING: {os.path.basename(s)}: failed to copy >> {original_name}: {e}")
                    flagged_folders.append(message)
                    continue
            else:
                print(f"\tUsing existing copy: {copied_path}")

        # SUMMARY STATS:
    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)

    print(f"BIM folders found: {len(subfolders_filtered)}")
    print(f"Folders flagged: {len(flagged_folders)}")

    if flagged_folders:
        print("\nFolders requiring attention:")
        for message in flagged_folders:
            print(f"  - {message}")
    else:
        print("All folders processed without errors.")

    print("=" * 60)

get_hxb_files(parent_folder)
# get_hxb_files("/home/emilygv/Desktop/TESTING_EDF")