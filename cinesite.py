# ================================================================
#
# Author: Christian Vizcarra Guerrero
# June 5, 2017
#
# ================================================================
#
# The program uses Arnold python API provided by the SDK Arnold-5.0.0.3-windows
#
# Render a sphere with user-defined color.
# The log file is displayed in the Log Output tab.
# The rendered image is loaded into the Rendered Image tab.
#
# ================================================================

import sys
import os
from PyQt4 import QtGui, QtCore
from arnold import *

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)


class renderImage(QtCore.QThread):

    renderDone = QtCore.pyqtSignal()

    def __init__(self, rImage, rLog, rPrimitive, rgb_render ):
        #
        QtCore.QThread.__init__(self)

        self.log_file = rLog
        self.image_file = rImage
        self.selected_primitve = rPrimitive
        self.renderR = rgb_render[0]
        self.renderG = rgb_render[1]
        self.renderB = rgb_render[2]


    def run(self):

        # start an Arnold session, log to both a file and the console
        AiBegin()
        AiMsgSetLogFileName(self.log_file)
        AiMsgSetConsoleFlags(AI_LOG_ALL)

        # create a sphere geometric primitive
        sph = AiNode(self.selected_primitve)
        AiNodeSetStr(sph, "name", "theSphere")
        AiNodeSetVec(sph, "center", 0.0, 2.0, 0.0)
        AiNodeSetFlt(sph, "radius", 8.0)

        # create a red standard shader
        shader1 = AiNode("standard")
        AiNodeSetStr(shader1, "name", "myshader1")
        AiNodeSetRGB(shader1, "Kd_color", self.renderR, self.renderG, self.renderB)
        AiNodeSetFlt(shader1, "Ks", 0.01)

        # assign the shaders to the geometric objects
        AiNodeSetPtr(sph, "shader", shader1)

        # create a perspective camera
        camera = AiNode("persp_camera")
        AiNodeSetStr(camera, "name", "mycamera")
        # position the camera (alternatively you can set 'matrix')
        AiNodeSetVec(camera, "position", 0.0, 10.0, 35.0)
        AiNodeSetVec(camera, "look_at", 0.0, 3.0, 0.0)
        AiNodeSetFlt(camera, "fov", 45.0)

        # create a point light source
        light = AiNode("point_light")
        AiNodeSetStr(light, "name", "mylight")
        # position the light (alternatively use 'matrix')
        AiNodeSetVec(light, "position", 15.0, 30.0, 15.0)
        AiNodeSetFlt(light, "intensity", 4200.0) # alternatively, use 'exposure'
        AiNodeSetFlt(light, "radius", 2.0) # for soft shadows

        # get the global options node and set some options
        options = AiUniverseGetOptions()
        AiNodeSetInt(options, "AA_samples", 8)
        AiNodeSetInt(options, "xres", 480)
        AiNodeSetInt(options, "yres", 360)
        AiNodeSetInt(options, "GI_diffuse_depth", 4)
        # set the active camera (optional, since there is only one camera)
        AiNodeSetPtr(options, "camera", camera)

        # create an output driver node
        driver = AiNode("driver_jpeg")
        AiNodeSetStr(driver, "name", "mydriver")
        AiNodeSetStr(driver, "filename", self.image_file)
        AiNodeSetFlt(driver, "gamma", 2.2)

        # create a gaussian filter node
        filter = AiNode("gaussian_filter")
        AiNodeSetStr(filter, "name", "myfilter")

        # assign the driver and filter to the main (beauty) AOV,
        # which is called "RGBA" and is of type RGBA
        outputs_array = AiArrayAllocate(1, 1, AI_TYPE_STRING)
        AiArraySetStr(outputs_array, 0, "RGBA RGBA myfilter mydriver")
        AiNodeSetArray(options, "outputs", outputs_array)

        # finally, render the image!
        AiRender(AI_RENDER_MODE_CAMERA)

        # Arnold session shutdown
        AiEnd()

        self.renderDone.emit()


class ExtendedQLabel(QtGui.QLabel):

    def __init(self, parent):
        QtGui.QLabel.__init__(self, parent)

    def mouseReleaseEvent(self, ev):
        self.emit(QtCore.SIGNAL('clicked()'))


