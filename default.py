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

        isHanFun     = 0b00000000000001
        isAlert      = 0b00000000010000
        isThermostat = 0b00000001000000
        isPowerMeter = 0b00000010000000
        isTempSensor = 0b00000100000000
        isPwrSwitch  = 0b00001000000000
        isRepeater   = 0b00010000000001
        isMicrophone = 0b00100000000000
        isHanFunUnit = 0b10000000000000

        # Device attributes

        self.actor_id = device.attrib['identifier']
        self.device_id = device.attrib['id']
        self.fwversion = device.attrib['fwversion']
        self.productname = device.attrib['productname']
        self.manufacturer = device.attrib['manufacturer']
        self.functionbitmask = int(device.attrib['functionbitmask'])

        self.name = device.find('name').text
        self.present = int(device.find('present').text or '0')

        self.is_thermostat = bool(self.functionbitmask & isThermostat)        # Comet DECT (Radiator Thermostat)
        self.has_powermeter = bool(self.functionbitmask & isPowerMeter)       # Energy Sensor
        self.has_temperature = bool(self.functionbitmask & isTempSensor)      # Temperature Sensor
        self.is_switch = bool(self.functionbitmask & isPwrSwitch)             # Power Switch
        self.is_repeater = bool(self.functionbitmask & isRepeater)            # DECT Repeater

        self.type = 'n/a'
        self.state = 'n/a'
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

        _group = re.match('([A-F]|[0-9]){2}:([A-F]|[0-9]){2}:([A-F]|[0-9]){2}-([A-F]|[0-9]){3}', self.actor_id)
        if _group is not None:
            self.type = 'group'

        if self.is_repeater:
            self.type = 'switch'

    @classmethod

    def bin2degree(cls, binary_value = 0):
        if 16 <= binary_value <= 56: return '{:0.1f}'.format((binary_value - 16)/2.0 + 8) + ' °C'.decode('utf-8')
        elif binary_value == 253: return ['off']
        elif binary_value == 254: return ['on']
        return ['invalid']


class FritzBox():

    def FbBadRequestException(self, e):
        writeLog('Bad request or server error: %s' % e)
        notifyOSD(addonName, LS(30011), xbmcgui.NOTIFICATION_ERROR, time=3000)

    def __init__(self):
        self.getSettings()
        self.base_url = '%s%s' % (self.__fbtls, self.__fbserver)
        self.rights = None
        self.established = False

        self.INVALID = '0000000000000000'
        self.login_url = '/login_sid.lua'

        url = '%s%s' % (self.base_url, self.login_url)
        self.session = requests.Session()
        try:
            sid, challenge = self.getFbSID(url, self.__fbSID)
            if sid == self.INVALID:
                writeLog('SID invalid or session expired, make challenge')
                sid, blocktime = self.makeChallenge(url, challenge, self.__fbuser, self.__fbpasswd)
                if sid == self.INVALID and blocktime > 0:
                        writeLog("Login blocked, please wait %s seconds" % (blocktime), xbmc.LOGERROR)
                        notifyOSD(addonName, LS(30012) % blocktime)
                else:
                    writeLog('new SID: %s' % sid)
                    self.established = True
            elif sid == self.__fbSID:
                writeLog('Validation Ok')
                self.established = True
            self.__fbSID = sid
            addon.setSetting('SID', self.__fbSID)

        except UnicodeDecodeError:
            writeLog('UnicodeDecodeError, special chars not allowed in password challenge', level=xbmc.LOGERROR)
            notifyOSD(addonName, LS(30016), icon=xbmcgui.NOTIFICATION_ERROR)
            sys.exit()
        except (requests.exceptions.ConnectionError, TypeError):
            writeLog('FritzBox unreachable', level=xbmc.LOGERROR)
            notifyOSD(addonName, LS(30010))

    def getFbSID(self, url, sid=None, timeout=5):
        writeLog('Connecting to %s' % url)
        if sid is None or sid == self.INVALID:
            response = self.session.get(url, timeout=timeout, verify=False)
        else:
            writeLog('Validate SID %s' % sid)
            response = self.session.get(url, params={'sid': sid}, timeout=timeout, verify=False)

        if response.status_code != 200: raise self.FbBadRequestException(response.status_code)

        xml = ET.fromstring(response.text)
        return (xml.find('SID').text, xml.find('Challenge').text)

    def makeChallenge(self, url, challenge, fbuser, fbpasswd, timeout=5):
        login_challenge = (challenge + '-' + fbpasswd).encode('utf-16le')
        login_hash = hashlib.md5(login_challenge).hexdigest()
        response = self.session.get(url, params={'username': fbuser, 'response': challenge + '-' + login_hash}, timeout=timeout)

        if response.status_code != 200: raise self.FbBadRequestException(response.status_code)

        xml = ET.fromstring(response.text)
        return (xml.find('SID').text, int(xml.find('BlockTime').text))

    def getFbUserRights(self, xml):

        # get user permissions
        if not self.established: return None
        rl = list()
        al = list()
        rights = xml.find('Rights')
        names = rights.findall('Name')
        access = rights.findall('Access')
        for name in names: rl.append(name.text)
        for acc in access: al.append(acc.text)
        writeLog(str(self.rights))
        return dict(zip(rl, al))

    def getSettings(self):
        self.__fbserver = addon.getSetting('fbServer')
        self.__fbuser = addon.getSetting('fbUsername')
        self.__fbpasswd = crypter('fbPasswd', 'fb_key', 'fb_token')
        self.__fbtls = 'https://' if addon.getSetting('fbTLS').upper() == 'TRUE' else 'http://'
        self.__prefAIN = addon.getSetting('preferredAIN')
        self.__readonlyAIN = addon.getSetting('readonlyAIN').split(',')
        self.__unknownAIN = True if addon.getSetting('unknownAIN').upper() == 'TRUE' else False
        self.__fbSID = addon.getSetting('SID') or None

    def get_actors(self, handle=None, devtype=None):

        # Returns a list of Actor objects for querying SmartHome devices.

        actors = list()
        _devicelist = self.switch('getdevicelistinfos')

        if _devicelist is not None:
            # print _devicelist.encode('utf-8')
            devices = ET.fromstring(_devicelist.encode('utf-8'))
            if len(list(devices)) > 0:
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
                        wid = xbmcgui.ListItem(label=actor.name, label2=actor.actor_id)
                        wid.setArt({'icon': actor.icon})
                        wid.setProperty('type', actor.type)
                        wid.setProperty('present', LS(30032 + actor.present))
                        if isinstance(actor.state, int):
                            wid.setProperty('state', LS(30030 + actor.state))
                        else:
                            wid.setProperty('state', str(actor.state))
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
                notifyOSD(addonName, LS(30015))
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
                    notifyOSD(addonName, LS(30013), xbmcgui.NOTIFICATION_WARNING, time=3000)
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
            response = self.session.get(self.base_url + '/webservices/homeautoswitch.lua', params=params, verify=False, timeout=5)
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, TypeError), e:
            writeLog('Bad request or timed out', level=xbmc.LOGERROR)
            writeLog(str(e), level=xbmc.LOGERROR)
            notifyOSD(addonName, LS(30014), xbmcgui.NOTIFICATION_ERROR, time=3000)
            return None

        return response.text.strip()

