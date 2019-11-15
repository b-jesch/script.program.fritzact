#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Documentation for the login procedure
https://avm.de/fileadmin/user_upload/Global/Service/Schnittstellen/AVM_Technical_Note_-_Session_ID.pdf

Smart Home interface:
https://avm.de/fileadmin/user_upload/Global/Service/Schnittstellen/AHA-HTTP-Interface.pdf
'''

from resources.lib.tools import *

import hashlib
import requests
import resources.lib.slider as Slider

import sys
from time import time
import urllib

import xbmcplugin
from xml.etree import ElementTree as ET
import re

s_on = os.path.join(addonImages, 'dect_on.png')
s_off = os.path.join(addonImages, 'dect_off.png')
s_absent = os.path.join(addonImages, 'dect_absent.png')
t_on = os.path.join(addonImages, 'comet_on.png')
t_absent = os.path.join(addonImages, 'comet_absent.png')
gs_on = os.path.join(addonImages, 'dect_group_on.png')
gs_off = os.path.join(addonImages, 'dect_group_off.png')
gt_on = os.path.join(addonImages, 'comet_group_on.png')
gt_absent = os.path.join(addonImages, 'comet_group_absent.png')
unknown_device = os.path.join(addonImages, 'unknown.png')


class Device():

    def __init__(self, device):

        # Device attributes

        self.actor_id = device.attrib['identifier']
        self.device_id = device.attrib['id']
        self.fwversion = device.attrib['fwversion']
        self.productname = device.attrib['productname']
        self.manufacturer = device.attrib['manufacturer']
        self.functionbitmask = int(device.attrib['functionbitmask'])

        self.name = device.find('name').text
        self.present = int(device.find('present').text or '0')
        self.b_present = 'true' if self.present == 1 else 'false'

        self.is_thermostat = self.functionbitmask & (1 << 6) > 0        # Comet DECT (Radiator Thermostat)
        self.has_powermeter = self.functionbitmask & (1 << 7) > 0       # Energy Sensor
        self.has_temperature = self.functionbitmask & (1 << 8) > 0      # Temperature Sensor
        self.is_switch = self.functionbitmask & (1 << 9) > 0            # Power Switch
        self.is_repeater = self.functionbitmask & (1 << 10) > 0         # DECT Repeater

        self.type = 'n/a'
        self.state = 'n/a'
        self.b_state = 'n/a'
        self.power = 'n/a'
        self.energy = 'n/a'
        self.temperature = 'n/a'
        self.mode = 'n/a'
        self.lock = 'n/a'

        self.unknown = False

        self.set_temp = ['n/a']
        self.comf_temp = ['n/a']
        self.lowering_temp = ['n/a']
        self.bin_slider = 0

        # Switch attributes

        if self.is_switch:
            self.type = 'switch'
            self.state = int(device.find('switch').find('state').text or '0')
            self.b_state = 'true' if self.state == 1 else 'false'
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
                self.power = '{:0.2f}'.format(float(device.find('powermeter').find('power').text)/1000) + ' W'
                self.energy = '{:0.2f}'.format(float(device.find('powermeter').find('energy').text)/1000) + ' kWh'
        except TypeError:
            pass

        # Temperature attributes

        try:
            if self.has_temperature:
                self.temperature = '{:0.1f}'.format(float(device.find("temperature").find("celsius").text)/10) + ' °C'.decode('utf-8')
        except TypeError:
            pass

        _group = re.match('([A-F]|\d){2}:([A-F]|\d){2}:([A-F]|\d){2}-([A-F]|\d){3}', self.actor_id)
        if _group is not None:
            self.type = 'group'

            # ToDo: change back to group ^^

            '''
            self.type = 'thermostat'
            self.temperature = '22.0' + ' °C'.decode('utf-8')
            self.bin_slider = 44
            self.set_temp = self.bin2degree(self.bin_slider)
            '''

        if self.is_repeater:
            self.type = 'switch'

    @classmethod

    def bin2degree(cls, binary_value = 0):
        if 16 <= binary_value <= 56: return '{:0.1f}'.format((binary_value - 16)/2.0 + 8) + ' °C'.decode('utf-8')
        elif binary_value == 253: return ['off']
        elif binary_value == 254: return ['on']
        return ['invalid']


class FritzBox():

    def __init__(self):
        self.getSettings()
        self.base_url = '%s%s' % (self.__fbtls, self.__fbserver)

        self.session = requests.Session()

        if self.__fbSID is None or (int(time()) - self.__lastLogin > 3600):

            writeLog('SID invalid or session expired, try to login')
            sid = "0000000000000000"
            url = '%s%s' % (self.base_url, '/login_sid.lua')

            try:
                response = self.session.get(url, verify=False)
                xml = ET.fromstring(response.text)
                if xml.find('SID').text == "0000000000000000":
                    challenge = xml.find('Challenge').text
                    response = self.session.get(url, params={
                        "username": self.__fbuser,
                        "response": self.calculate_response(challenge, self.__fbpasswd),
                    }, verify=False)
                    xml = ET.fromstring(response.text)
                    if xml.find('SID').text == "0000000000000000":
                        blocktime = int(xml.find('BlockTime').text)
                        writeLog("Login failed, please wait %s seconds" % (blocktime), xbmc.LOGERROR)
                        notifyOSD(addonName, LS(30012) % (blocktime))
                    else:
                        sid = xml.find('SID').text

            except (requests.exceptions.ConnectionError, TypeError):
                writeLog('FritzBox unreachable', level=xbmc.LOGERROR)
                notifyOSD(addonName, LS(30010))

            self.__fbSID = sid
            self.__lastLogin = int(time())
            addon.setSetting('SID', self.__fbSID)
            addon.setSetting('lastLogin', str(self.__lastLogin))

    @classmethod
    def calculate_response(cls, challenge, password):

        # Calculate response for the challenge-response authentication

        to_hash = (challenge + "-" + password).encode("UTF-16LE")
        hashed = hashlib.md5(to_hash).hexdigest()
        return '%s-%s' % (challenge, hashed)

    def getSettings(self):
        self.__fbserver = addon.getSetting('fbServer')
        self.__fbuser = addon.getSetting('fbUsername')
        self.__fbpasswd = crypter('fbPasswd', 'fb_key', 'fb_token')
        self.__fbtls = 'https://' if addon.getSetting('fbTLS').upper() == 'TRUE' else 'http://'
        self.__prefAIN = addon.getSetting('preferredAIN')
        self.__readonlyAIN = addon.getSetting('readonlyAIN').split(',')
        self.__unknownAIN = True if addon.getSetting('unknownAIN').upper() == 'TRUE' else False
        #
        self.__lastLogin = int(addon.getSetting('lastLogin') or 0)
        self.__fbSID = addon.getSetting('SID') or None

    def get_actors(self, handle=None, devtype=None):

        # Returns a list of Actor objects for querying SmartHome devices.

        actors = []
        _devicelist = self.switch('getdevicelistinfos')

        if _devicelist is not None:

            devices = ET.fromstring(_devicelist.encode('utf-8'))

            for device in devices:

                actor = Device(device)

                if (devtype is not None and devtype != actor.type) or actor.actor_id is None: continue

                if actor.is_switch:
                    actor.icon = s_absent
                    if actor.present == 1:
                        actor.icon = gs_on if actor.type == 'group' else s_on
                        if actor.state == 0: actor.icon = gs_off if actor.type == 'group' else s_off
                elif actor.is_thermostat:
                    actor.icon = t_absent
                    if actor.present == 1:
                        actor.icon = gt_on if actor.type == 'group' else t_on
                        if actor.state == 0: actor.icon = gt_absent if actor.type == 'group' else t_absent
                else:
                    actor.unknown = True
                    actor.icon = unknown_device

                if not self.__unknownAIN and  actor.unknown: continue

                actors.append(actor)

                if handle is not None:
                    wid = xbmcgui.ListItem(label=actor.name, label2=actor.actor_id, iconImage=actor.icon)
                    wid.setProperty('type', actor.type)
                    wid.setProperty('present', LS(30032 + actor.present))
                    wid.setProperty('b_present', actor.b_present)
                    if isinstance(actor.state, int):
                        wid.setProperty('state', LS(30030 + actor.state))
                    else:
                        wid.setProperty('state', actor.state)
                    wid.setProperty('b_state', actor.b_state)
                    wid.setProperty('mode', actor.mode)
                    wid.setProperty('temperature', unicode(actor.temperature))
                    wid.setProperty('power', actor.power)
                    wid.setProperty('energy', actor.energy)

                    wid.setProperty('set_temp', unicode(actor.set_temp))
                    wid.setProperty('comf_temp', unicode(actor.comf_temp))
                    wid.setProperty('lowering_temp', unicode(actor.lowering_temp))

                    xbmcplugin.addDirectoryItem(handle=handle, url='', listitem=wid)

                writeLog('<<<<', xbmc.LOGDEBUG)
                writeLog('----- current state of AIN %s -----' % (actor.actor_id))
                writeLog('Name:          %s' % (actor.name))
                writeLog('Type:          %s' % (actor.type))
                writeLog('Presence:      %s' % (actor.present))
                writeLog('Device ID:     %s' % (actor.device_id))
                writeLog('Temperature:   %s' % (actor.temperature))
                writeLog('State:         %s' % (actor.state))
                writeLog('Icon:          %s' % (actor.icon))
                writeLog('Power:         %s' % (actor.power))
                writeLog('Consumption:   %s' % (actor.energy))
                writeLog('soll Temp.:    %s' % (actor.set_temp))
                writeLog('comfort Temp.: %s' % (actor.comf_temp))
                writeLog('lower Temp.:   %s' % (actor.lowering_temp))
                writeLog('>>>>', xbmc.LOGDEBUG)

            if handle is not None:
                xbmcplugin.endOfDirectory(handle=handle, updateListing=True)
            xbmc.executebuiltin('Container.Refresh')

        else:
            writeLog('no device list available', xbmc.LOGDEBUG)
        return actors

    def switch(self, cmd, ain=None, param=None, label=None):

        writeLog('Provided command: %s' % (cmd))
        writeLog('Provided ain:     %s' % (ain))
        writeLog('Provided param:   %s' % (param))
        writeLog('Provided device:  %s' % (label))

        # Call an actor method

        if self.__fbSID is None:
            writeLog('Not logged in or no connection to FritzBox', level=xbmc.LOGERROR)
            return

        params = {
            'switchcmd': cmd,
            'sid': self.__fbSID,
        }
        if ain:

            # check if readonly AIN

            for li in self.__readonlyAIN:
                if ain == li.strip():
                    xbmcgui.Dialog().notification(addonName, LS(30013), xbmcgui.NOTIFICATION_WARNING, 3000)
                    return

            params['ain'] = ain

        if cmd == 'sethkrtsoll':
            slider = Slider.SliderWindow.createSliderWindow()
            slider.label = LS(30035) % (label)
            slider.initValue = (param - 16) * 100 / 40
            slider.doModal()
            slider.close()

            _sliderBin = int(slider.retValue) * 2

            writeLog('Thermostat binary before/now: %s/%s' % (param, _sliderBin))
            del slider

            if param == _sliderBin: return
            else:
                writeLog('set thermostat %s to %s' % (ain, _sliderBin))
                param = str(_sliderBin)

            if param: params['param'] = param

        try:
            response = self.session.get(self.base_url + '/webservices/homeautoswitch.lua', params=params, verify=False)
            response.raise_for_status()
        except (requests.exceptions.HTTPError, TypeError):
            writeLog('Bad request, action could not performed', level=xbmc.LOGERROR)
            xbmcgui.Dialog().notification(addonName, LS(30014), xbmcgui.NOTIFICATION_ERROR, 3000)
            return None

        return response.text.strip()

# _______________________________
#
#           M A I N
# _______________________________

action = None
ain = None
dev_type = None

_addonHandle = None

fritz = FritzBox()

arguments = sys.argv

if len(arguments) > 1:
    if arguments[0][0:6] == 'plugin':
        _addonHandle = int(arguments[1])
        arguments.pop(0)
        arguments[1] = arguments[1][1:]
        writeLog('Refreshing dynamic list content with plugin handle #%s' % (_addonHandle))

    params = paramsToDict(arguments[1])
    action = urllib.unquote_plus(params.get('action', ''))
    ain = urllib.unquote_plus(params.get('ain', ''))
    dev_type = urllib.unquote_plus(params.get('type', ''))

    if dev_type not in ['switch', 'thermostat', 'repeater', 'group']: dev_type = None

    writeLog('Parameter hash: %s' % (arguments[1:]))

actors = fritz.get_actors(handle=_addonHandle, devtype=dev_type)

if _addonHandle is None:

    name = None
    param = None
    cmd = None

    if action == 'toggle':
        cmd = 'setswitchtoggle'

    elif action == 'on':
        cmd = 'setswitchon'

    elif action == 'off':
        cmd = 'setswitchoff'

    elif action == 'temp':
        for device in actors:
            if device.actor_id == ain:
                cmd = 'sethkrtsoll'
                ain = ain
                name = device.name
                param = device.bin_slider
                break

    elif action == 'setpreferredain':
        _devlist = [LS(30006)]
        _ainlist = ['']
        for device in actors:
            if device.type == 'switch':
                _devlist.append(device.name)
                _ainlist.append(device.actor_id)
        if len(_devlist) > 0:
            dialog = xbmcgui.Dialog()
            _idx = dialog.select(LS(30020), _devlist)
            if _idx > -1:
                addon.setSetting('preferredAIN', _ainlist[_idx])

    elif action == 'setreadonlyain':
        _devlist = [LS(30006)]
        _ainlist = ['']
        for device in actors:
            _devlist.append(device.name)
            _ainlist.append(device.actor_id)
        if len(_devlist) > 0:
            dialog = xbmcgui.Dialog()
            _idx = dialog.multiselect(LS(30020), _devlist)
            if _idx is not None:
                addon.setSetting('readonlyAIN', ', '.join([_ainlist[i] for i in _idx]))
    else:
        cmd = 'setswitchtoggle'
        if addon.getSetting('preferredAIN') != '':
            ain =  addon.getSetting('preferredAIN')
        else:
            if len(actors) == 1 and actors[0].is_switch:
                ain = actors[0].actor_id
            else:
                _devlist = []
                _ainlist = []
                for device in actors:
                    '''
                    if device.is_switch:
                        _alternate_state = __LS__(30031) if device.b_state == 'false' else __LS__(30030)
                        _devlist.append('%s: %s' % (device.name, _alternate_state))
                    elif device.is_thermostat:
                        _devlist.append('%s: %s' % (device.name, device.temperature))
                    '''
                    if device.is_switch:
                        L2 = LS(30041) if device.b_state == 'false' else LS(30040)
                    elif device.is_thermostat:
                        L2 = device.temperature
                    liz = xbmcgui.ListItem(label=device.name, label2=L2, iconImage=device.icon)
                    liz.setProperty('ain', device.actor_id)
                    _devlist.append(liz)
                    _ainlist.append(device)

                if len(_devlist) > 0:
                    dialog = xbmcgui.Dialog()
                    _idx = dialog.select(LS(30020), _devlist, useDetails=True)
                    if _idx > -1:
                        device = _ainlist[_idx]
                        ain = device.actor_id

                        if device.is_thermostat:
                            cmd = 'sethkrtsoll'
                            name = device.name
                            param = device.bin_slider
    if cmd is not None:
        fritz.switch(cmd, ain=ain, param=param, label=name)
        writeLog('Last command on device %s was: %s' % (ain, cmd), xbmc.LOGDEBUG)
        ts = int(time())
        tsp = int(xbmcgui.Window(10000).getProperty('fritzact.timestamp') or '0')
        if ts - tsp > 5:
            writeLog('Set timestamp: %s' % (str(ts)), xbmc.LOGDEBUG)
            xbmcgui.Window(10000).setProperty('fritzact.timestamp', str(ts))
