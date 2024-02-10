"""
Utility functions for parsing tracklist strings, getting MP3 metadata, processing MP3 files, and adding ID3 tags.
Used to split an MP3 file into multiple tracks based on a tracklist string.
"""
import argparse
import re
import subprocess
from typing import Optional
from mutagen.id3 import ID3
from mutagen.id3._frames import TIT2, TRK
from mutagen.mp3 import MP3
from datetime import datetime, timedelta

STARTPATTERN = r"((?:\d{1,2}:)?\d{1,2}:\d{2})(?:\s*)(.*)"


class BADFORMAT(Exception):
    pass


def get_mp3_duration(file_path):
    audio = MP3(file_path)
    return timedelta(seconds=int(audio.info.length))


def parse_tracklist(tracklist_str, pattern=STARTPATTERN):
    matches = []
    try:
        # pattern = r"((?:\d{1,2}:)?\d{1,2}:\d{2})(?:\s*)(.*)"
        matches = re.finditer(pattern, tracklist_str, re.MULTILINE)
    except:
        raise BADFORMAT("Tracklist format / regex is not correct.")
    start_times = []
    track_names = []
    # rows = []

    for match in matches:
        t = match.group(1)
        if t.count(":") == 1:
            t = "00:" + t
        tn = match.group(2).strip()
        start_times.append(t)
        track_names.append(tn)
        # rows.append(t,tn)

    return start_times, track_names


def get_duration(start, end):
    start_time = (
        datetime.strptime(start, "%H:%M:%S")
        if ":" in start
        else datetime.strptime(start, "%M:%S")
    )
    end_time = (
        datetime.strptime(end, "%H:%M:%S")
        if ":" in end
        else datetime.strptime(end, "%M:%S")
    )
    duration = end_time - start_time
    return str(duration)


def argparsing():
    """Parse the arguments

    Returns:
        tuple: (skip_conf, tracklist_in, input_file)"""
    parser = argparse.ArgumentParser(
        description="Cut MP3 file into parts based on tracklist."
    )
    parser.add_argument("-i", "--input", help="Input MP3 file", required=False)
    parser.add_argument("-I", "--input-tracklist", help="Input tracklist file")
    parser.add_argument(
        "-t", "--tracklist", help="Tracklist as a string", required=False
    )
    parser.add_argument(
        "-s", "--skip", help="Skip the confirmation step", action="store_true"
    )
    parser.add_argument(
        "-o", "--output-dir", help="Output directory", default="output", required=False
    )

    # add help
    parser.usage = "cut.py [-h] [-i INPUT] [-I INPUT_TRACKLIST] [-t TRACKLIST] [-s] [-o OUTPUT_DIR]"

    parser.description = "Cut MP3 file into parts based on tracklist."
    parser.epilog = (
        'Example: cut.py -i input.mp3 -t "00:00:00 Track 1\n00:01:00 Track 2"'
    )
    parser.formatter_class = argparse.RawDescriptionHelpFormatter

    args = parser.parse_args()

    if not args.input:
        args.input = input("Please provide the input MP3 file: ")

    if args.input_tracklist:
        with open(args.input_tracklist, "r") as f:
            args.tracklist = f.read()

    if not args.tracklist:
        args.tracklist = input("Please provide the tracklist as a string: ")
    return (args.skip, args.tracklist, args.input)


def process_file(input_file, track_name, start, end=None):
    """Process the input file and create the output file

    Args:
        input_file (str): Input file name
        track_name (str): Track name
        start (str): Start time
        end (str, optional): End time. Defaults to None.

    Returns:
        None"""
    args = ["ffmpeg", "-i", input_file, "-ss", start, "-vn", "-acodec", "copy"]
    if end:
        args.extend(["-to", end])
    args.append(track_name)
    subprocess.run(args)


def format_filename(
    s: str, track_number: Optional[int] = None, number_of_tracks: Optional[int] = None
):
    """Format the filename

    Args:
        s (str): Filename
        track_number (int, optional): Track number. Defaults to None.
        number_of_tracks (int, optional): Number of tracks. Defaults to None.

    Returns:
        str: Formatted filename"""
    s = s.strip().replace(" ", "_")
    s += ".mp3"
    if track_number:
        if number_of_tracks:
            extra_zeros = len(str(number_of_tracks))
        else:
            extra_zeros = 2
        s = f"{track_number:0{extra_zeros}d}-{s}"
    return s.replace("--", "-")


def process_file_list(
    input_file: str,
    start_times: list,
    end_times: list,
    track_names: list,
    output_dir: str,
):
    """Process the input file and create the output files

    Args:
        input_file (str): Input file name
        start_times (list): List of start times
        end_times (list): List of end times
        track_names (list): List of track names
        output_dir (str): Output directory

    Returns:
        None"""

    os.makedirs(output_dir, exist_ok=True)

    for i, (start, end, track_name) in enumerate(
        zip(start_times, end_times, track_names)
    ):
        output_file = format_filename(track_name, i + 1, len(track_names))
        output_file = os.path.join(output_dir, output_file)

        if end == "EOF":
            end = None

        print(f"Processing {output_file} : {start}-{end}")
        process_file(input_file, output_file, start, end)
        tag(output_file, track_name, i + 1)


# TODO track_number does not work
def tag(output_file: str, track_name: str, track_number: Optional[int] = None):
    """Add ID3 tags to the output file

    Args:
        output_file (str): Output file name
        track_name (str): Track name
        track_number (int, optional): Track number. Defaults to None.

    Returns:
        None"""
    audio = MP3(output_file, ID3=ID3)
    if audio and audio.tags:
        audio.tags.add(TIT2(encoding=3, text=track_name))
        audio.save()
        try:
            if track_number:
                audio.tags.add(TRK(encoding=3, text=track_number))
        except:
            pass


def main():
    """Main function"""

    (skip_conf, tracklist_in, input_file) = argparsing()
    start_times, track_names = parse_tracklist(tracklist_in)

    # Calculate the end times
    end_times = start_times[1:] + ["EOF"]
    # mp3_duration = get_mp3_duration(input_file)

    if not skip_conf:
        print("\nPreview of files to be created:")
        for i, (start, end, track_name) in enumerate(
            zip(start_times, end_times[:-1], track_names)
        ):
            duration = get_duration(start, end)
            output_file = f"{i+1:02d}-{track_name.replace(' ', '_')}.mp3"
            print(f"{i+1:02d}: {start}-{end}: {output_file} ({duration})")

        proceed = input("\nProceed with cutting the MP3 file? [Y/n] ").lower()
        if proceed != "y":
            print("Operation aborted.")
            exit()

    process_file_list(input_file, start_times, end_times, track_names, "./")
    print("Done!")