# _______________________________
#
#           M A I N
# _______________________________

action = ''
ain = ''
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
    action = urllib.unquote_plus(params.get('action', action))
    ain = urllib.unquote_plus(params.get('ain', ain))
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
                name = device.name
                param = device.bin_slider
                break

    elif action == 'setpreferredain':
        _devlist = list()
        liz = xbmcgui.ListItem(label=LS(3006))
        liz.setProperty('ain', '')
        _devlist.append(liz)

        for device in actors:
            if device.type == 'switch':
                liz = xbmcgui.ListItem(label=device.name, label2=device.actor_id)
                liz.setProperty('ain', device.actor_id)
                _devlist.append(liz)

        dialog = xbmcgui.Dialog()
        _idx = dialog.select(LS(30020), _devlist)
        if _idx > -1:
            addon.setSetting('preferredAIN', _devlist[_idx].getProperty('ain'))

    elif action == 'setreadonlyain':
        _devlist = list()
        liz = xbmcgui.ListItem(label=LS(30006))
        liz.setProperty('ain', '')
        _devlist.append(liz)

        for device in actors:
            liz = xbmcgui.ListItem(label=device.name, label2=device.actor_id)
            liz.setProperty('ain', device.actor_id)
            _devlist.append(liz)

        dialog = xbmcgui.Dialog()
        _idx = dialog.multiselect(LS(30020), _devlist)
        if _idx is not None:
            addon.setSetting('readonlyAIN', ', '.join([_devlist[i].getProperty('ain') for i in _idx]))
    else:
        cmd = 'setswitchtoggle'
        if addon.getSetting('preferredAIN') != '':
            ain =  addon.getSetting('preferredAIN')
        else:
            if len(actors) == 1 and actors[0].is_switch:
                ain = actors[0].actor_id
            else:
                _devlist = list()
                for device in actors:
                    if device.is_switch:
                        L2 = LS(30041) if device.state == 0 else LS(30040)
                    elif device.is_thermostat:
                        L2 = device.temperature
                    else:
                        writeLog('skip device type with bitmask {0:013b}'.format(device.functionbitmask))
                        continue

                    liz = xbmcgui.ListItem(label=device.name, label2=L2, iconImage=device.icon)
                    liz.setProperty('ain', device.actor_id)
                    liz.setProperty('name', device.name)
                    liz.setProperty('type', device.type)
                    liz.setProperty('slider', str(device.bin_slider))
                    _devlist.append(liz)

                if len(_devlist) > 0:
                    dialog = xbmcgui.Dialog()
                    _idx = dialog.select(LS(30020), _devlist, useDetails=True)
                    if _idx > -1:
                        ain = _devlist[_idx].getProperty('ain')
                        name = _devlist[_idx].getProperty('name')
                        type = _devlist[_idx].getProperty('type')
                        slider = int(_devlist[_idx].getProperty('slider'))

                        if type == 'thermostat':
                            cmd = 'sethkrtsoll'
                            param = slider
                    else:
                        cmd = None
                else:
                    cmd = None

    if cmd is not None:
        fritz.switch(cmd, ain=ain, param=param, label=name)
        writeLog('Last command on device %s was: %s' % (ain, cmd), xbmc.LOGDEBUG)
        ts = int(time())
        tsp = int(xbmcgui.Window(10000).getProperty('fritzact.timestamp') or '0')
        if ts - tsp > 5:
            writeLog('Set timestamp: %s' % (str(ts)), xbmc.LOGDEBUG)
            xbmcgui.Window(10000).setProperty('fritzact.timestamp', str(ts))
