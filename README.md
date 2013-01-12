smart-move
==========

The plugin improves Deluge 'move storage' functionality in several ways:
* Statusbar indicates when one or more torrent storages are being moved
* Click the statusbar indicator to view the details: the torrent name, the destination folder and the progress bar for each currently moving torrent
* In Deluge when a user tries to move storage to a folder that already contains a file/directory with the same name as the torrent, nothing happens. SmartMove notifies the user when this situation occurs and suggests to view the destination folder.

I have tested the plugin on Ubuntu 12.04 and 10.04. I hope it works on other systems, although it is known not to work on Windows.
The plugin has a GTK UI and I am not currently planning to work on web UI.
