#!/usr/bin/env python
"""The GTK-GUI view for subprocs"""
__author__ = "Martin Zackrisson"
__copyright__ = "Swedish copyright laws apply"
__credits__ = ["Martin Zackrisson"]
__license__ = "GPL v3.0"
__version__ = "0.997"
__maintainer__ = "Martin Zackrisson"
__email__ = "martin.zackrisson@gu.se"
__status__ = "Development"

#
# DEPENDENCIES
#

import pygtk
pygtk.require('2.0')
import gtk
import gobject
"""
from matplotlib.backends.backend_gtk import FigureCanvasGTK as FigureCanvas
import matplotlib.image as plt_img
import matplotlib.pyplot as plt
import matplotlib.text as plt_text
import matplotlib.patches as plt_patches
"""

#
# INTERNAL DEPENDENCIES
#

from src.view_generic import *

#
# STATIC GLOBALS
#

"""Gotten from view_generic instead
PADDING_LARGE = 10
PADDING_MEDIUM = 4
PADDING_SMALL = 2
"""

#
# CLASSES
#

class Subprocs_View(gtk.Frame):

    def __init__(self, controller, model, specific_model):

        super(Subprocs_View, self).__init__(model['composite-stat-title'])

        self._model = model
        self._controller = controller
        self._specific_model = specific_model

        table = gtk.Table(rows=4, columns=2)
        table.set_col_spacings(PADDING_MEDIUM)
        table.set_row_spacing(0, PADDING_MEDIUM)
        table.set_row_spacing(3, PADDING_MEDIUM)
        self.add(table)

        """ HEADER ROW REMOVED
        label = gtk.Label()
        label.set_markup(model['composite-stat-type-header']) 
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1 , 0, 1)

        label = gtk.Label()
        label.set_markup(model['composite-stat-count-header'])
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, 0, 1)
        """
        label = gtk.Label(model['free-scanners']) 
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1 , 0, 1)

        self.scanners = gtk.Button()
        self.scanners.set_label(str(specific_model['free-scanners']))
        self.scanners.connect("clicked", controller.produce_free_scanners)
        self.scanners.set_alignment(0, 0.5)
        table.attach(self.scanners, 1, 2, 0, 1)

        label = gtk.Label(model['running-experiments'])
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2)

        self.experiments = gtk.Button()
        self.experiments.set_label(str(specific_model['running-scanners']))
        self.experiments.connect("clicked", controller.produce_running_experiments)
        table.attach(self.experiments, 1, 2, 1, 2)

        label = gtk.Label(model['running-analysis'])
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 2, 3)

        self.analysis = gtk.Button()
        self.analysis.set_label(str(specific_model['running-analysis']))
        self.analysis.connect("clicked", controller.produce_running_analysis)
        table.attach(self.analysis, 1, 2, 2, 3)

        label = gtk.Label(model['collected-messages'])
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 3, 4)

        self.messages = gtk.Button()
        self.messages.set_label(str(specific_model['collected-messages']))
        table.attach(self.messages, 1, 2, 3, 4)

        self.show_all()


    def update(self):

        specific_model = self._specific_model
        
        self.scanners.set_label(str(specific_model['free-scanners']))
        self.experiments.set_label(str(specific_model['running-scanners']))
        self.analysis.set_label(str(specific_model['running-analysis']))
        self.messages.set_label(str(specific_model['collected-messages']))


class Running_Experiments(gtk.VBox):

    def __init__(self, controller, model, specific_model):

        super(Running_Experiments, self).__init__(False, 0)

        self._controller = controller
        self._model = model
        self._specific_model = specific_model

        label = gtk.Label()
        label.set_markup(model['running-experiments-intro'])
        self.pack_start(label, False, False, PADDING_LARGE)

        self._stuff = list()

        for p in controller.get_subprocesses(self, by_type='experiment'):
            frame = gtk.Frame(p['sm']['experiment-prefix'])
            vbox = gtk.VBox(False, 0)
            frame.add(vbox)
            progress = gtk.ProgressBar()
            vbox.pack_start(progress, False, False, PADDING_SMALL)
            self.pack_start(frame, False, False, PADDING_LARGE)
            hbox = gtk.HBox(False, 0)
            info = gtk.Label()
            button = gtk.Button()
            button.set_label(model['running-experiments-stop'])
            button.connect("clicked", self._verify_stop, p)
            hbox.pack_start(info, True, True, PADDING_LARGE)
            hbox.pack_end(button, False, False, PADDING_LARGE)
            vbox.pack_start(hbox, False, False, PADDING_MEDIUM)
            
            self._stuff.append((p, progress, info))
           
        self.show_all()
        gobject.timeout_add(20, self.update)

    def _verify_stop(self, widget, proc):

        def _verify_sure(widget, b_yes):

            if widget.get_text().lower() == 'stop':
                b_yes.set_sensitive(True)
            else:
                b_yes.set_sensitive(False)

        m = self._model
        dialog = gtk.MessageDialog(self._controller.get_window(),
                        gtk.DIALOG_DESTROY_WITH_PARENT,
                        gtk.MESSAGE_WARNING, gtk.BUTTONS_NONE,
                        "")

        b_no = dialog.add_button(gtk.STOCK_NO, False)
        b_yes = dialog.add_button(gtk.STOCK_YES, True)
        b_yes.set_sensitive(False)

        vbox = dialog.get_children()[0]
        hbox, bbox = vbox.get_children()
        im, vbox2 = hbox.get_children()
        vbox2.remove(vbox2.get_children()[1])
        label = vbox2.get_children()[0]
        label.set_markup(
            m['running-experiments-stop-warning'].format(
            proc['sm']['experiment-prefix']))

        entry = gtk.Entry()
        entry.connect("changed", _verify_sure, b_yes)
        vbox2.pack_start(entry, False, False, PADDING_SMALL)

        dialog.show_all()

        resp = dialog.run()

        dialog.destroy()
 
        if resp == True:

            self._controller.stop_process(proc)
            proc['progress'] = proc['sm']['scans']
            widget.set_sensitive(False)
            widget.set_label(m['running-experiments-stopping'])
            self.update()

    def update(self):

        sm = self._specific_model
        for p, progress, info in self._stuff:
            
            progress.set_fraction(p['progress']/float(p['sm']['scans']))
            eta = (p['sm']['scans'] - p['progress']) * p['sm']['interval'] / 60.0
            progress.set_text("Expected to finnish in {0:.2f}h".format(eta))
            info.set_text("Feedback not yet implemented")