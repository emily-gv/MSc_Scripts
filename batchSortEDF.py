"""
Created on Wed Oct 15 14:38 2026

@author: Emily Garcia-Volk
"""

# https://github.com/holgern/pyedflib
# https://pyedflib.readthedocs.io/en/latest/ref/highlevel.html
# Requirements: numpy, pandas, pyedflib,  openpyxl

from pyedflib import highlevel
import os
import shutil
import numpy as np
import pandas as pd
import re

# Replace with channels for applicable version of the sleep kits
# CHANNELS = ["SpO2", "Pulse"] # Embletta
CHANNELS = ["Oximeter", "Pulse"] # Cerebra

# Select parent folder naming format:
# "BIM_ID" = BIM1234 + description (extract BIM1234)
    # Will append PHASE to file_id(BIM1234_P4)
# "FULL_NAME" = BIM1234-1 (keep entire folder name)
# "BIM_II" format = BIM 1234_P#

FOLDER_FORMAT = "FULL_NAME"
PHASE = "P4"

"""
Iterates through parents folder and identifies folders labelled 'BIM...'
Transfers .EDF/.REC file from into an HxB subfolder, then extracts the specified channels and:
    1. Creates a new .EDF file with just the filtered channels
    2. Creates intermediate .txt and .xlsx files
    3. Creates a final .csv file (named [BIM-ID]_Sagatech.csv)

Script will never delete or overwrite data. If an HxB folder already exists, the BIM-ID is flagged for manual review.
"""
def sort_edf(parent_folder_to_sort):
    parent_folder = parent_folder_to_sort
    if not os.path.exists(parent_folder):
        print("Parent folder does not exist")
        return

    # 1: Iterate through all folders starting with BIM
    subfolders = [f.path for f in os.scandir(parent_folder) if f.is_dir()] # tested, good
    subfolders_filtered = [f for f in subfolders if 'BIM' in os.path.basename(f)] # tested, good

    # print(subfolders)
    # print(subfolders_filtered) 

    flagged_folders = []

    for s in subfolders_filtered:

        folder_name = os.path.basename(s)

        # Determine output filename based on the selected folder format
        if FOLDER_FORMAT == "BIM_ID":
            match = re.search (r'BIM\d{4}', folder_name)

            if not match:
                message = f"Skipping invalid BIM folder name: {folder_name}"
                print(message)
                flagged_folders.append(message)
                continue

            file_id = match.group() + f"_{PHASE}" # match.group() returns everything from regex 
        
        elif FOLDER_FORMAT == "FULL_NAME":
            file_id = folder_name

        elif FOLDER_FORMAT == "BIM_II": # nvm this is just full name unless you want to disregard whatever is after P#
            match = re.search(r'BIM \d{4}_P\d{1}', folder_name)

            if not match:
                message = f"Skipping invalid BIM folder name: {folder_name}"
                print(message)
                flagged_folders.append(message)
                continue
            
            file_id = match.group()

        else:
            raise ValueError(f"Unknown FOLDER_FORMAT: {FOLDER_FORMAT}")


        print(f"\nProcessing folder: {os.path.basename(s)}")

        # 2. Create HxB subfolder (if it doesn't exist already)
        output_folder = os.path.join(s, "HxB")

        # 3. Find EDF and REC files in the BIM folder
        input_files = [f for f in os.scandir(s) if f.is_file() and f.name.lower().endswith((".edf", ".rec"))]

        # Should only be 1 EDF file per folder. Otherwise, flag and skip
        if len(input_files) == 0:
            message = f"{os.path.basename(s)}: no EDF/REC files found. Folder skipped"
            flagged_folders.append(message)
            continue
        
        elif len(input_files) > 1:
            message = (f"WARNING: {os.path.basename(s)}: expected 1 EDF file, found {len(input_files)}. Folder skipped")
            flagged_folders.append(message)
            continue

        os.makedirs(output_folder, exist_ok=True)

        original_path = input_files[0]
        original_name = os.path.basename(original_path)
        stem, extension = os.path.splitext(original_name)

        # 4. Copy EDF file into HxB
        copied_name = f"{file_id} Copy{extension}" 
        copied_path = os.path.join(output_folder, copied_name)

        if not os.path.exists(copied_path):
            try:
                shutil.copy2(original_path, copied_path) # copy2 tries to preserve metadata while copy does not

            except Exception as e:
                message = (f"WARNING: {os.path.basename(s)}: failed to copy. >> {original_name}: {e}")
                flagged_folders.append(message)
                continue
        else:
            print(f"\tUsing existing copy: {copied_name}")

        # 5. Extract channels from the COPY
        try:
            # Read available channel labels
            file_header = highlevel.read_edf_header(copied_path)
            available_channels = file_header["channels"]

                        # Match requested channel names, ignoring capitalization
            channel_lookup = {
                label.strip().lower(): label
                for label in available_channels
            }

            selected_channels = []

            for channel in CHANNELS:
                matched = channel_lookup.get(channel.lower())

                if matched is None:
                    raise ValueError(
                        f"Channel '{channel}' not found. Available channels: {available_channels}")

                selected_channels.append(matched)

            # Read only the requested channels from the COPY
            signals, signal_headers, header = highlevel.read_edf(copied_path, ch_names=selected_channels)

            # 6. Save filtered EDF in HxB
            output_edf = os.path.join(output_folder, f"{file_id}_filtered.edf")
            
            if os.path.exists(output_edf):
                print(f"Filtered EDF already exists; skipping: {output_edf}")
            else:
                highlevel.write_edf(output_edf, signals, signal_headers, header)

            print(f"Saved filtered EDF: {os.path.basename(output_edf)}")

            # Ensure channels have compatible sampling frequencies
                # 1Hz for newer kits, 3Hz for older kits - SpO2/Oximeter and Pulse
            sampling_frequencies = [h["sample_frequency"] for h in signal_headers]

            if len(set(sampling_frequencies)) != 1:
                raise ValueError(
                    "Selected channels have different sampling frequencies"
                )

            # Create time column in seconds and combine with signal data
            sampling_frequency = sampling_frequencies[0]
            num_samples = len(signals[0])
            time = np.arange(num_samples) / sampling_frequency
            data = np.column_stack([time] + list(signals))

            # Create column headers
            header = ["Time (s)"] + selected_channels

            # Save final CSV file in HxB
            output_csv = os.path.join(output_folder, f"{file_id}_Sagatech.csv")
            if os.path.exists(output_csv):
                print(f"CSV already exists; skipping: {output_csv}")
            else:
                np.savetxt(output_csv,data,fmt=["%.9f"] + ["%.1f"] * len(selected_channels),delimiter=",",header=",".join(header),comments="")
            
            print(f"\tSaved as CSV: {os.path.basename(s)}")

        except Exception as e:
            message = (f"{os.path.basename(s)}: failed to process as .csv >> {copied_name}: {e}")
            flagged_folders.append(message)
            continue


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


#sort_edf("/mnt/med_mplab/BIM Study/Sub Studies/Sleep/PSG/BIM I/BIM_I__PSG_Files (original)/")
# sort_edf("/home/emilygv/Desktop/TESTING_EDF")
sort_edf("/mnt/med_mplab/BIM II Study/4. BIM II Sub-Studies/1. Sleep/BIM II Sleep Night Files")