#!/usr/bin/env python

import sys, time
#from PySide.QtCore import *
#from PySide.QtGui import *
from PySide import QtCore, QtGui
#import PySide.QtCore, PySide.QtGui

import os;  # for strip EOL and port selection

sys.settrace

from filterstage_ui import Ui_MainWindow # when using pyside-uic
#from filterstage_ui import * # when using pyuic4 (PyQt4) --> be carefull with import *!

import simplejson as json

try:
    import serial
    import serial.tools.list_ports as listPorts
except Exception, e:
#    raise ImportError("Required package 'pyserial' not found.")
    print "Required package 'pyserial' not found."
    print "No serial port functionality."

favPort = "/dev/ttyFTDI0"
baudRates = ("9600", "38400", "115200")
endl = os.linesep

class Receiver(QtCore.QThread):

    update = QtCore.Signal()    # New signal to emit (connected to a function in main form)

    def __init__(self, parent):

        self.starter = 1
        self.runner = 0
        self.SL_MS = 0.01
        self.parent = parent
        QtCore.QThread.__init__(self, parent)

    def run(self):
        while self.starter:
            time.sleep(self.SL_MS)
            if self.runner:
                line = self.parent.ser.readline()
                if (line): # chunk is line!
                    self.parent.terminalAdd(line)
                    self.parent.termJson(line)
                    self.update.emit()


class ConSender(QtCore.QThread):

    update = QtCore.Signal()

    def __init__(self, parent):

        self.starter = 1
        self.runner = 0
        self.SL_MS = 2.00
        self.parent = parent
        QtCore.QThread.__init__(self, parent)

    def run(self):
        while self.starter:
            time.sleep(self.SL_MS)
            if self.runner:
                sertext = "{\"fstat\":{\"type\":\"long\"}}"

