#!/usr/bin/env python3

'''
Script to upload videos to tumblr

It is intended to run in a loop as a daemon. According to Tumblr rules (22.02.2017)
you can upload max 5 min of movies a day.
When the limit will be reached the daemon will wait 24 hours to upload new files

File can have max 100MB. If has more the resolution will be reduced.

Caption will be read from <video_name>.txt

Dependencies:
- avconv (libav debian package, works also on macos: brew install libav)
- hachoir3 (pip3 install hachoir3)
- py3tumblr (pip3 install Py3Tumblr)
'''

import pytumblr
import subprocess
from os import rename, remove, path, makedirs, listdir
from time import sleep
from datetime import timedelta
import math
from argparse import ArgumentParser
import logging
from requests.exceptions import ConnectionError

from hachoir.parser import createParser
from hachoir.metadata import extractMetadata


def read_caption(file_name_path):
    caption_file_path = '{fn}.txt'.format(fn=file_name_path)
    while True:
        try:
            with open(caption_file_path) as caption_file:
                caption_text = caption_file.read()
                logging.info('Caption file contains:\n{0}'.format(caption_text))
                return caption_text, caption_file_path
        except OSError:
            logging.info('Cannot open file with caption: {0}. Will try again for one minute.\n{1}'.format(
                caption_file_path, OSError)
            )
            sleep(60)


def move_video_to_sent_folder(file_path):
    file_dirname = path.dirname(file_path)
    sent_dir = '{0}/sent/'.format(file_dirname)
    if not path.exists(sent_dir):
        try:
            makedirs(sent_dir)
        except OSError:
            logging.info('Exception occured during directory creation:\n{0}'.format(OSError))
            exit(1)

    logging.info('File will be moved to {0}'.format(sent_dir))

    try:
        rename(file_path, '{0}/{1}'.format(sent_dir, path.basename(file_path)))
    except OSError:
        logging.info('Exception occured during file move:\n{0}'.format(OSError))
        exit(1)


def too_big(file_path, file_name_path, file_ext, metadata, exceed_factor):
    new_file_path = file_name_path + '_smaller' + file_ext
    convert_params = ['ffmpeg',
                      '-loglevel', 'quiet',
                      '-i', file_path,
                      '-s', '{width}x{height}'.format(width=int(metadata.get('width')/exceed_factor),
                                                      height=int(metadata.get('height')/exceed_factor)),
                      new_file_path]

    logging.info('File will be converted with:\n{0}'.format(convert_params))

    while True:
        try:
            out = subprocess.run(convert_params, check=True)
        except subprocess.CalledProcessError as Error:
            logging.info('Error during file conversion: {0}\nCommand output: {1}\nTrying once again'.format(
                Error,
                out
            ))
        else:
            break

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

    while True:
        logging.info('Uploading file')
        try:
            upload_message = client.create_video(username, caption=caption, data=file_path)
            logging.info('Tumblr upload message:\n{0}'.format(upload_message))
        except ConnectionError as Error:
            logging.info('Connection error: {0}'.format(Error))
        else:
            # server errors:
            # - upload_message: {'meta': {'status': 400, 'msg': 'Bad Request'},
            #       'response': {'errors': [
            #           'This video is longer than your daily upload limit allows. Try again tomorrow.'
            #       ]
            # }}
            # - upload-message: {
            #       'response': {'message': 'You can only have one video transcoding at a time.', 'code': 11},
            #       'meta': {'status': 429, 'msg': 'Limit Exceeded'}}
            # wait and try again

            upload_message_meta = upload_message.get('meta')

            if upload_message_meta != None:

                print('upload message meta status: ', upload_message_meta)

                message_status = upload_message_meta.get('status')

                # Transcoding limit exceeded error
                if 429 == message_status:
                    try_again_time = 10
                # Max daily upload movie length limit reached
                elif 400 == message_status:
                    # check every hour
                    try_again_time = 3600
                else:
                    try_again_time = 360

                logging.info('Server side error ocured. Will try again for {0} seconds'.format(try_again_time))
                sleep(try_again_time)
                continue

            break


def main():
    try_again_time = 600

    argument_parser = ArgumentParser()
    argument_parser.add_argument('-v', '--verbose', action='store_true',
                                 help='Turn on verbose mode - will log events to console')
    argument_parser.add_argument('-p', '--path', required=True, action='store',
                                 help='Path to directory where the files to upload are')
    argument_parser.add_argument('-d', '--delete', action='store_true',
                                 help='Delete file rather than store it in sent foler')
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

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
        logging.info('Verbose mode turned on')

    # INFINITY LOOP START
    while True:
        # list all files in folder
        dirpath = args.path
        for filename in sorted([f for f in listdir(dirpath) if path.isfile(path.join(dirpath, f))]):
            file_path = path.join(dirpath, filename)
            file_name_path, file_ext = path.splitext(file_path)
            if file_ext != '.mp4':
                continue
            logging.info('File path: {0}'.format(file_path))


            # File can't be bigger than 100MB
            # if so, video will be compressed (later)
            # but now check how many times is it too big
            file_size = path.getsize(file_path)
            logging.info('File size: {0}'.format(file_size))

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
                                                         # video resolution denominator
                logging.info('File is too big')
                file_path = too_big(file_path, file_name_path, file_ext, metadata, exceed_factor)

            file_length = metadata.get('duration')
            logging.info('File length: {0}'.format(file_length))

            # read caption from file
            caption_text, caption_file_path = read_caption(file_name_path)

            upload(file_path, args.username, caption_text, args.consumer_key, args.consumer_secret, args.oauth_token,
                   args.oauth_secret)

            # after upload remove file with caption
            try:
                remove(caption_file_path)
            except OSError:
                logging.info('File not removed\n{0}'.format(OSError))

            if args.delete:
                remove(file_path)
            else:
                move_video_to_sent_folder(file_path)

        # Wait 10 mins before rerun the directory scanning
        logging.info('Waiting for new files. Scanning directory every {0} seconds'.format(try_again_time))
        sleep(try_again_time)


if __name__ == '__main__':
    main()
