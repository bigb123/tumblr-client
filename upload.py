#!/usr/bin/env python3

'''
Script to upload videos to tumblr

It is intended to run in a loop as a daemon. According to Tumblr rules (22.02.2017)
you can upload max 5 min of movies a day.
When the limit will be reached the daemon will wait 24 hours to upload new files

File can have max 100MB. If has more the resolution will be reduced.

Caption will be read from <video_name>.txt

Dependencies:
- avconv (libav debian package)
- hachoir3 (pip3 install hachoir3)
- py3tumblr (pip3 install Py3Tumblr)
'''

import pytumblr
import subprocess
from os import rename, remove, path, makedirs, walk, listdir
from time import sleep
from datetime import timedelta
import math
from argparse import ArgumentParser
import logging

from hachoir.parser import createParser
from hachoir.metadata import extractMetadata


def read_caption(file_name_path):
    caption_file_path = '{fn}.txt'.format(fn=file_name_path)
    while True:
        try:
            with open(caption_file_path) as caption_file:
                caption_text = caption_file.read()
                logging.debug('Caption file contains:\n{0}'.format(caption_text))
                return caption_text, caption_file_path
        except Exception:
            logging.debug('Cannot open file with caption: {0}. Will try again for one minute.\n{1}'.format(
                caption_file_path, Exception
                )
            )
            sleep(60)


def move_video_to_sent_folder(file_path):
    file_dirname = path.dirname(file_path)
    sent_dir = '{0}/sent/'.format(file_dirname)
    if not path.exists(sent_dir):
        try:
            makedirs(sent_dir)
        except Exception:
            logging.debug('Exception occured during directory creation:\n{0}'.format(Exception))
            exit(1)

    logging.debug('File will be moved to {0}'.format(sent_dir))

    try:
        rename(file_path, '{0}/{1}'.format(sent_dir, path.basename(file_path)))
    except OSError:
        logging.debug('Exception occured during file move:\n{0}'.format(OSError))
        exit(1)


def too_big(file_path, file_name_path, file_ext, metadata, exceed_factor):
    new_file_path = file_name_path + '_smaller' + file_ext
    convert_params = ['avconv',
                      '-loglevel', 'quiet',
                      '-i', file_path,
                      '-s', '{width}x{height}'.format(width=int(metadata.get('width')/exceed_factor),
                                                      height=int(metadata.get('height')/exceed_factor)),
                      new_file_path]

    logging.debug('File will be converted with:\n{0}'.format(convert_params))

    try:
        out = subprocess.run(convert_params, check=True)
    except subprocess.CalledProcessError as Error:
        logging.debug('Error during file conversion: {0}'.format(Error))
    # if err != 0:
    #     logging.debug('Error {0}, avconv output:\n{1}'.format(err, out))
    #     exit(1)

    # Moving too big video to sent folder
    move_video_to_sent_folder(file_path)
    return new_file_path


def upload(file_path, username, caption, consumer_key, consumer_secret, oauth_token, oauth_secret):
    client = pytumblr.TumblrRestClient(
        consumer_key,
        consumer_secret,
        oauth_token,
        oauth_secret
    )

    upload_output = client.create_video(username, caption=caption, data=file_path)
    logging.debug("Tumbler upload message:\n{0}".format(upload_output))


def main():
    argument_parser = ArgumentParser()
    argument_parser.add_argument('-d', '--debug', action='store_true',
                                 help='Turn on debug mode - will log all events to console')
    argument_parser.add_argument('-p', '--path', required=True, action='store',
                                 help='Path to directory where the files to upload are')
    argument_parser.add_argument('--username', required=True, action='store',
                                 help='User name/nick of the account')
    argument_parser.add_argument('--consumer-key', required=True, action='store',
                                 help='Consumer key')
    argument_parser.add_argument('--consumer-secret', required=True, action='store',
                                 help='Consumer secret')
    argument_parser.add_argument('--oauth-token', required=True, action='store',
                                 help='OAuth token')
    argument_parser.add_argument('--oauth-secret', required=True, action='store',
                                 help='OAuth secret')

    args = argument_parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("Debug mode turned on")

    daily_upload_time = timedelta(milliseconds=0)

    # INFINITY LOOP START
    while True:
        # list all files in folder
        dirpath = args.path
        filenames = [f for f in listdir(dirpath) if path.isfile(path.join(dirpath, f))]
        for filename in filenames:
            file_path = path.join(dirpath, filename)
            file_name_path, file_ext = path.splitext(file_path)
            if file_ext != '.mp4':
                continue
            logging.debug('File path: {0}'.format(file_path))


            # File can't be bigger than 100MB
            # if so, video will be compressed (later)
            # but now check how many times bigger it is
            file_size = path.getsize(file_path)
            logging.debug('File size: {0}'.format(file_size))

            exceed_factor = file_size/104857600

            parser = createParser(file_path)
            if not parser:
                print('Unable to create parser, check if file exist')
                exit(1)

            metadata = extractMetadata(parser)
            if not metadata:
                print('Unable to extract metadata')
                exit(1)

            if exceed_factor >= 1:
                exceed_factor = math.ceil(exceed_factor) # need to round it up because it will be the
                                                         # resolution denominator
                logging.debug('File is too big')
                file_path = too_big(file_path, file_name_path, file_ext, metadata, exceed_factor)

            file_length = metadata.get('duration')
            logging.debug('File length: {0}'.format(file_length))
            logging.debug('Already uploaded time: {0}'.format(daily_upload_time))

            daily_upload_time += file_length
            logging.debug('Total time after upload: {0}'.format(daily_upload_time))

            if daily_upload_time >= timedelta(minutes=5):
                logging.debug('Cannot upload more today, will wait 24 hours')
                sleep(86400)    # sleep for 24 hours
                daily_upload_time = timedelta(milliseconds=0)

            # read caption from file
            caption_text, caption_file_path = read_caption(file_name_path)

            upload(file_path, args.username, caption_text, args.consumer_key, args.consumer_secret, args.oauth_token,
                   args.oauth_secret)

            # after upload remove file with caption
            try:
                remove(caption_file_path)
            except Exception:
                logging.debug('File not removed\n{0}'.format(Exception))

            move_video_to_sent_folder(file_path)

        # Wait 10 mins before rerun the directory scanning
        logging.debug('Waiting for new files')
        sleep(600)


if __name__ == '__main__':
    main()
