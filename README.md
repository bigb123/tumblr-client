# tumblr-client
Tumblr script to auto upload files. Written in python 3. Created io queue multiple short videos. Designed to run in text mode.

Reason of it's creation was the poor internet connection. In case of bigger files (> 50MB) Tumblr web interface was dropping the connection saying "Connection error". It was easier to send files with ssh and to the server located in other part of the world and upload them to Tumblr service directly from in. It was also important that client can run as text mode daemon.

Right now script is uploading only mp4 files. It is sendint as much videos as possible a day. After file upload server response is reading and decision what to do next is being taken:
* if success: upload next video
* if video processing error try uploading again
* if the video uploaded time reached the limit wait longer and try again
* if any other error try again for a while

For this moment script uploading only mp4 files. It is reading caption from <video_name>.txt file. If there is no such a txt file it is waiting a while and trying to find file once again (infinity loop). It is moving sent files to "sent" directory in given path. If all files are sent it is scanning given directory every period of time. 

# Usage:
```
usage: upload.py [-h] [-v] -p PATH --username USERNAME --consumer-key
                 CONSUMER_KEY --consumer-secret CONSUMER_SECRET --oauth-token
                 OAUTH_TOKEN --oauth-secret OAUTH_SECRET

where:
-p / --path       - path to directory with videos to upload
--username        - tumblr username
--consumer-key    - obtained from tumblr
--consumer-secret - as above
--oauth-token     - as above
--oauth-secret    - as above
```

You can obtain your Tumblr api credentials on https://api.tumblr.com. They are unique for each account.

Dependencies:
- ffmpeg (libav debian package, works also on macos: brew install libav)
- hachoir3 (pip3 install hachoir3)
- py3tumblr (pip3 install Py3Tumblr)
