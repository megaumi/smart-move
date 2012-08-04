#
# core.py
#
# Copyright (C) 2012 Valentina Mukhamedzhanova <umirra@gmail.com>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
# Copyright (C) 2010 Pedro Algarvio <pedro@algarvio.me>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#

import logging
import os
from deluge.plugins.pluginbase import CorePluginBase
import deluge.component as component
import deluge.configmanager
from deluge.core.rpcserver import export
from deluge.core.torrent import Torrent
from twisted.internet.task import LoopingCall

DEFAULT_PREFS = {
    "test":"NiNiNi"
}

log = logging.getLogger(__name__)

class Core(CorePluginBase):
    def enable(self):
        log.info('SmartMove: plugin enabled')
        self.config = deluge.configmanager.ConfigManager("smartmove.conf", DEFAULT_PREFS)
        self.monkeypatch()
        self.tasks = []
        self.updater = LoopingCall(self._update)
        self.updater.start(1)

    def disable(self):
        log.info('SmartMove: plugin disabled')
        Torrent.move_storage = self._orig_move_storage
        self.updater.stop()
        self.tasks = None

    def _update(self):
        """
        Updates information for each running task and deletes completed tasks.
        Runs once per second.
        """
        for task in self.tasks:
            prev_update_size = task.cur_size
            task.update()
            log.info('SmartMove: %s, %s, %s, %s, %s' %
                (task.torrent, task.size, task.cur_size, task.cur_percent,
                 task.counter))
            # Libtorrent's move_storage() does not signal if it is not going to
            # move data, so we check for size changes since the last 5 updates
            if len(self.tasks) == 1:
                if task.cur_size == prev_update_size:
                    task.counter += 1
                else:
                    task.counter = 0
                if task.counter >= 5:
                    log.info('SmartMove: looks like nothing is being moved')
                    self.tasks.remove(task)
            if task.cur_size >= task.size:
                log.info('SmartMove: move completed')
                self.tasks.remove(task)

    @export
    def get_progress(self):
        """Provides progress information on running tasks"""
        return self.tasks

    def monkeypatch(self):
        """Replaces calls to Torrent.move_storage()"""
        self._orig_move_storage = Torrent.move_storage

        def move_storage(torrent, dest):
            """Initiates moving data"""
            _orig_move_storage = self._orig_move_storage
            result = _orig_move_storage(torrent, dest)
            if result:
                self.tasks.append(Task(torrent, dest))
                log.info('SmartMove: started moving %s' % torrent)
            return result

        Torrent.move_storage = move_storage

    def update(self):
        """
        This is supposed to be called by Deluge every second,
        but it isn't. Need to fix in the upstream.
        """
        pass

    @export
    def set_config(self, config):
        """Sets the config dictionary"""
        for key in config.keys():
            self.config[key] = config[key]
        self.config.save()

    @export
    def get_config(self):
        """Returns the config dictionary"""
        return self.config.config

class Task(object):
    num_tasks = 0
    def __init__(self, torrent, dest):
        self.id = Task.num_tasks
        Task.num_tasks += 1
        self.torrent = torrent
        self.dest = dest
        self.files = [f['path'] for f in torrent.get_files()]
        self.source = torrent.get_options()['download_location']
        self.size = self.get_size(self.files, self.source)
        self.cur_size = 0
        self.cur_percent = 0
        self.counter = 0

    def get_size(self, files, path):
        """Returns total size of 'files' currently located in 'path'"""
        files = [os.path.join(path, f) for f in files]
        return sum(os.stat(f).st_size for f in files if os.path.exists(f))

    def update(self):
        self.cur_size = self.get_size(self.files, self.dest)
        self.cur_percent = self.cur_size * 100 / self.size
