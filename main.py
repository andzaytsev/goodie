#!/usr/bin/env python

# This script invokes the script that uploads the document every
# 0.5sec (but only if the file is changed).

import argparse
import filecmp
import shutil
import threading
import os

import hack

from lockfile import FileLock

# Command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--file-name", type=str, default="document.txt")
parser.add_argument("--title", type=str)
parser.add_argument("--single", action='store_true', help='run only once')
parser.add_argument("--id", type=int, help='run id', default=0)
parser.add_argument("--clean", action='store_true', help='clean meta files', default=False)
parser.add_argument("--compile", type=int, help='compile sources and include report', default=0)
parser.add_argument("--add-line-numbers", type=int, help='include line numbers', default=0)
parser.add_argument("--check-code-quality", type=int, help='check code quality using PMD', default=0)
args = parser.parse_args()

# Name of the file to keep use for comparison
BAK_FILE = "bak.document.bak"
UPLOAD_FILE = "upload"
ID_LOCK_FILE = "id.lock"
META_FILE = "meta.json"

# Extensions
EXTENSION_TO_LANGUAGE = {"py" : "python",
                         "java": "java",
                         "cc": "c++",
                         "cpp": "c++"}


if __name__ == "__main__":
    if args.clean:
        try:
            os.remove(META_FILE)
        except OSError:
            pass

    drive_service = hack.get_drive_service()
    if args.title:
        title, file_obj = hack.get_file_by_title(str(args.title), drive_service)
        file_name = title + '.txt'
        temp = open(file_name, 'w')
        temp.write('Edit this file')
        temp.close()
    else:
        file_name = args.file_name

        if '.' not in file_name:
            language = "python"
        else:
            extension = file_name.split('.')[-1]
            language = EXTENSION_TO_LANGUAGE.get(extension, "python")

        file_obj = hack.insert(file_name, language, drive_service)

    print('Run ' + str(args.id) + ' editing: ' + file_name)

    # Cleaning
    open(BAK_FILE, 'a').close()
    try:
        os.remove(ID_LOCK_FILE)
    except OSError:
        pass
    with open(ID_LOCK_FILE, 'w') as f:
        f.write("-1")
    
    #shutil.copy2(file_name, BAK_FILE)
    while True:
        with FileLock(ID_LOCK_FILE):
            # Check if id is greater than existing
            print("D: Reading current id from file")
            with open(ID_LOCK_FILE, 'r') as f:
                max_id = int(f.readline())
                if args.id < max_id:
                    break
            print("D: Updating id in file " + file_name)
            with open(ID_LOCK_FILE, 'w') as f:
                f.write(str(args.id))

            if not filecmp.cmp(file_name, BAK_FILE):
                shutil.copy2(file_name, BAK_FILE)
                shutil.copy2(BAK_FILE, UPLOAD_FILE)

                # Add line numbers
                if args.add_line_numbers:
                    hack.add_line_numbers(UPLOAD_FILE)

                # Compile
                if args.compile and language == "java":
                   result=hack.compile(file_name)
                   with open(UPLOAD_FILE, "a") as myfile:
                        myfile.write('\n\nCompiling:\n\n' + result)

                # Convert to HTML
                hack.convert_to_html(UPLOAD_FILE, language)

                # Checking code quality with PMD
                if args.check_code_quality:
                    hack.invoke_pmd(file_name, UPLOAD_FILE + ".html", language)

                # Upload/update on Google Docs
                hack.update(file_obj, UPLOAD_FILE, language, drive_service)
            if args.single:
                break
            threading.Event().wait(0.5)

    print('D: Finished ' + str(args.id))
