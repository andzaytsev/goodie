#!/usr/bin/env python

# This script uploads the (given) file to google drive.

import cStringIO
import httplib2
import json
import os
import pprint
import re
import subprocess

from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage

# Copy your credentials from the APIs Console
CLIENT_ID = 'CLIENT_ID_HERE'
CLIENT_SECRET = 'CLIENT_SECRET_HERE'

# Check https://developers.google.com/drive/scopes for all available scopes
OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'

# Redirect URI for installed apps
REDIRECT_URI = 'http://localhost'

# Path to the file to upload
HTML_TEMPLATE_NAME = "template.html"

# Storage and check credentials
CREDENTIALS = "_credentials"
storage = Storage(CREDENTIALS)

## Storage for file id
META = "meta.json"

# Mime type
mimeType = 'text/html'


def preprocess(fn):
    out = cStringIO.StringIO()
    with open(fn, 'r') as f:
        for line in f:
            out.write(line)
    return out.getvalue()


def make_html(fn, fmt):
    print("D: Making HTML from the template")
    code = preprocess(fn)
    html_page = subprocess.Popen(
        ('enscript', '-E%s' % fmt, '--language=html', '-o-', '--color', '--line-numbers'),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE).communicate(code)[0]
    return re.search('<PRE>.*</PRE>', html_page, re.DOTALL).group(0)


def add_line_numbers(file_name):
    inp = open(file_name, 'r')
    lines = inp.readlines()
    digits = len(str(len(lines)))
    inp.close()
    for i, line in enumerate(lines):
        lines[i] = str(i + 1).zfill(digits) + ' ' + line
    out = open(file_name, 'w')
    out.writelines(lines)
    out.close()


def convert_to_html(file_name, language):
    with open(file_name + '.html', "wt") as out_file:
        with open(HTML_TEMPLATE_NAME, "rt") as fin:
            for line in fin:
                out_file.write(line.replace('Hi Lamya', make_html(file_name, language) ))


def compile(file_name):
    print("D: compiling...")
    result=subprocess.Popen('javac ' + file_name, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = result.communicate()
    if not err:
       return "Successful Compilation"
    return err


def is_empty(file_name):
    return os.stat(file_name)[6]==0


def get_drive_service():
    print("D: Checking if storage exist and obtaining credentials")
    if not storage.get():
        # Run through the OAuth flow and retrieve credentials
        flow = OAuth2WebServerFlow(CLIENT_ID, CLIENT_SECRET, OAUTH_SCOPE, REDIRECT_URI)
        authorize_url = flow.step1_get_authorize_url()
        print 'Go to the following link in your browser: ' + authorize_url
        code = raw_input('Enter verification code: ').strip()
        credentials = flow.step2_exchange(code)

        storage.put(credentials)
    else:
        credentials = storage.get()

    # Create an httplib2.Http object and authorize it with our credentials
    print("D: Creating an http object and authorize with the credentials")
    http = httplib2.Http()
    http = credentials.authorize(http)

    drive_service = build('drive', 'v2', http=http)
    return drive_service


def insert(file_name, language, drive_service):
    try:
        with open(META) as meta_file:
            #http://stackoverflow.com/questions/2835559/parsing-values-from-a-json-file-in-python
            meta = json.load(meta_file)
            file_id = meta['fileId']
            File = drive_service.files().get(fileId=file_id).execute()
            #print(meta['fileId'])
    except IOError:
        if is_empty(file_name):
            print 'Empty file'
            return
        # Insert a file
        print("D: Inserting file for the first time " + file_name)
        convert_to_html(file_name, language)
        media_body = MediaFileUpload(file_name + ".html", mimetype=mimeType, resumable=True)
        body = {
            'title': file_name,
            'description': 'A test document',
            'mimeType': mimeType
        }
        File = drive_service.files().insert(body=body, media_body=media_body, convert=True).execute()
        #pprint.pprint(file)
        #http://stackoverflow.com/questions/12309269/write-json-data-to-file-in-python
        with open(META, "w") as meta_file:
            json.dump({'fileId': File['id']}, meta_file)

    return File


def update(file_obj, file_name, language, drive_service):

    if is_empty(file_name):
        print 'Empty file'
        return
    print("D: Uploading " + file_name)
    media_body = MediaFileUpload(file_name + '.html', mimetype=mimeType, resumable=True)
    drive_service.files().update(fileId=file_obj['id'], body=file_obj, media_body=media_body).execute()


def print_permissions(file_obj, drive_service):
    permissions = drive_service.permissions().list(fileId=file_obj['id']).execute()
    print permissions


def get_permissions_for_email(email, drive_service):
    id_resp = drive_service.permissions().getIdForEmail(email=email).execute()
    print id_resp['id']


def get_file_by_title(title, drive_service):
    param = {}
    param['q'] = 'title = \'' + title + '\' and trashed = false'
    files = drive_service.files().list(**param).execute()
    fileId = files.get('items')[0]['id']
    file_obj = drive_service.files().get(fileId = fileId).execute()
    url = file_obj['exportLinks']['text/html']
    resp, content = drive_service._http.request(url)
    local_file = open(title + '.html', 'w')
    local_file.write(content)
    local_file.close()
    return title, file_obj


def invoke_pmd(input_file, output_file, language):
    """Invokes PDM on the given input file and appends the result to the
given output file.

    """
    
    ## Ensure that the language is Java
    if language != "java":
        return

    pmd_report, stderrdata = subprocess.Popen('pmd-bin-5.0.5/bin/run.sh pmd -d ' + input_file + ' -language java -rulesets java-basic,java-design -f html', shell=True, stdout=subprocess.PIPE).communicate()
    begin_index = int(pmd_report.index('<table'))
    end_index = int(pmd_report.index('</body>'))
    pmd_report = pmd_report[begin_index:end_index]
    pmd_report = pmd_report.replace("lightgrey", "lightyellow")
    pmd_report = pmd_report.replace("<a", "<a style=\"color:black; text-decoration:none\"")

    inf = open(output_file, 'r')
    lines = inf.readlines()
    inf.close()

    for i, line in enumerate(lines):
        if "</body>" in line:
            lines[i] = line.replace("</body>", pmd_report + "</body>")

    outf = open(output_file, 'w')
    outf.writelines(lines)
    outf.close()
