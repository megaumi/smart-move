#
# gtkui.py
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

import gtk
import logging

from deluge.ui.client import client
from deluge.plugins.pluginbase import GtkPluginBase
import deluge.component as component
import deluge.common

from common import get_resource

log = logging.getLogger(__name__)

class GtkUI(GtkPluginBase):
    def enable(self):
        self.glade = gtk.glade.XML(get_resource("config.glade"))

        component.get("Preferences").add_page("SmartMove", self.glade.get_widget("prefs_box"))
        component.get("PluginManager").register_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").register_hook("on_show_prefs", self.on_show_prefs)
        self.status_item = component.get("StatusBar").add_item(image=None, text="",
            callback=self.show_tasks, tooltip="Click to see the details")
        self.view = View()

        # {task_id: gtk.TreeIter} mapping
        self.rows = {}

    def update(self):
        client.smartmove.get_progress().addCallback(self.update_gui)
        client.smartmove.get_messages().addCallback(self.process_messages)

    def update_gui(self, tasks):
        self.update_statusbar(len(tasks))
        self.update_torrent_view(tasks)

    def update_torrent_view(self, tasks):
        # Update extisting or create new rows for current tasks
        for task in tasks:
            if task.id in self.rows:
                self.view.store.set(self.rows[task.id], 1, task.torrent.torrent_info.name())
                self.view.store.set(self.rows[task.id], 2, task.cur_percent)
                self.view.store.set(self.rows[task.id], 3, task.dest)
            else:
                treeiter = self.view.store.append([
                    task.id,
                    task.torrent.torrent_info.name(),
                    task.cur_percent,
                    task.dest])
                self.rows[task.id] = treeiter

        # Delete rows corresponding to completed tasks
        current_task_ids = [task.id for task in tasks]
        remove = [task_id for task_id in self.rows if task_id not in current_task_ids]
        for task_id in remove:
            self.view.store.remove(self.rows[task_id])
            del self.rows[task_id]

    def update_statusbar(self, num_tasks):
        if num_tasks:
            self.status_item.set_text("Moving data: %s left"
            % num_tasks)
        else:
            self.status_item.set_text("")

    def show_tasks(self, *args):
        self.view.window.show()

    def process_messages(self, messages):
        """Process messages from core, such as errors, messages for the user, etc"""
        if messages:
            msg = messages.pop(0)
            if msg.type == 'already_contains':
                AlreadyContainsDialog(msg).show()

    def disable(self):
        component.get("Preferences").remove_page("SmartMove")
        component.get("PluginManager").deregister_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").deregister_hook("on_show_prefs", self.on_show_prefs)
        component.get("StatusBar").remove_item(self.status_item)
        del self.status_item

    def on_apply_prefs(self):
        log.debug("applying prefs for SmartMove")
        config = {
            "test":self.glade.get_widget("txt_test").get_text()
        }
        client.smartmove.set_config(config)

    def on_show_prefs(self):
        client.smartmove.get_config().addCallback(self.cb_get_config)

    def cb_get_config(self, config):
        "callback for on show_prefs"
        self.glade.get_widget("txt_test").set_text(config["test"])

class View(object):
    """A table of currently moving tasks: torrent name, progress and destination folder"""
    def __init__(self):
        self.glade = gtk.glade.XML(get_resource("torrent_view.glade"))
        self.window = self.glade.get_widget("torrent_view_window")
        self.torrentview = self.glade.get_widget("torrent_view")
        self.store = gtk.ListStore(int, str, int, str)
        self.torrentview.set_model(self.store)

        # Set up columns
        renderer = gtk.CellRendererText()

        task_col = gtk.TreeViewColumn('Task', renderer)
        task_col.add_attribute(renderer, "text", 0)
        task_col.set_visible(False)
        self.torrentview.append_column(task_col)

        name_col = gtk.TreeViewColumn('Name', renderer)
        name_col.add_attribute(renderer, "text", 1)
        self.torrentview.append_column(name_col)

        p_renderer = gtk.CellRendererProgress()
        progress_col = gtk.TreeViewColumn('Progress', p_renderer)
        progress_col.add_attribute(p_renderer, "value", 2)
        self.torrentview.append_column(progress_col)

        dest_col = gtk.TreeViewColumn('Destination', renderer)
        dest_col.add_attribute(renderer, "text", 3)
        self.torrentview.append_column(dest_col)

class AlreadyContainsDialog(object):
    def __init__(self, msg):
        self.msg = msg
        self.glade = gtk.glade.XML(get_resource("already_contains_dialog.glade"))
        self.window = self.glade.get_widget("dialog")
        self.label = self.glade.get_widget("label")
        self.label.set_text('The destination folder already contains %s.'
            '\nTorrent storage will NOT be moved.' % msg.t_name)
        self.glade.signal_autoconnect(self)

    def show(self):
        self.window.show()

    def on_ok_button_clicked(self, widget):
        self.window.destroy()

    def on_open_folder_button_clicked(self, widget):
        deluge.common.open_file(self.msg.dest)