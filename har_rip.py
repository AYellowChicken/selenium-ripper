import os
from os import listdir
from os.path import isfile, join, isdir
from pathlib import Path
import requests
import re
import unicodedata
import shutil
from lxml.html import fromstring

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFC', value).encode('ascii', 'ignore').decode('ascii')
    char_to_remove = "/\*^"
    for c in char_to_remove:
        value = value.replace(c, "")
    value = value.replace(".", "-")
    value = value.replace(":", "-")
    return value

def chap_exists(url):
    """
    Return slugified chap_name if not already on the server. Finishes script by signalling the chapter path otherwise. 
    """
    r = requests.get(url)
    tree = fromstring(r.content)
    title = tree.findtext('.//title')
    chap_found = title.split("(Manga) ")

    # filter it and return chap name, or exit to signal existing
    if len(chap_found) > 0:
        chap_found = chap_found[1]
        chap_found = chap_found.split(" - pattern to remove")
        chap_name = chap_found[0]

        chap_name = slugify(chap_name)

        directory = f"/home/my_user/my_folder/files/{chap_name}"
        if os.path.exists(directory) and os.path.isfile(f"{directory}.zip"):
            print(f"{directory}.zip")
            exit(0)

    else: # Else we just return ChapterX.
        chap_name = "ChapterX"

    return chap_name

def rip_har(harfile, chap_name):
    # Get pages from har
    regex_page = re.compile('(?<=\'url\': \')https://my_url_to_rip([^"\']*)/2048/[^"\']*(\.webp)[^"\']*')
    pages = [x.group() for x in re.finditer(regex_page, harfile)]
    length = len(pages)


    # Download starts
    print(f"Downloading {chap_name}")

    # Save directory
    directory = f"/home/my_user/my_folder/files/{chap_name}"
    if os.path.exists(directory) and os.path.isfile(f"{directory}.zip"):
        print(f"{directory}.zip")
        exit(0)

    if length < 5: # Something went wrong. We didn't get pages.
        os.system("rm /home/my_user/my_folder/files/hellobmp")
        exit(-1)

    os.makedirs(directory)
    print(f"Saving to {directory}")

    i = 0
    for p in pages:
        i += 1
        print(f"Page {i}/{length} ...")
        img = requests.get(p)
        with open(f"{directory}/{i}.webp", 'wb') as dest:
            dest.write(img.content)

    # Zip directory
    shutil.make_archive(directory, 'zip', directory)
    os.system("rm /home/my_user/my_folder/files/hellobmp")
    print(f"{directory}.zip")
    exit(0)

# def webp_to_jpg(directory):
#     from PIL import Image
#     onlyfiles = [join(directory, f) for f in listdir(directory) if isfile(join(directory, f))]
#     for f in onlyfiles:
#         if(f.endswith(".webp")):
#             im = Image.open(f).convert("RGB")
#             filename = f.replace("webp", "jpg")
#             im.save(filename)