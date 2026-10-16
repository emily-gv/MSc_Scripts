"""
Created on Wed Oct 15 14:38 2026

@author: Emily Garcia-Volk
"""

# https://github.com/holgern/pyedflib
# https://pyedflib.readthedocs.io/en/latest/ref/highlevel.html

# conda install -c conda-forge pyedflib

# TODO - add check for info inside of HxB instead of folder existing

from pyedflib import highlevel
import os
import shutil
import numpy as np
import pandas as pd

# Replace with channels for applicable version of the sleep kits
CHANNELS = ["SpO2", "Pulse"]
# CHANNELS = ["Oximeter", "Pulse"]

def sort_edf(parent_folder_to_sort):

    parent_folder = parent_folder_to_sort
    if not os.path.exists(parent_folder):
        print("Parent folder does not exist")
        return

    # 1: Iterate through all folders starting with BIM
    subfolders = [f.path for f in os.scandir(parent_folder) if f.is_dir()] # tested, good
    subfolders_filtered = [f for f in subfolders if 'BIM' in f] # tested, good

    # print(subfolders)
    # print(subfolders_filtered) 

    flagged_folders = []

    # Process each BIM folder (can generalize to non-BIM later)
    for s in subfolders_filtered:

        print(f"\nProcessing folder: {os.path.basename(s)}")

        # 2. Create HxB subfolder (if it doesn't exist already)
        output_folder = os.path.join(s, "HxB")
        if os.path.isdir(output_folder):
            message = (f"Skipping {os.path.basename(s)}: HxB folder already exists")
            flagged_folders.append(message)
            continue

        os.makedirs(output_folder, exist_ok=True)

        # 3. Find EDF and REC files in the BIM folder
        input_files = [f for f in os.scandir(s) if f.is_file() and f.name.lower().endswith((".edf", ".rec"))]
            ### FLAG ONES WITH MULTIPLE AND IGNORE

        # Should only be 1 EDF file per folder. Otherwise, flag and skip
        if len(input_files) == 0:
            message = f"{os.path.basename(s)}: no EDF/REC files found. Folder skipped"
            flagged_folders.append(message)
            continue
        
        elif len(input_files) > 1:
            message = (f"WARNING: {os.path.basename(s)}: expected 1 EDF file, found {len(input_files)}. Folder skipped")
            flagged_folders.append(message)
            continue

        original_path = input_files[0]
        original_name = os.path.basename(original_path)
        stem, extension = os.path.splitext(original_name)

        # 4. Copy EDF file into HxB
        copied_name = f"{stem} Copy{extension}" 
        copied_path = os.path.join(output_folder, copied_name)

        try:
            shutil.copy2(original_path, copied_path) # copy2 tries to preserve metadata while copy does not

        except Exception as e:
            message = (f"WARNING: {os.path.basename(s)}: failed to copy. >> {original_name}: {e}")
            flagged_folders.append(message)
            continue

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
                        f"Channel '{channel}' not found. "
                        f"Available channels: {available_channels}"
                    )

                selected_channels.append(matched)

            # Read only the requested channels from the COPY
            signals, signal_headers, header = highlevel.read_edf(copied_path, ch_names=selected_channels)

            # 6. Save filtered EDF in HxB
            output_edf = os.path.join(output_folder, f"{stem}_filtered.edf")
            highlevel.write_edf(output_edf, signals, signal_headers, header)

            print(f"Saved filtered EDF: {os.path.basename(output_edf)}")

            # 7. Save ASCII TXT in HxB
            output_txt = os.path.join(output_folder, f"{stem}_filtered_data.txt") 

            # Ensure channels have compatible sampling frequencies
                # 1Hz for newer kits, 3Hz for older kits - SpO2/Oximeter and Pulse
            sampling_frequencies = [h["sample_frequency"] for h in signal_headers]

            if len(set(sampling_frequencies)) != 1:
                raise ValueError(
                    "Selected channels have different sampling frequencies"
                )

            # Create time column in seconds
            sampling_frequency = sampling_frequencies[0]
            num_samples = len(signals[0])

            time = np.arange(num_samples) / sampling_frequency

            # Combine time and signal data
            data = np.column_stack([time] + list(signals))

            # Write comma-separated ASCII TXT
            header = ["Time (s)"] + selected_channels

            np.savetxt(
                output_txt,
                data,
                delimiter=",",
                fmt=["%.9f"] + ["%.6f"] * len(selected_channels),
                header=",".join(header),
                comments=""
            )

            print(f"\tSaved ASCII TXT: {os.path.basename(output_txt)}")
        except Exception as e:
            message = (f"{os.path.basename(s)}: failed to process as TXT >> {copied_name}: {e}")
            flagged_folders.append(message)
            ## IF CHANNEL VALUE ERROR, just quit script

        try:
            df = pd.read_csv(output_txt, header=0) # assumes seprated by commas, else add sep='\t'
            df.to_excel(os.path.join(output_folder,f"{stem}_filtered_data.xlsx"), index=False)
            print(f"\t\tSaved as XLSX: {os.path.basename(s)}")
        except Exception as e:
            message = (f"{os.path.basename(s)}: failed to process as .xlsx >> {copied_name}: {e}")
            flagged_folders.append(message)
            continue

        try:
            df = pd.read_csv(output_txt, header=0) # assumes seprated by commas, else add sep='\t'
            df.to_csv(os.path.join(output_folder, f"{os.path.basename(s)}_Sagatech.csv"),index=False)
            print(f"\t\t\tSaved as CSV: {os.path.basename(s)}")
        except Exception as e:
            message = (
                f"{os.path.basename(s)}: failed to process as .csv >> {copied_name}: {e}")

            flagged_folders.append(message)




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
