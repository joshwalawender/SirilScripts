from pathlib import Path
import configparser
import sys
import shutil
import json
import re
import argparse
import numpy as np

# Siril commands: https://siril.readthedocs.io/en/stable/Commands.html
# Siril python: https://siril.readthedocs.io/en/stable/Python-API.html

try:
    import sirilpy
    from sirilpy import LogColor
    siril = sirilpy.SirilInterface()
    siril.connect()
    siril.log(f"-----------------------------------------------")
    siril.log(f"Running {Path(__file__).name}")
    siril.log(f"-----------------------------------------------")
    siril.log(f"Connected to Siril", LogColor.GREEN)
except ModuleNotFoundError:
    print("Could not import sirilpy")
    sys.exit(1)
except siril.SirilConnectionError:
    print("Failed to connect to Siril")
    sys.exit(1)


##-------------------------------------------------------------------------
## find_stacks
##-------------------------------------------------------------------------
def find_stacks(p, min_stack_count=20):
    p = Path(p)
    if not p.exists():
        siril.log(f'Could not find path {p}', LogColor.RED)
        return
    raw_path = p / 'Raw'
    images_path = p / 'Images'
    stacks = {}
    for json_file in images_path.glob('Stack_*.json'):
        pattern = json_file.name.split('.')[0][6:]
        with open(json_file, 'r') as jf:
            metadata = json.loads(jf.read())
        stack_count = metadata.get('Camera Info').get('Stack Count')
        exptime = float(metadata.get('Camera Info').get('Exposure (seconds)'))
        total_exptime = exptime*stack_count
        if stack_count > min_stack_count:
            stacks[pattern] = {'exptime': exptime,
                               'stack_count': stack_count,
                               'total_exptime': total_exptime}
    return stacks



##-------------------------------------------------------------------------
## find_files
##-------------------------------------------------------------------------
def find_files(p, pattern):
    raw_path = p / 'Raw'
    images_path = p / 'Images'
    with open(images_path / f'Stack_{pattern}.json', 'r') as jf:
        metadata = json.loads(jf.read())
    stack_count = metadata.get('Camera Info').get('Stack Count')
    exptime = float(metadata.get('Camera Info').get('Exposure (seconds)'))
    gain = metadata.get('Camera Info').get('Gain Setting')
    raw_files = [f for f in raw_path.glob(f'exp_{pattern}*.fit')]
    total_exptime = exptime*len(raw_files)
    if len(raw_files) < stack_count:
        siril.log(f'--> Found only {len(raw_files)} raw files. Stack count is {stack_count}', LogColor.RED)

    nraw = len(raw_files)
    siril.log(f'  Found {exptime:.0f}s x {nraw} raw files = {total_exptime/60:.1f} min', LogColor.GREEN)

    framenos = []
    exptimes = []
    temperatures = []
    for raw_file in raw_files:
        patt = 'exp_'+pattern+'_([0-9]{4})_([0-9]{2})sec_([-+]?[0-9]+)C.fit'
        ismatch = re.match(patt, raw_file.name)
        if ismatch:
            framenos.append(int(ismatch.group(1)))
            exptimes.append(int(ismatch.group(2)))
            temperatures.append(int(ismatch.group(3)))

    # Temperature
    bins = np.arange(min(temperatures)-0.5, max(temperatures)+1.5, 1)
    temp_hist = np.histogram(temperatures, bins=bins)
    peak_index = np.argmax(temp_hist[0])
    temperature = int(np.mean(temp_hist[1][peak_index:peak_index+2]))
    mean_frac = max(temp_hist[0])/len(temperatures)
    std_temp = np.std(temperatures)
    siril.log(f"  Typical Temperature = {temperature:d} C", LogColor.GREEN)
    if mean_frac < 0.99:
        siril.log(f"  Fraction at Temperature = {mean_frac:.0%}", LogColor.GREEN)
        deltas = abs(np.array(temperatures) - temperature)
        w = deltas > 0.9
        siril.log(f"  Outlier Temps:", LogColor.RED)
        for temp_count in sorted(temp_hist[0])[:-1]:
            wtcs = np.where(temp_count == temp_hist[0])[0]
            for wtc in wtcs:
                tctemp = int(np.mean(temp_hist[1][wtc:wtc+2]))
                siril.log(f"--> {temp_count}/{nraw} files at {tctemp:d} C", LogColor.RED)
#         siril.log(np.array(temperatures)[w])
#     siril.log(f"  Std Dev of Temperatures = {std_temp:.1f} C")

    # ExpTime
    bins = np.arange(min(exptimes)-0.5, max(exptimes)+1.5, 1)
    exptime_hist = np.histogram(exptimes, bins=bins)
    peak_index = np.argmax(exptime_hist[0])
    exptime = int(np.mean(exptime_hist[1][peak_index:peak_index+2]))
    mean_frac = max(exptime_hist[0])/len(exptimes)
    std_exptime = np.std(exptimes)