class Window(QtGui.QMainWindow, Ui_MainWindow):

    update = QtCore.Signal()    # Signal for this class that emits a 'update' (see function!)

    vmax = (99, 136, 167, 197, 213, 228, 243, 273, 303, 334, 364, 395, 456, 546, 729, 973)  # FS/s
    current = (59, 71, 84, 100, 119, 141, 168, 200, 238, 283, 336, 400, 476, 566, 673, 800) # Peak Current in mA
    absthr = ('off', 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5) # Absolute threshold level in V
    delthr = ('off', 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75) # Delta Threshold level in V
    minsamples = [87, 130, 174, 217, 261, 304, 348, 391]    # delay time in us (for f=22.8 kHz)

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.comboBox.addItems(self.scanPorts())
        self.statusBar().showMessage('Ready')
        for entry in xrange(len(self.minsamples)):
            self.comboBoxMinSamples.addItem(str(self.minsamples[entry]))
        ''' Set up threads. '''
        self.thread_receiver = Receiver(self)
        self.thread_consender = ConSender(self)
        ''' Set up signals. '''
        self.openButton.clicked.connect(self.click_openButton)
        self.closeButton.clicked.connect(self.click_closeButton)

        self.refreshPortPushButton.clicked.connect(self.updatePorts)
        self.sendPushButton.clicked.connect(self.sendOne)
        self.lineEditsend.returnPressed.connect(self.sendPushButton.click)
        self.pushButtonShort.clicked.connect(self.sendPosShort)
        self.lineEditShort.returnPressed.connect(self.pushButtonShort.click)
        self.pushButtonLong.clicked.connect(self.sendPosLong)
        self.lineEditLong.returnPressed.connect(self.pushButtonLong.click)

        self.horizontalSliderShort.sliderReleased.connect(self.sendPosShort)
        self.horizontalSliderLong.sliderReleased.connect(self.sendPosLong)

        self.pushButtonClearTerm.clicked.connect(self.clearTerm)

        self.pushButtonSaveConfig.clicked.connect(self.saveConfig)
        self.pushButtonLoadConfig.clicked.connect(self.loadConfig)

        ''' Stall Detection '''
        self.pushButtonSetStall.clicked.connect(self.sendStallLong)
        self.pushButtonSetMotor.clicked.connect(self.sendMotor)

        self.thread_receiver.update.connect(self.terminalUpdate)
        self.update.connect(self.terminalUpdate)
        self.thread_consender.update.connect(self.terminalUpdate)


        self.thread_receiver.start()

    def changeSlider(self):
        self.lineEditAbsThr.setText(str(self.absthr[self.verticalSliderAbsThr.value()]))
        self.lineEditDelThr.setText(str(self.delthr[self.verticalSliderDelThr.value()]))

    def saveConfig(self):

        conf = {}
        conf['fmotor'] = {}
        conf['fmotor']['type'] = "long"
        conf['fmotor']['ihold'] = self.verticalSliderIhold.value()
        conf['fmotor']['irun'] =  self.verticalSliderIrun.value()
        conf['fmotor']['vmin'] = self.verticalSliderVmin.value()
        conf['fmotor']['vmax'] = self.verticalSliderVmax.value()
        conf['fmotor']['acc'] = self.verticalSliderAcc.value()
        conf['fmotor']['shaft'] = self.dialShaft.value()
        conf['fmotor']['secpos'] = 0
        conf['fmotor']['stepmode'] = self.comboBoxStepmode.currentIndex()
        conf['fmotor']['accshape'] = 0

        print json.dumps(conf)
        filename = QtGui.QFileDialog.getSaveFileName(self, 'Save File', '.')
        fname = open(filename[0], 'w')
        fname.write(json.dumps(conf, sort_keys=True, indent=4, separators=(',',':')))
        fname.close()

    def loadConfig(self):
        filename = QtGui.QFileDialog.getOpenFileName(self, 'Load File', '.')
        fname = open(filename[0], 'r')
        conf = json.loads(fname.read())
        fname.close()
        self.sendLine(json.dumps(conf))
        #print conf     # deserialize to a python object
        print json.dumps(conf)     # json formatted str ""

    def sendMotor(self):
        conf = {}
        conf['fmotor'] = {}
        conf['fmotor']['type'] = "long"
        conf['fmotor']['ihold'] = self.verticalSliderIhold.value()
        conf['fmotor']['irun'] =  self.verticalSliderIrun.value()
        conf['fmotor']['vmin'] = self.verticalSliderVmin.value()
        conf['fmotor']['vmax'] = self.verticalSliderVmax.value()
        conf['fmotor']['acc'] = self.verticalSliderAcc.value()
        conf['fmotor']['shaft'] = self.dialShaft.value()
        conf['fmotor']['secpos'] = 0
        conf['fmotor']['stepmode'] = self.comboBoxStepmode.currentIndex()
        conf['fmotor']['accshape'] = 0
        self.sendLine(json.dumps(conf))


    def sendStallLong(self):
        self.lineEditAbsThr.setText(str(self.absthr[self.verticalSliderAbsThr.value()]))
        self.lineEditDelThr.setText(str(self.delthr[self.verticalSliderDelThr.value()]))

        stall = {}
        stall['fstall'] = {}
        stall['fstall']['type'] = "long"
        stall['fstall']['dc100'] = self.pushButtonDC100En.isChecked()
        stall['fstall']['pwmjen'] = self.pushButtonPWMJEn.isChecked()
        stall['fstall']['minsamples'] = self.comboBoxMinSamples.currentIndex()
        stall['fstall']['fs2stallen'] = self.spinBoxFS2StallEN.value()
        stall['fstall']['delthr'] = self.verticalSliderDelThr.value()
        stall['fstall']['absthr'] = self.verticalSliderAbsThr.value()
        print json.dumps(stall)
        self.sendLine(json.dumps(stall))

    def terminalAdd(self, message):
        self.textEditTerm.append(message.rstrip('\r\n'))

    def termJson(self, message):
        # is message my json string?
        try:
            jdat = json.loads(message)
            #print jdat
            jdat_str = json.dumps(jdat)
            #self.termWindow.insertPlainText(jdat_str)
            self.termWindow.append(jdat_str)
            #self.termWindow.insertPlainText(jdat['type'])
            # Call parser
            self.parseJson(jdat)
            #if 'fshift' in jdat:
            #    print jdat['fshift']['type']
        except Exception, e:
            #print "Error:", e
            pass

    def parseJson(self, jmsg):
        # JSON parser (is called only for a valid JSON object)
        print jmsg

        if 'fstall' in jmsg:
            self.lineEditDC100.setText(str(jmsg['fstall']['dc100']))
            self.lineEditFS2StallEn.setText(str(jmsg['fstall']['fs2stallen']))
            self.lineEditPWMJEn.setText(str(jmsg['fstall']['pwmjen']))
            self.lineEditDC100StEn.setText(str(jmsg['fstall']['dc100sten']))
            self.lineEditMinSamples.setText(str(jmsg['fstall']['minsamples']))
            self.lineEditDelStallHi.setText(str(jmsg['fstall']['delstallhi']))
            self.lineEditDelStallLo.setText(str(jmsg['fstall']['delstalllo']))
            self.lineEditAbsStall.setText(str(jmsg['fstall']['absstall']))
            self.lineEditAbsThr.setText(str(self.absthr[jmsg['fstall']['absthr']]))
            self.lineEditDelThr.setText(str(self.delthr[jmsg['fstall']['delthr']]))

        if 'fstat' in jmsg:

            self.verticalSliderIhold.setValue(jmsg['fstat']['ihold'])
            self.verticalSliderIrun.setValue(jmsg['fstat']['irun'])
            self.lineEditIhold.setText(str(self.current[jmsg['fstat']['ihold']]))
            self.lineEditIrun.setText(str(self.current[jmsg['fstat']['irun']]))
            self.verticalSliderVmin.setValue(jmsg['fstat']['vmin'])
            self.verticalSliderVmax.setValue(jmsg['fstat']['vmax'])
            self.verticalSliderAcc.setValue(jmsg['fstat']['acc'])
            self.comboBoxStepmode.setCurrentIndex(jmsg['fstat']['stepmode'])
            self.dialShaft.setValue(jmsg['fstat']['shaft'])

            # Status information
            self.checkBoxVddReset.setChecked(bool(jmsg['fstat']['vddreset']))
            self.checkBoxOVC1.setChecked(bool(jmsg['fstat']['ovc1']))
            self.checkBoxOVC2.setChecked(bool(jmsg['fstat']['ovc2']))
            self.checkBoxStepLoss.setChecked(bool(jmsg['fstat']['steploss']))
            self.checkBoxElDef.setChecked(bool(jmsg['fstat']['eldef']))
            self.checkBoxUV2.setChecked(bool(jmsg['fstat']['uv2']))
            self.checkBoxTW.setChecked(bool(jmsg['fstat']['tw']))
            self.checkBoxTSD.setChecked(bool(jmsg['fstat']['tsd']))
            self.checkBoxESW.setChecked(bool(jmsg['fstat']['esw']))
            self.checkBoxCPFail.setChecked(bool(jmsg['fstat']['cpfail']))
            self.comboBoxMotion.setCurrentIndex(jmsg['fstat']['motion'])
            self.comboBoxTinfo.setCurrentIndex(jmsg['fstat']['tinfo'])

        if 'status' in jmsg:
            self.thread_consender.start()
            self.enableThread(self.thread_consender)
            self.thread_consender.start = 1

