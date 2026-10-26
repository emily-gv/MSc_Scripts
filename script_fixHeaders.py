"""
Created on Mon Oct 25 11:55 2026

@author: Emily Garcia-Volk
"""

from pathlib import Path
import subprocess

parent_folder = Path("/home/emilygv/Desktop/TESTING_EDF/TESTING_BROKEN_HEADER")
repair_script = Path("/home/emilygv/Documents/MSc_Scripts/edf-hdr-repair.sh")

DRY_RUN = False # Start with true to preview files and NOT EDIT

"""
This iterates through each BIM folder within a parent folder, and fixes the headers 
for the EDF file COPY within the HxB folder (making too this complex? maybe. 
willing to fix 200 headers by hand? no).

Using the reapair script from: https://www.teuniz.net/edf-hdr-repair/
(put in the directory that also houses this script)
"""
def repair_edf_copies(parent_folder, repair_script):
    if not parent_folder.is_dir():
        raise FileNotFoundError(f"Parent folder does not exist: {parent_folder}")

    if not repair_script.is_file():
        raise FileNotFoundError(f"Repair script not found: {repair_script}")

    # Find EDF copies inside HxB folders
    edf_files = sorted(
        f for hxb in parent_folder.rglob("HxB")
        if hxb.is_dir() 
        for f in hxb.iterdir()
        if f.is_file() and f.name.lower().endswith("copy.edf")
    )

    print(f"Found {len(edf_files)} EDF files.")

    successes = []
    failures = []

    for edf in edf_files:
        print(f"\nProcessing: {edf}")

        if DRY_RUN:
            print("DRY RUN: no changes made")
            continue

        try:
            # usage eg: subprocess.run(["ls", "-l"])
            # https://docs.python.org/3/library/subprocess.html
            result = subprocess.run(
                ["bash", str(repair_script), str(edf)], # bash <script>.sh /path/to/edf
                cwd=edf.parent, # working directory is HxB folder for each EDF
                capture_output=True, # captures stdout and stderr
                text=True, # stdout and stderr as string and not binary
                check=True # raises CalledProcessError if exits non-zero
            )

            print("Repair command completed successfully")
            if result.stdout:
                print(result.stdout)

            successes.append(str(edf))


        except subprocess.CalledProcessError as e:
            print(f"Repair failed (exit code {e.returncode})")
            if e.stdout:
                print(e.stdout)
            if e.stderr:
                print(e.stderr)
            failures.append(str(edf))

        except OSError as e:
            print(f"Could not run repair script: {e}")
            failures.append(str(edf))

    print("\n" + "=" * 50)
    print(f"Files found: {len(edf_files)}")

    if DRY_RUN:
        print("Dry run only: no files were repaired")
    else:
        print(f"Successful commands: {len(successes)}")
        print(f"Failed commands: {len(failures)}")

    if failures:
        print("\nFiles requiring review:")
        for f in failures:
            print(f"  {f}")

if __name__ == "__main__":
    repair_edf_copies(parent_folder, repair_script)
