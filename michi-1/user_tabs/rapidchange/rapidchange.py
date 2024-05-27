import os
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import qApp

import linuxcnc
from dataclasses import fields, dataclass, field

from qtpy import uic
from qtpy.QtWidgets import QWidget

from qtpyvcp import hal
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities import logger
import qtpyvcp

LOG = logger.getLogger(__name__)

STATUS = getPlugin('status')
TOOL_TABLE = getPlugin('tooltable')
NOTIFICIATIONS = getPlugin('notifications')
INI_FILE = linuxcnc.ini(os.getenv('INI_FILE_NAME'))


class UserTab(QWidget):
    def __init__(self, parent=None):
        super(UserTab, self).__init__(parent)
        ui_file = os.path.splitext(os.path.basename(__file__))[0] + ".ui"
        uic.loadUi(os.path.join(os.path.dirname(__file__), ui_file), self)

        # create pins
        self.pins = HalPins()
        LOG.info(f"Pins: {self.pins}")
        LOG.info(f"Fields: {self}")

        # connect pins to widgets
        self.safeZ.setValue(self.pins.SAFE_Z)
        self.safeZ.valueChanged.connect(lambda w: setattr(self.pins, "SAFE_Z", self.safeZ.value()))

        self.zIREngage.setValue(self.pins.Z_IR_ENGAGE)
        self.zIREngage.setEnabled(self.pins.IR_ENABLED)
        self.zIREngage.valueChanged.connect(lambda w: setattr(self.pins, "Z_IR_ENGAGE", self.zIREngage.value()))

        self.numPockets.setValue(self.pins.NUM_POCKETS)
        # pins.signal("NUM_POCKETS").connect(self.numPockets.setValue)
        self.numPockets.valueChanged.connect(lambda w: setattr(self.pins, "NUM_POCKETS", self.numPockets.value()))

        self.pocketOffset.setValue(self.pins.POCKET_OFFSET)
        self.pocketOffset.valueChanged.connect(lambda w: setattr(self.pins, "POCKET_OFFSET", self.pocketOffset.value()))

        self.firstPocketX.setValue(self.pins.FIRST_POCKET_X)
        self.firstPocketX.valueChanged.connect(lambda w: setattr(self.pins, "FIRST_POCKET_X", self.firstPocketX.value()))

        self.firstPocketY.setValue(self.pins.FIRST_POCKET_Y)
        self.firstPocketY.valueChanged.connect(lambda w: setattr(self.pins, "FIRST_POCKET_Y", self.firstPocketY.value()))

        self.engageZ.setValue(self.pins.ENGAGE_Z)
        self.engageZ.valueChanged.connect(lambda w: setattr(self.pins, "ENGAGE_Z", self.engageZ.value()))

        self.alignAxis.addItem("X")
        self.alignAxis.addItem("Y")
        self.alignAxis.setCurrentIndex(1 if self.pins.ALIGN_AXIS else 0)
        self.alignAxis.currentIndexChanged.connect(lambda w: setattr(self.pins, "ALIGN_AXIS", True if self.alignAxis.currentIndex() == 1 else False))

        self.alignDir.setChecked(self.pins.ALIGN_DIR == 1)
        self.alignDir.toggled.connect(lambda w: setattr(self.pins, "ALIGN_DIR", 1 if self.alignDir.isChecked() else -1))

        self.irHalDPin.setValue(self.pins.IR_HAL_DPIN)
        self.irHalDPin.setEnabled(self.pins.IR_ENABLED)
        self.irHalDPin.valueChanged.connect(lambda w: setattr(self.pins, "IR_HAL_DPIN", self.irHalDPin.value()))

        self.coverHalDPin.setValue(self.pins.COVER_HAL_DPIN)
        self.coverHalDPin.setEnabled(self.pins.COVER_ENABLED)
        self.coverHalDPin.valueChanged.connect(lambda w: setattr(self.pins, "COVER_HAL_DPIN", self.coverHalDPin.value()))

        self.engageFeedRate.setValue(self.pins.ENGAGE_FEED_RATE)
        self.engageFeedRate.valueChanged.connect(lambda w: setattr(self.pins, "ENGAGE_FEED_RATE", self.engageFeedRate.value()))

        self.dropRate.setValue(self.pins.DROP_RATE)
        self.dropRate.valueChanged.connect(lambda w: setattr(self.pins, "DROP_RATE", self.dropRate.value()))

        self.pickupRate.setValue(self.pins.PICKUP_RATE)
        self.pickupRate.valueChanged.connect(lambda w: setattr(self.pins, "PICKUP_RATE", self.pickupRate.value()))

        self.spindleSpeedDrop.setValue(self.pins.SPINDLE_SPEED_DROP)
        self.spindleSpeedDrop.valueChanged.connect(lambda w: setattr(self.pins, "SPINDLE_SPEED_DROP", self.spindleSpeedDrop.value()))

        self.spindleSpeedPickup.setValue(self.pins.SPINDLE_SPEED_PICKUP)
        self.spindleSpeedPickup.valueChanged.connect(lambda w: setattr(self.pins, "SPINDLE_SPEED_PICKUP", self.spindleSpeedPickup.value()))

        self.xManualChangePos.setValue(self.pins.X_MANUAL_CHANGE_POS)
        self.xManualChangePos.valueChanged.connect(lambda w: setattr(self.pins, "X_MANUAL_CHANGE_POS", self.xManualChangePos.value()))

        self.yManualChangePos.setValue(self.pins.Y_MANUAL_CHANGE_POS)
        self.yManualChangePos.valueChanged.connect(lambda w: setattr(self.pins, "Y_MANUAL_CHANGE_POS", self.yManualChangePos.value()))

        self.irEnabled.setChecked(self.pins.IR_ENABLED)
        self.irEnabled.setLedState(self.irEnabled.isChecked())
        self.irEnabled.toggled.connect(lambda w: self.irEnabled.setLedState(self.irEnabled.isChecked()))
        self.irEnabled.toggled.connect(lambda w: self.irHalDPin.setEnabled(self.irEnabled.isChecked()))
        self.irEnabled.toggled.connect(lambda w: self.zIREngage.setEnabled(self.irEnabled.isChecked()))
        self.irEnabled.toggled.connect(lambda w: setattr(self.pins, "IR_ENABLED", self.irEnabled.isChecked()))

        self.coverEnabled.setChecked(self.pins.COVER_ENABLED)
        self.coverEnabled.toggled.connect(lambda w: self.coverHalDPin.setEnabled(self.coverEnabled.isChecked()))
        self.coverEnabled.toggled.connect(lambda w: setattr(self.pins, "COVER_ENABLED", self.coverEnabled.isChecked()))

        self.currentToolPocket.setText(str(self.pins.CURRENT_TOOL_POCKET))
        self.currentToolPocket.textChanged.connect(lambda w: setattr(self.pins, "CURRENT_TOOL_POCKET", int(self.currentToolPocket.text())))
        # self.pins.signal("CURRENT_TOOL_POCKET").connect(lambda p: self.currentToolPocket.setText(str(p)))

        self.saveIniButton.clicked.connect(self.saveIniFile)

        # connect IR LED
        LOG.info(f"din = {STATUS.stat.din}")
        self.irTimer = QTimer()
        self.irTimer.timeout.connect(self.__updateIR)
        self.irTimer.setInterval(100)
        self.irTimer.start()

        # update pockets
        self.updatePocketsTimer = QTimer()
        self.updatePocketsTimer.timeout.connect(self.__updatePockets)
        self.updatePocketsTimer.setInterval(500)
        self.updatePocketsTimer.start()

        # make our widgets accessible through the mainwindow such that the subcall button find them
        self.t = QTimer()
        self.t.setSingleShot(True)
        self.t.setInterval(0)
        self.t.timeout.connect(self.__addWidgetsToMainWindow)
        self.t.start()

    def __addWidgetsToMainWindow(self):
        rootWidget = self.parent()
        while rootWidget.parent() is not None:
            rootWidget = rootWidget.parent()
        for w in self.findChildren(QWidget):
            rootWidget.__setattr__(w.objectName(), w)

    def __updatePockets(self):
        occupied = {}
        tbl = TOOL_TABLE.getToolTable()
        foundCurrent = False
        for n in tbl:
            if n == 0:
                continue
            tool = tbl[n]
            # LOG.info(f"Tool: {n}:{tool}")
            try:
                if tool['P'] != 0 and tool['P'] <= self.pins.NUM_POCKETS:
                    label = self.__getattribute__(f"p{tool['P']}")
                    label.setText(f"T{tool['T']}")
                    occupied[tool['P']] = tool['T']
                    if str(STATUS.tool_in_spindle) == str(tool['T']):
                        self.currentToolPocket.setText(str(tool['P']))
                        foundCurrent = True
            except Exception as e:
                LOG.error(f"Error updating pocket {tool}: {e}")
                # NOTIFICIATIONS.error_message(f"Error updating pocket {tool.P}: {e}")
        if not foundCurrent:
            self.currentToolPocket.setText("0")
        for pocket in range(1, self.pins.NUM_POCKETS + 1):
            if pocket not in occupied:
                label = self.__getattribute__(f"p{pocket}")
                label.setText("empty")

    def __updateIR(self):
        try:
            if self.pins.IR_ENABLED:
                self.irLED.setEnabled(True)
                on = (STATUS.stat.din[self.pins.IR_HAL_DPIN] == 1)
                self.irEnabled.setLedColor(QColor(0,255,0) if on else QColor("red"))
                self.irLED.setColor(QColor(0,255,0) if on else QColor("red"))
            else:
                self.irLED.setEnabled(False)
        except Exception as e:
            LOG.error(f"Error updating IR: {e}")
            self.irLED.setEnabled(False)
            # NOTIFICIATIONS.error_message(f"Error updating IR: {e}")

    def saveIniFile(self):
        try:
            with open("atc.ini.new", "w") as f:
                # write [ATC] header
                f.write("[ATC]\n")
                # write the pin values
                for fld in fields(HalPins):
                    v = getattr(self.pins, fld.name)
                    f.write(f"{fld.name}={v}\n")
                os.rename("atc.ini.new", "atc.ini")
                LOG.info("Saved atc.ini file")
                # NOTIFICIATIONS.info_message("Saved atc.ini file")
        except Exception as e:
            LOG.error(f"Error saving ini file: {e}")
            # NOTIFICIATIONS.error_message(f"Error saving ini file: {e}")