#            if jmsg['fstat']['type'] == "short":
#                self.lineEditActualPosShort.setText(str(jmsg['fstat']['apos']))
#            else:
#                self.lineEditActualPosLong.setText(str(jmsg['fstat']['apos']))

            #print motorstat.encode("hex")
            # convert str to list
            #l = list(motorstat)
            # keep it as an int number
            #stat1 = {'Irun': int(l[0],16)}
            #print stat


    def terminalUpdate(self):
        ''' Updates the terminal window '''
        #print "update"
        #self.textBrowser.verticalScrollBar().setValue( self.textBrowser.verticalScrollBar().maximum() )
        
        # uncommentent because of segfaults
        #mycursor = QtGui.QTextCursor(self.textEditTerm())
        #mycursor.setPosition(end)
        #self.textEditTerm.setPosition(QtGui.QTextCursor.End)
        #self.textEditTerm.QTextCursor.setPosition(
        #editor = self.textEditTerm()



#        cursor = self.textEditTerm.textCursor()     # return a copy that represents the currently visible cursor
#        cursor.movePosition(QtGui.QTextCursor.End)      # move the 
#        self.textEditTerm.setTextCursor(cursor)     # update the visible cursor

        self.textEditTerm.moveCursor(QtGui.QTextCursor.End) # this alone should work
        self.termWindow.moveCursor(QtGui.QTextCursor.End)



