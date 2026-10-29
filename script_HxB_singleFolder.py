"""
Created on Wed Oct 28 11:06 2026

@author: Emily Garcia-Volk
"""

from pyedflib import highlevel
import os
import shutil
import numpy as np
import pandas as pd
import re

# Replace with channels for applicable version of the sleep kits
# CHANNELS = ["SpO2", "Pulse"] # Embletta / Prodigy sleep kit
CHANNELS = ["Oximeter", "Pulse"] # Cerebra

# No naming convention, since this is one-by-one can manually edit folder names once its run
# This should be run after fixing whatever issues were flag for invidual folders after runnign script_batchSortEDF.py

folder_to_sort = ""

def sort_edf_singleFolder(folder_to_sort):
    if not os.path.exists(folder_to_sort):
        print("Parent folder does not exist")
        return

    folder_name = os.path.basename(folder_to_sort)

    print(f"\nProcessing folder: {folder_name}")

    # 2. Create HxB subfolder (if it doesn't exist already)
    output_folder = os.path.join(folder_to_sort, "HxB")

    # 3. Find EDF and REC files in the BIM folder
    input_files = [f for f in os.scandir(folder_to_sort) if f.is_file() and f.name.lower().endswith((".edf", ".rec"))]

        # Should only be 1 EDF file per folder. Otherwise, flag and skip
    if len(input_files) == 0:
        print("\tNo EDF/REC directly in BIM folder; checking subfolders...")

        for item in os.scandir(folder_to_sort):
            if item.is_dir() and item.name != "HxB":
                for subitem in os.scandir(item.path):
                    if (subitem.is_file() and subitem.name.lower().endswith((".edf", ".rec"))):
                        input_files.append(subitem.path)
    
    flagged_folders = []

    if len(input_files) == 0:
        message = f"{folder_name}: no EDF/REC files found in BIM folder or a subfolder. Folder skipped"
        flagged_folders.append(message)
    
    elif len(input_files) > 1:
        message = (f"WARNING: {folder_name}: expected 1 EDF file, found {len(input_files)}. Folder skipped")
        flagged_folders.append(message)

    os.makedirs(output_folder, exist_ok=True)

    original_path = input_files[0]

    match = re.search(r'BIM\d{4} - P\d{1}', folder_name)
    file_id = match.group()
    
    original_name = os.path.basename(original_path)
    stem, extension = os.path.splitext(original_name)

    # 4. Copy EDF file into HxB
    copied_name = f"{file_id} Copy{extension}" 
    copied_path = os.path.join(output_folder, copied_name)

    if not os.path.exists(copied_path):
        try:
            shutil.copy2(original_path, copied_path) # copy2 tries to preserve metadata while copy does not

        except Exception as e:
            message = (f"WARNING: {folder_name}: failed to copy. >> {original_name}: {e}")
            flagged_folders.append(message)
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
            print(f"\tFiltered EDF already exists; skipping: {output_edf}")
        else:
            highlevel.write_edf(output_edf, signals, signal_headers, header)
            print(f"\tSaved filtered EDF: {os.path.basename(output_edf)}")

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
            print(f"\tCSV already exists, skipping")
        else:
            np.savetxt(output_csv,data,fmt=["%.9f"] + ["%.1f"] * len(selected_channels),delimiter=",",header=",".join(header),comments="")
            print(f"\tSaved as CSV: {folder_name}")

    except Exception as e:
        message = (f"{folder_name}: failed to process channels >> {copied_name} \n\t {e}")
        flagged_folders.append(message)

    if flagged_folders:
        for message in flagged_folders:
            print(f"  - {message}")
    else:
        print("Folder processed without errors.")

sort_edf_singleFolder(folder_to_sort)

