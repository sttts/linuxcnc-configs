import os
import hal as linuxcnchal
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QSpinBox, qApp

import linuxcnc
from dataclasses import dataclass, field, fields


from qtpy import uic
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget

from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities import logger
from qtpyvcp import hal
import qtpyvcp

LOG = logger.getLogger(__name__)

STATUS = getPlugin('status')
TOOL_TABLE = getPlugin('tooltable')
NOTIFICIATIONS = getPlugin('notifications')
INI_FILE = linuxcnc.ini(os.getenv('INI_FILE_NAME'))

@dataclass
class HalPins:
    SAFE_Z: float = field(metadata={"pin": 'safe_z', "type": "float", "dir": "out"}, default=0.0)
    Z_IR_ENGAGE: float = field(metadata={"pin": 'z_ir_engage', "type": "float", "dir": "out"}, default=0.0)
    POCKETS: int = field(metadata={"pin": 'num_pockets', "type": "s32", "dir": "out"}, default=6)
    POCKET_OFFSET: float = field(metadata={"pin": 'pocket_offset', "type": "float", "dir": "out"}, default=0.0)
    FIRST_POCKET_X: float = field(metadata={"pin": 'first_pocket_x', "type": "float", "dir": "out"}, default=0.0)
    FIRST_POCKET_Y: float = field(metadata={"pin": 'first_pocket_y', "type": "float", "dir": "out"}, default=0.0)
    ENGAGE_Z: float = field(metadata={"pin": 'engage_z', "type": "float", "dir": "out"}, default=0.0)
    ALIGN_AXIS: bool = field(metadata={"pin": 'align_axis', "type": "bit", "dir": "out"}, default=False)
    ALIGN_DIR: int = field(metadata={"pin": 'align_dir', "type": "s32", "dir": "out"}, default=0)
    IR_HAL_DPIN: int = field(metadata={"pin": 'ir_hal_dpin', "type": "s32", "dir": "out"}, default=0)
    COVER_HAL_DPIN: int = field(metadata={"pin": 'cover_hal_dpin', "type": "s32", "dir": "in"}, default=0)
    ENGAGE_FEED_RATE: int = field(metadata={"pin": 'engage_feed_rate', "type": "s32", "dir": "out"}, default=10)
    DROP_RATE: int = field(metadata={"pin": 'drop_feed_rate', "type": "s32", "dir": "out"}, default=100)
    PICKUP_RATE: int = field(metadata={"pin": 'pickup_feed_rate', "type": "s32", "dir": "out"}, default=100)
    SPINDLE_SPEED: int = field(metadata={"pin": 'spindle_speed', "type": "s32", "dir": "out"}, default=1000)
    X_MANUAL_CHANGE_POS: float = field(metadata={"pin": 'x_manual_change_pos', "type": "float", "dir": "out"}, default=0.0)
    Y_MANUAL_CHANGE_POS: float = field(metadata={"pin": 'y_manual_change_pos', "type": "float", "dir": "out"}, default=0.0)
    CURRENT_TOOL_POCKET: int = field(metadata={"pin": 'current_tool_pocket', "type": "s32", "dir": "out"}, default=0)
    IR_ENABLED: bool = field(metadata={"pin": 'ir_enabled', "type": "bit", "dir": "out"}, default=False)
    COVER_ENABLED: bool = field(metadata={"pin": 'cover_enabled', "type": "bit", "dir": "out"}, default=False)
    DUST_COVER_STATE: bool = field(metadata={"pin": 'dust_cover_state', "type": "bit", "dir": "in"}, default=False)

    signals = {}
    pins = {}
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
                    v = int(v)
                elif t == "bit":
                    v = v in ["1", "True", "true"]
                else:
                    raise ValueError(f"Unknown type {t}")
                super.__setattr__(self, f.name, v)

            self.comp.addPin(f.metadata["pin"], f.metadata["type"], f.metadata["dir"])
            self.pins[f.name] = f.metadata["pin"]
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
            self.comp.getPin(self.pins[name]).value = value


class UserTab(QWidget):
    def __init__(self, parent=None):
        super(UserTab, self).__init__(parent)
        ui_file = os.path.splitext(os.path.basename(__file__))[0] + ".ui"
        uic.loadUi(os.path.join(os.path.dirname(__file__), ui_file), self)

        # create pins
        self.pins = HalPins()
        LOG.info(f"Pins: {self.pins}")
        LOG.info(f"Fields: {self}")

        # connect pins
        self.numPockets.setValue(self.pins.POCKETS)
        # pins.signal("POCKETS").connect(self.numPockets.setValue)
        self.numPockets.valueChanged.connect(lambda w: setattr(self.pins, "POCKETS", self.numPockets.value()))

        self.irEnabled.setChecked(self.pins.IR_ENABLED)
        self.irEnabled.toggled.connect(lambda w: setattr(self.pins, "IR_ENABLED", self.irEnabled.isChecked()))

        self.saveIniButton.clicked.connect(self.saveIniFile)

        # connect IR LED
        LOG.info(f"din = {STATUS.stat.din}")
        self.irTimer = QTimer()
        self.irTimer.timeout.connect(self.__updateIR)
        self.irTimer.setInterval(100)
        self.irTimer.start()

        # hook into atc widget for tool updates
        QTimer.singleShot(1, self.__connectDynATC)

    def __connectDynATC(self):
        try:
            dynATC = self.__getWidget("dynatc")
            dynATC.showToolSig.connect(self.__storeTool)
            dynATC.hideToolSig.connect(self.__hideTool)
        except:
            LOG.info(f"Error connecting to dynatc, trying again")
            QTimer.singleShot(1, self.__connectDynATC)

    def __updateIR(self):
        try:
            if self.pins.IR_ENABLED:
                self.irLED.setEnabled(True)
                self.irLED.setColor(QColor(0,255,0) if (STATUS.stat.din[self.pins.IR_HAL_DPIN] == 1) else QColor("red"))
            else:
                self.irLED.setEnabled(False)
        except Exception as e:
            LOG.error(f"Error updating IR: {e}")
            self.irLED.setEnabled(False)
            # NOTIFICIATIONS.error_message(f"Error updating IR: {e}")

    def __storeTool(self, pocket, tool):
        try:
            pocket=int(pocket)
            tool=int(tool)
            LOG.info(f"Storing tool {tool} in pocket {pocket}")
            self.__getattribute__(f"p{pocket}").setText(f"T{tool}")
        except Exception as e:
            LOG.error(f"Error storing tool: {e}")
            # NOTIFICIATIONS.error_message(f"Error storing tool: {e}")

    def __hideTool(self, pocket):
        try:
            pocket=int(pocket)
            LOG.info(f"Hiding tool in pocket {pocket}")
            self.__getattribute__(f"p{pocket}").setText("empty")
        except Exception as e:
            LOG.error(f"Error hiding tool: {e}")
            # NOTIFICIATIONS.error_message(f"Error hiding tool: {e}")

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

    def __getWidget(self, name):
        """Searches for a widget by name in the application windows.

        Args:
            name (str) : ObjectName of the widget.

        Returns: QWidget
        """
        LOG.info(f"Getting widget {name} from {qtpyvcp.WINDOWS.items()}")
        for win_name, obj in list(qtpyvcp.WINDOWS.items()):
            if hasattr(obj, name):
                return getattr(obj, name)

        raise AttributeError("Could not find widget with name: %s" % name)