# tumblr-client
Tumblr script for auto upload files. Written in python 3. Created to queue multiple short videos. Designed to run in text mode.

Reason of it's creation was the poor internet connection. In case of bigger files (> 50MB) Tumblr web interface was dropping the connection saying "Connection error". It was easier to send files via ssh to the server located in other part of the world and upload them to Tumblr service directly from it. It was also important that client can be running as text mode daemon.

Right now script is uploading only mp4 files. It is uploading as much videos as possible a day. After file upload server response is reading and decision what to do next is being taken:
* if success: upload next video
* if video processing error try uploading again
* if the video uploaded time reached the limit wait longer and try again
* if any other error try again in some time

For this moment script uploading only mp4 files. It is reading caption from <video_name>.txt file. If there is no such a txt file it is waiting a while and trying to find file once again (infinity loop). It is moving uploaded file to "sent" directory in given path. If all files are sent it is scanning given directory from time to time. 

# Usage:
```
usage: upload.py [-h] [-v] [-l LOG] -p PATH [-d] --username USERNAME
                 --consumer-key CONSUMER_KEY --consumer-secret CONSUMER_SECRET
                 --oauth-token OAUTH_TOKEN --oauth-secret OAUTH_SECRET

Required arguments:
  -p PATH, --path PATH  Path to directory where the files to upload are
  --username USERNAME   User name/nick of the account
  --consumer-key CONSUMER_KEY
                        Consumer key
  --consumer-secret CONSUMER_SECRET
                        Consumer secret
  --oauth-token OAUTH_TOKEN
                        OAuth token
  --oauth-secret OAUTH_SECRET
                        OAuth secret

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Turn on verbose mode
  -l LOG, --log LOG     Path to log file. Useful with --verbose option
  -d, --delete          Delete file rather than store it in sent foler

```

You can obtain your Tumblr api credentials on https://api.tumblr.com. They are unique for each account.

Dependencies:
- ffmpeg (libav debian package, works also on macos: brew install libav)
- hachoir3 (pip3 install hachoir3)
- py3tumblr (pip3 install Py3Tumblr)