class cinesiteWindow(QtGui.QDialog):

    def __init__(self):
        super(cinesiteWindow, self).__init__()

        self.setupUi(self)

        self.primitive = "sphere"
        # default colorview
        self.colorDisplay.setStyleSheet("QWidget { background-color: %s}" % "#00ff00")
        # default color for image render
        self.red = 0.0
        self.green = 1.0
        self.blue = 0.0
        # default folder and imagge name
        self.folder_path = os.path.dirname(__file__)
        self.img_render_name = 'cinesite_test.jpg'
        self.log_render_name = 'cinesite.log'

    def renderFinished(self):

        # Disable ui controls
        self.colorBtn.setEnabled(True)
        self.colorDisplay.setEnabled(True)
        self.renderBtn.setEnabled(True)

        # Stop progressBar
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setProperty("value", 100)

        # Set image to view
        img_path = os.path.join(self.folder_path, self.img_render_name)
        pixmap = QtGui.QPixmap(img_path)
        pixmap2 = pixmap.scaledToWidth(518)
        self.imageOutput.setPixmap(pixmap2)

        # read logfile
        log_path = os.path.join(self.folder_path, self.log_render_name)
        log_file = open(log_path, 'r')
        with log_file:
            text = log_file.read()
            self.logOutput.setText(text)

    def arnold_process(self):
        #
        rgb_color = [self.red, self.green, self.blue]
        self.processThread = renderImage(self.img_render_name, self.log_render_name, self.primitive, rgb_color)
        self.processThread.renderDone.connect(self.renderFinished)
        self.processThread.start()

    def renderImage(self):
        # Disable ui controls
        self.colorBtn.setEnabled(False)
        self.colorDisplay.setEnabled(False)
        self.renderBtn.setEnabled(False)

        # set progresBar format
        self.logOutput.setText("Rendering image...")
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(0)
        self.progressBar.setProperty("value", -1)

        # process render in arnold
        self.arnold_process()

    def setupUi(self, Dialog):
        #
        Dialog.setObjectName(_fromUtf8("renderDialogW"))
        Dialog.resize(881, 496)
        Dialog.setMinimumSize(QtCore.QSize(881, 496))
        Dialog.setMaximumSize(QtCore.QSize(881, 496))
        self.gridLayout = QtGui.QGridLayout(Dialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.logo = QtGui.QLabel(Dialog)
        self.logo.setMinimumSize(QtCore.QSize(0, 100))
        self.logo.setMaximumSize(QtCore.QSize(16777215, 100))
        self.logo.setStyleSheet(_fromUtf8("background-color: rgb(0, 0, 0);"))
        self.logo.setText(_fromUtf8(""))
        self.logo.setPixmap(QtGui.QPixmap(_fromUtf8("logo.png")))
        self.logo.setScaledContents(False)
        self.logo.setAlignment(QtCore.Qt.AlignCenter)
        self.logo.setObjectName(_fromUtf8("logo"))
        self.verticalLayout.addWidget(self.logo)
        self.description = QtGui.QLabel(Dialog)
        self.description.setTextFormat(QtCore.Qt.PlainText)
        self.description.setWordWrap(True)
        self.description.setObjectName(_fromUtf8("description"))
        self.verticalLayout.addWidget(self.description)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.colorBtn = QtGui.QPushButton(Dialog)
        self.colorBtn.setMinimumSize(QtCore.QSize(0, 40))
        self.colorBtn.setMaximumSize(QtCore.QSize(16777215, 40))
        self.colorBtn.setObjectName(_fromUtf8("colorBtn"))
        self.horizontalLayout.addWidget(self.colorBtn)
        #self.colorDisplay = QtGui.QLabel(Dialog)
        self.colorDisplay = ExtendedQLabel(self)
        self.colorDisplay.setMinimumSize(QtCore.QSize(40, 40))
        self.colorDisplay.setMaximumSize(QtCore.QSize(40, 40))
        self.colorDisplay.setFrameShape(QtGui.QFrame.Box)
        self.colorDisplay.setText(_fromUtf8(""))
        self.colorDisplay.setObjectName(_fromUtf8("colorDisplay"))
        self.horizontalLayout.addWidget(self.colorDisplay)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.renderBtn = QtGui.QPushButton(Dialog)
        self.renderBtn.setMinimumSize(QtCore.QSize(300, 100))
        self.renderBtn.setMaximumSize(QtCore.QSize(300, 100))
        self.renderBtn.setObjectName(_fromUtf8("renderBtn"))
        self.horizontalLayout_3.addWidget(self.renderBtn)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.verticalLayout_2 = QtGui.QVBoxLayout()
        self.verticalLayout_2.setContentsMargins(10, -1, -1, -1)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.outputTabs = QtGui.QTabWidget(Dialog)
        self.outputTabs.setObjectName(_fromUtf8("outputTabs"))
        self.tab = QtGui.QWidget()
        self.tab.setObjectName(_fromUtf8("tab"))
        self.gridLayout_2 = QtGui.QGridLayout(self.tab)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.logOutput = QtGui.QTextEdit(self.tab)
        self.logOutput.setObjectName(_fromUtf8("logOutput"))
        self.gridLayout_2.addWidget(self.logOutput, 0, 0, 1, 1)
        self.outputTabs.addTab(self.tab, _fromUtf8(""))
        self.tab_2 = QtGui.QWidget()
        self.tab_2.setObjectName(_fromUtf8("tab_2"))
        self.gridLayout_3 = QtGui.QGridLayout(self.tab_2)
        self.gridLayout_3.setObjectName(_fromUtf8("gridLayout_3"))
        self.imageOutput = QtGui.QLabel(self.tab_2)
        self.imageOutput.setFrameShape(QtGui.QFrame.Box)
        self.imageOutput.setText(_fromUtf8(""))
        self.imageOutput.setObjectName(_fromUtf8("imageOutput"))
        self.gridLayout_3.addWidget(self.imageOutput, 0, 0, 1, 1)
        self.outputTabs.addTab(self.tab_2, _fromUtf8(""))
        self.verticalLayout_2.addWidget(self.outputTabs)
        self.progressBar = QtGui.QProgressBar(Dialog)
        self.progressBar.setMinimumSize(QtCore.QSize(300, 0))
        self.progressBar.setMaximumSize(QtCore.QSize(300, 16777215))
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setProperty("value", 0)
        self.progressBar.setTextVisible(False)
        self.progressBar.setValue(0)
        self.progressBar.setObjectName(_fromUtf8("progressBar"))
        self.verticalLayout.addWidget(self.progressBar)
        self.gridLayout.addLayout(self.verticalLayout_2, 0, 1, 1, 1)

        self.retranslateUi(Dialog)
        self.outputTabs.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

        self.colorBtn.clicked.connect(self.color_picker)
        self.connect(self.colorDisplay, QtCore.SIGNAL('clicked()'), self.color_picker)
        self.renderBtn.clicked.connect(self.renderImage)

        self.show()

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("renderDialogW", "Cinesite test", None))
        self.colorBtn.setText(_translate("Dialog", "Color Picker", None))
        self.renderBtn.setText(_translate("Dialog", "Render", None))
        self.description.setText(_translate("renderDialogW", "The program uses Arnold  python API.\n"
"\n"
"Render a sphere with user-defined color.\n"
"The log file is displayed in the Log Output tab.\n"
"The rendered image is loaded into the Rendered Image tab.", None))
        self.outputTabs.setTabText(self.outputTabs.indexOf(self.tab), _translate("Dialog", "Log Output", None))
        self.outputTabs.setTabText(self.outputTabs.indexOf(self.tab_2), _translate("Dialog", "Rendered Image", None))

    def color_picker(self):
        color = QtGui.QColorDialog.getColor()

        self.red= color.redF()
        self.green= color.greenF()
        self.blue= color.blueF()

        self.colorDisplay.setStyleSheet("QWidget { background-color: %s}" % color.name())


def run():
    app = QtGui.QApplication(sys.argv)
    GUI = cinesiteWindow()
    sys.exit(app.exec_())



run()