#     siril.log(f"  Typical ExpTime = {exptime:d} s")
    if mean_frac < 0.99:
        siril.log(f"  Fraction at Nominal ExpTime = {mean_frac:.0%}", LogColor.GREEN)
        deltas = abs(np.array(exptimes) - exptime)
        w = deltas > 0.9
        siril.log(f"  Outlier ExpTimes:", LogColor.RED)
        for exptime_count in sorted(exptime_hist[0])[:-1]:
            wecs = np.where(exptime_count == exptime_hist[0])[0]
            for wec in wecs:
                tcexp = int(np.mean(exptime_hist[1][wec:wec+2]))
                siril.log(f"--> {exptime_count}/{nraw} files at {tcexp:d} sec", LogColor.RED)

        siril.log(np.array(exptimes)[w])
#     siril.log(f"  Std Dev of ExpTimes = {std_exptime:.1f} C")

    # Dark File
    if temperature > -0.1 and temperature < 0.1:
        dark_file_name = f'StackDark_00C_{exptime:02.0f}_{gain}.fit'
    else:
        dark_file_name = f'StackDark_{temperature:.0f}C_{exptime:02.0f}_{gain}.fit'
    dark_file = p / 'DarkLibrary' / dark_file_name
    if dark_file.exists():
        siril.log(f"  Dark File: {dark_file}", LogColor.GREEN)
    else:
        siril.log(f"  Dark File: {dark_file} Does not exist!", LogColor.RED)
        dark_file = None
    

    return raw_files, dark_file, framenos, temperature, exptime


##-------------------------------------------------------------------------
## main
##-------------------------------------------------------------------------
config = configparser.ConfigParser()
configfile = Path(__file__).parent / 'processing.ini'
if not configfile.exists():
    siril.log(f'Config File {configfile} does not exist!', LogColor.RED)
    sys.exit(1)
config.read(configfile)
locations = config.sections()
# for location in locations:
#     if not Path(location).absolute().exists():
#         locations.pop(locations.index(location))
#         siril.log(f'Location {location} does not exist')

# get current directory
location = siril.get_siril_wd()
if location in locations:
    siril.log(f'Found config for {location}', LogColor.GREEN)
else:
    siril.log(f'No configuration for {location}', LogColor.RED)

## --> Create mode where location is one of the object or pattern directories

raw_dir = Path(location) / 'Raw'
stacks = find_stacks(location)

for pattern in stacks:
    try:
        stacks[pattern]['object'] = config[location][pattern]
    except KeyError:
        stacks[pattern]['object'] = pattern

    objectname = stacks[pattern].get('object', pattern)
    siril.log(f"Processing files {pattern}*: object={objectname}")
    # Crate object directory
    object_dir = Path(location) / objectname
    if object_dir.exists() is False:
        object_dir.mkdir(mode=0o755)

    raw_files, dark_file, framenos, temperature, exptime = find_files(Path(location), pattern)

    # cd to raw_dir
    args = ["cd", str(raw_dir)]
    siril.log("Running: "+" ".join(args), LogColor.GREEN)
    siril.cmd(*args)

    # copy raw files to object_dir
    siril.log(f"Linking {len(raw_files)} raw files in to {object_dir}")
    for file in raw_files:
        new_file_name = '_'.join(file.name.split('_')[:4]) + file.suffix
        new_file = object_dir / new_file_name
        if not new_file.exists():
            new_file.symlink_to(file)

    # cd to object_dir
    args = ["cd", str(object_dir)]
    siril.log("Running: "+" ".join(args), LogColor.GREEN)
    siril.cmd(*args)

    # link/convert
    outputfile = Path(f"{objectname}.fit")
    if outputfile.exists():
        siril.log(f"{outputfile} exists. Skipping convert step.", LogColor.GREEN)
    else:
        args = ["convert", objectname, '-fitseq', f"-out={str(object_dir)}"]
        siril.log("Running: "+" ".join(args), LogColor.GREEN)
        siril.cmd(*args)

    # calibrate
    outputfile = Path(f"pp_{objectname}.fit")
    if outputfile.exists():
        siril.log(f"{outputfile} exists. Skipping calibrate step.", LogColor.GREEN)
    else:
        args = ["calibrate", objectname, '-fitseq', '-debayer',
                f"-dark={dark_file}",
                "-cfa -equalize_cfa"]
        siril.log("Running: "+" ".join(args), LogColor.GREEN)
        siril.cmd(*args)

    # register
    outputfile = Path(f"r_pp_{objectname}.fit")
    if outputfile.exists():
        siril.log(f"{outputfile} exists. Skipping register step.", LogColor.GREEN)
    else:
        args = ["register", f"pp_{objectname}"]
        siril.log("Running: "+" ".join(args), LogColor.GREEN)
        siril.cmd(*args)

    # stack
    outputfile = Path(f"r_pp_{objectname}_stacked.fit")
    if outputfile.exists():
        siril.log(f"{outputfile} exists. Skipping stacking step.", LogColor.GREEN)
    else:
        args = ["stack", f"r_pp_{objectname}", 'rej', '3 3', '-norm=addscale', '-rgb_equal']
        siril.log("Running: "+" ".join(args), LogColor.GREEN)
        siril.cmd(*args)

siril.log("SmartEye Processing Complete", LogColor.GREEN)