#        self.textEditTerm.

        #cursor = self.termWindow.textCursor()
        #cursor.movePosition(QtGui.QTextCursor.End)
        #self.termWindow.setTextCursor(cursor)

        #self.textEditTerm.setTextCursor(QtGui.QTextCursor.End)
        #self.textBrowser.moveCursor(QtGui.QTextCursor.End)
        #self.textBrowser.ensureCursorVisible()

        #self.termWindow.moveCursor(QtGui.QTextCursor.End)
        #self.termWindow.ensureCursorVisible()

    def updatePorts(self):
        self.comboBox.clear()
        self.comboBox.addItems(self.scanPorts())

#    def setupUi(self):
#        self.ui.setupUI(self)
#        self.ui.ComboBox.addItems(baudRates)
#        self.statusBar().showMessage('Ready')
        #self.refreshPorts()

    def readData(self):
#        print"timer function"
        lineread=self.ser.readline()
        if lineread:
            self.textBrowser.insertPlainText(lineread)
            #self.textBrowser.verticalScrollBar().setValue( self.textBrowser.verticalScrollBar().maximum() )

    def scanPorts(self):
#        print(list(serial.tools.list_ports.comports()))
#        comPorts = listPorts.comports()
        ports = []
        for port, desc, hwid in listPorts.comports():
            if hwid != 'n/a': # != oder grep() statt comports()
                ports.append(port)
#        self.comboBox.addItems(sorted(comPorts))
#        print (comPorts)
        return sorted(ports)

    def click_openButton(self): # common openport funktion hier?
#        self.close()
        portSelector = self.comboBox.currentText()
        try:
            self.statusBar().showMessage('Connecting port %s ... ' % portSelector)
            #self.ser = serial.Serial(str(portSelector), 9600, timeout=0.01)
            self.ser = serial.Serial(str(portSelector), 115200, timeout=0.01)
            self.ser.flushInput()
            self.openButton.setDisabled(True)
            self.closeButton.setDisabled(False)
            self.comboBox.setDisabled(True)
#            self.statusBar().showMessage('Connected to %s' % portSelector, 2000)
            self.statusBar().showMessage('Connected to %s' % portSelector)
#            self.scrollArea.textEdit.appen
            self.thread_receiver.start()
            self.enableThread(self.thread_receiver)
            self.thread_receiver.starter = 1
        except serial.SerialException:
            self.statusBar().showMessage("Failed to open port")
            self.ser = None

    def click_closeButton(self):
        try:
            self.statusBar().showMessage('Disconnecting ...', 2000)
            self.thread_receiver.starter = 0
            self.thread_receiver.wait()
            self.thread_receiver.exit()
            self.thread_receiver.wait()
            self.thread_consender.starter = 0
            self.thread_consender.wait()
            #self.disableThread(self.thread_consender)
            self.thread_consender.exit()
            self.thread_consender.wait()
            self.ser.close()
            self.openButton.setDisabled(False)
            self.closeButton.setDisabled(True)
            self.comboBox.setDisabled(False)
        except None:
            pass

    def enableThread(self, thread):
        ''' Enables the thread processing loop '''
        thread.runner = 1
        return True

    def disableThread(self, thread):
        ''' Disables the thread processing loop '''
        thread.runner = 0
        return True

    def sendOne(self):
        ''' Send one was clicked '''
        currentline = self.lineEditsend.text()
        self.lineEditsend.clear()
        self.sendLine(currentline)

    def sendPosShort(self):
        ''' Send Short Position '''
        position = int(self.lineEditShort.text())
        jdict = {'fpos': {'type':'short', 'pos':position}}
        # print jdict
        print json.dumps(jdict)
        self.sendLine(json.dumps(jdict))

    def sendPosLong(self):
        ''' Send Long Position '''
        position = int(self.lineEditLong.text())
        #position = int(self.horizontalSliderLong.value())
        jdict = {'fpos': {'type':'long', 'pos':position}}
        # print jdict
        print json.dumps(jdict)
        self.sendLine(json.dumps(jdict))

        # get stat
        jdict = {'fstat': {'type':'long'}}
        self.sendLine(json.dumps(jdict))

    def sendLine(self, message):
        ''' Send one line to the serial port and add it to the terminal window '''
        self.terminalAdd(message+"\n")
        self.ser.writeTimeout = 0.1
        try:
            self.ser.write((message+"\n").encode('utf-8'))
        except serial.SerialTimeoutException:
            self.terminalAdd('Error: Serial command timed out')
        # self.emit.update()   # (not self.emit.update()) but self.update.emit() !!!
        self.update.emit()

    def clearTerm(self):
        self.textBrowser.clear()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())