@dataclass
class HalPins:
    SAFE_Z: float = field(metadata={"pin": 'safe_z', "type": "float", "dir": "out"}, default=0.0)
    Z_IR_ENGAGE: float = field(metadata={"pin": 'z_ir_engage', "type": "float", "dir": "out"}, default=0.0)
    NUM_POCKETS: int = field(metadata={"pin": 'num_pockets', "type": "s32", "dir": "out"}, default=6)
    POCKET_OFFSET: float = field(metadata={"pin": 'pocket_offset', "type": "float", "dir": "out"}, default=0.0)
    FIRST_POCKET_X: float = field(metadata={"pin": 'first_pocket_x', "type": "float", "dir": "out"}, default=0.0)
    FIRST_POCKET_Y: float = field(metadata={"pin": 'first_pocket_y', "type": "float", "dir": "out"}, default=0.0)
    ENGAGE_Z: float = field(metadata={"pin": 'engage_z', "type": "float", "dir": "out"}, default=0.0)
    ALIGN_AXIS: bool = field(metadata={"pin": 'align_axis', "type": "bit", "dir": "out"}, default=False)
    ALIGN_DIR: int = field(metadata={"pin": 'align_dir', "type": "s32", "dir": "out"}, default=1)
    IR_HAL_DPIN: int = field(metadata={"pin": 'ir_hal_dpin', "type": "s32", "dir": "out"}, default=0)
    COVER_HAL_DPIN: int = field(metadata={"pin": 'cover_hal_dpin', "type": "s32", "dir": "in"}, default=0)
    ENGAGE_FEED_RATE: int = field(metadata={"pin": 'engage_feed_rate', "type": "s32", "dir": "out"}, default=10)
    DROP_RATE: int = field(metadata={"pin": 'drop_feed_rate', "type": "s32", "dir": "out"}, default=100)
    PICKUP_RATE: int = field(metadata={"pin": 'pickup_feed_rate', "type": "s32", "dir": "out"}, default=100)
    SPINDLE_SPEED_DROP: int = field(metadata={"pin": 'spindle_speed_drop', "type": "s32", "dir": "out"}, default=1000)
    SPINDLE_SPEED_PICKUP: int = field(metadata={"pin": 'spindle_speed_pickup', "type": "s32", "dir": "out"}, default=1000)
    X_MANUAL_CHANGE_POS: float = field(metadata={"pin": 'x_manual_change_pos', "type": "float", "dir": "out"}, default=0.0)
    Y_MANUAL_CHANGE_POS: float = field(metadata={"pin": 'y_manual_change_pos', "type": "float", "dir": "out"}, default=0.0)
    CURRENT_TOOL_POCKET: int = field(metadata={"pin": 'current_tool_pocket', "type": "s32", "dir": "out"}, default=0)
    IR_ENABLED: bool = field(metadata={"pin": 'ir_enabled', "type": "bit", "dir": "out"}, default=False)
    COVER_ENABLED: bool = field(metadata={"pin": 'cover_enabled', "type": "bit", "dir": "out"}, default=False)
    DUST_COVER_STATE: bool = field(metadata={"pin": 'dust_cover_state', "type": "bit", "dir": "in"}, default=False)

    signals = {}
    pinsByName = {}
    comp = hal.getComponent("rapid_atc")

    def __init__(self):
        LOG.info("Creating rapidchange component")

        for f in fields(HalPins):
            t = f.metadata["type"]
            v = INI_FILE.find("ATC", f.name)
            if v is not None:
                if t == "float":
                    v = float(v)
                elif t == "s32":
                    v = int(float(v))
                elif t == "bit":
                    v = v in ["1", "True", "true"]
                else:
                    raise ValueError(f"Unknown type {t}")
                super.__setattr__(self, f.name, v)

            self.comp.addPin(f.metadata["pin"], f.metadata["type"], f.metadata["dir"])
            self.pinsByName[f.name] = f.metadata["pin"]
            LOG.info(f"Added rapidchange pin {f.metadata['pin']} of type {f.metadata['type']} and direction {f.metadata['dir']}")

            if f.metadata["dir"] == "in":
                if f.metadata["type"] == "bit":
                    self.signals[f.name] = pyqtSignal(bool)
                elif f.metadata["type"] == "s32":
                    self.signals[f.name] = pyqtSignal(int)
                elif f.metadata["type"] == "float":
                    self.signals[f.name] = pyqtSignal(float)
                else:
                    raise ValueError(f"Unknown type {f.metadata['type']}")
                self.comp.addListener(f.metadata["pin"], lambda v: setattr(self, f.name, v))
            else:
                self.comp.getPin(f.metadata["pin"]).value = getattr(self, f.name)

        self.comp.ready()
        LOG.info("Rapidchange component ready")

    def signal(self, name):
        return self.signals[name]

    def pin(self, name):
        return self.comp.getPin(name)

    def __setattr__(self, name, value):
        old = getattr(self, name)
        if old == value:
            return
        super().__setattr__(name, value)
        if name in self.signals:
            self.signals[name].emit(value)
        else:
            self.comp.getPin(self.pinsByName[name]).value = value
