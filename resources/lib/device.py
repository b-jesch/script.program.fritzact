import xbmc
import xbmcaddon
import os
import re

addon = xbmcaddon.Addon()
addonPath = xbmc.translatePath(addon.getAddonInfo('path'))
addonImages = os.path.join(xbmc.translatePath(addonPath), 'resources', 'lib', 'media')

s_on = os.path.join(addonImages, 'dect_on.png')
s_off = os.path.join(addonImages, 'dect_off.png')
s_absent = os.path.join(addonImages, 'dect_absent.png')
t_on = os.path.join(addonImages, 'comet_on.png')
t_absent = os.path.join(addonImages, 'comet_absent.png')
t_lowbatt = os.path.join(addonImages, 'comet_lowbatt.png')
gs_on = os.path.join(addonImages, 'dect_group_on.png')
gs_off = os.path.join(addonImages, 'dect_group_off.png')
gt_on = os.path.join(addonImages, 'comet_group_on.png')
gt_absent = os.path.join(addonImages, 'comet_group_absent.png')
unknown_device = os.path.join(addonImages, 'unknown.png')


class Device:

    def __init__(self, device):

        '''
        Funktionsbitmasken

        Bit 0: HANFUN Gerät
        Bit 4: Alarm-Sensor
        Bit 6: Heizkörperregler
        Bit 7: Energie Messgerät
        Bit 8: Temperatursensor
        Bit 9: Schaltsteckdose
        Bit 10: AVM DECT Repeater
        Bit 11: Mikrofon
        Bit 13: HANFUN Unit
        '''

        isHanFun = 0b00000000000001
        isAlert = 0b00000000010000
        isThermostat = 0b00000001000000
        isPowerMeter = 0b00000010000000
        isTempSensor = 0b00000100000000
        isPwrSwitch = 0b00001000000000
        isRepeater = 0b00010000000001
        isMicrophone = 0b00100000000000
        isHanFunUnit = 0b10000000000000

        # Device attributes

        self.ain = device.attrib['identifier']
        self.device_id = device.attrib['id']
        self.fwversion = device.attrib['fwversion']
        self.productname = device.attrib['productname']
        self.manufacturer = device.attrib['manufacturer']
        self.functionbitmask = int(device.attrib['functionbitmask'])

        self.name = device.find('name').text
        self.present = int(device.find('present').text or '0')

        self.is_thermostat = bool(self.functionbitmask & isThermostat)  # Comet DECT (Radiator Thermostat)
        self.has_powermeter = bool(self.functionbitmask & isPowerMeter)  # Energy Sensor
        self.has_temperature = bool(self.functionbitmask & isTempSensor)  # Temperature Sensor
        self.is_switch = bool(self.functionbitmask & isPwrSwitch)  # Power Switch
        self.is_repeater = bool(self.functionbitmask & isRepeater)  # DECT Repeater

        self.type = 'n/a'
        self.state = 'n/a'
        self.power = 'n/a'
        self.energy = 'n/a'
        self.temperature = 'n/a'
        self.mode = 'n/a'
        self.lock = 'n/a'
        self.battery = 'n/a' if device.find('battery') is None else device.find('battery').text + '%'
        self.batterylow = 0 if device.find('batterylow') is None else int(device.find('batterylow').text)

        self.unknown = False

        self.set_temp = 'n/a'
        self.comf_temp = 'n/a'
        self.lowering_temp = 'n/a'
        self.bin_slider = 0

        self.icon = unknown_device

        # Switch attributes

        if self.is_switch:
            self.type = 'switch'
            self.state = int(device.find('switch').find('state').text or '0')
            self.mode = device.find('switch').find('mode').text
            self.lock = int(device.find('switch').find('lock').text or '0')

        if self.is_thermostat:
            self.type = 'thermostat'
            self.set_temp = self.bin2degree(int(device.find('hkr').find('tsoll').text or '0'))
            self.comf_temp = self.bin2degree(int(device.find('hkr').find('komfort').text or '0'))
            self.lowering_temp = self.bin2degree(int(device.find('hkr').find('absenk').text or '0'))

            # get temp for slider value

            self.bin_slider = int(device.find('hkr').find('tsoll').text or '0')

        # Power attributes

        try:
            if self.has_powermeter:
                self.power = '{:0.2f}'.format(float(device.find('powermeter').find('power').text) / 1000) + ' W'
                self.energy = '{:0.2f}'.format(float(device.find('powermeter').find('energy').text) / 1000) + ' kWh'
        except TypeError:
            pass

        # Temperature attributes

        try:
            if self.has_temperature:
                self.temperature = '{:0.1f}'.format(float(device.find("temperature").find("celsius").text) / 10) + ' °C'
        except TypeError:
            pass

        _group = re.match('([A-F]|[0-9]){2}:([A-F]|[0-9]){2}:([A-F]|[0-9]){2}-([A-F]|[0-9]){3}', self.ain)
        if _group is not None:
            self.type = 'group'

        if self.is_repeater:
            self.type = 'switch'

        # Icons

        if self.is_switch:
            self.icon = s_absent
            if self.present == 1:
                self.icon = gs_on if self.type == 'group' else s_on
                if self.state == 0: self.icon = gs_off if self.type == 'group' else s_off
        elif self.is_thermostat:
            self.icon = t_absent
            if self.present == 1:
                if self.type == 'group':
                    self.icon = gt_on
                else:
                    if self.batterylow == 1:
                        self.icon = t_lowbatt
                    else:
                        self.icon = t_on
        else:
            self.unknown = True
            self.icon = unknown_device

    @classmethod
    def bin2degree(cls, binary_value=0):
        if 16 <= binary_value <= 56:
            return '{:0.1f}'.format((binary_value - 16) / 2.0 + 8) + ' °C'
        elif binary_value == 253: return '[off]'
        elif binary_value == 254: return '[max]'
        return 'n/a'
