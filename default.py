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
from resources.lib.device import Device

import sys
from time import time

import xbmcplugin
from xml.etree import ElementTree
from xml.dom import minidom
from urllib.parse import unquote_plus, urlencode, parse_qsl

fbserver = addon.getSetting('fbServer')
fbuser = addon.getSetting('fbUsername')
fbpasswd = crypter('fbPasswd', 'fb_key', 'fb_token')
fbtls = 'https://' if addon.getSetting('fbTLS').upper() == 'TRUE' else 'http://'
prefAIN = addon.getSetting('preferredAIN')
readonlyAIN = [item.strip() for item in addon.getSetting('readonlyAIN').split(',')]
unknownAIN = True if addon.getSetting('unknownAIN').upper() == 'TRUE' else False
fbsid = addon.getSetting('SID') or None
enableExtLog = True if addon.getSetting('enableExtendedLogging').upper() == 'TRUE' else False
widgetAction = int(addon.getSetting('widgetAction'))


def prettify(xml):
    try:
        reparse = minidom.parseString(xml)
        return reparse.toprettyxml(indent='    ')
    except AttributeError as e:
        writeLog(e, xbmc.LOGERROR)
        return False


def get_url(url, **kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.
    """
    return '{0}?{1}'.format(url, urlencode(kwargs))


def build_devlist(params):
    _devlist = list()
    liz = xbmcgui.ListItem(label=LS(30006))
    liz.setProperty('ain', '')
    _devlist.append(liz)

    for device in actors:
        if device.type == 'switch':
            liz = xbmcgui.ListItem(label=device.name, label2=device.ain)
            liz.setProperty('ain', device.ain)
            _devlist.append(liz)
    dialog = xbmcgui.Dialog()
    if params.get('multiselect', 'false') == 'true':
        _idx = dialog.multiselect(LS(30037), _devlist)
        if _idx is not None:
            addon.setSetting(params['action'], ', '.join([_devlist[i].getProperty('ain') for i in _idx]))
    else:
        _idx = dialog.select(LS(30020), _devlist)
        if _idx > -1:
            addon.setSetting(params['action'], _devlist[_idx].getProperty('ain'))


def build_notificationlabel(device, info=True):
    if device.is_switch:
        if info:
            L2 = '{} {}'.format(LS(30023),  LS(30030) if device.state == 0 else LS(30031))
        else:
            L2 = LS(30041) if device.state == 0 else LS(30040)
    elif device.is_thermostat:
        L2 = '{} / {}'.format(device.temperature, device.set_temp)
    else:
        writeLog('skip device type with bitmask {0:013b}'.format(device.functionbitmask))
        return None

    if device.battery != 'n/a':
        if device.batterylow == 0:
            L2 += LS(30042) % device.battery
        else:
            L2 += LS(30043) % device.battery
    return L2


def show_info(params):
    device = next((item for item in actors if item.ain == params['ain']), None)
    L2 = build_notificationlabel(device, info=True)
    if L2 is None: L2 = 'unkown'
    notifyOSD(device.name, L2, icon=device.icon)


def build_widget(params):
    if params.get('handle', None) is not None:
        writeLog('build/refresh widget with handle #%s' % params['handle'])
        for actor in actors:
            wid = xbmcgui.ListItem(label='%s' % actor.name,
                                   label2=actor.ain)
            wid.setArt({'icon': actor.icon})
            wid.setProperty('type', actor.type)
            wid.setProperty('present', LS(30032 + actor.present))
            if isinstance(actor.state, int):
                wid.setProperty('state', LS(30030 + actor.state))
            else:
                wid.setProperty('state', str(actor.state))
            wid.setProperty('mode', actor.mode)
            wid.setProperty('temperature', actor.temperature)
            wid.setProperty('power', actor.power)
            wid.setProperty('energy', actor.energy)
            wid.setProperty('set_temp', actor.set_temp)
            wid.setProperty('comf_temp', actor.comf_temp)
            wid.setProperty('lowering_temp', actor.lowering_temp)
            wid.setProperty('battery', actor.battery)
            wid.setProperty('batterylow', str(actor.batterylow))

            action = 'info'
            if widgetAction == 1:
                if actor.type == 'thermostat': action = 'temp'
                else: action = 'toggle'

            wid.setProperty('IsPlayable', 'false')
            url = get_url(params.get('url', ''), action=action, ain=actor.ain)
            xbmcplugin.addDirectoryItem(handle=params['handle'], url=url, listitem=wid)

            if enableExtLog:
                writeLog('<<<<')
                writeLog('----- current state of AIN %s -----' % actor.ain)
                writeLog('Name:          %s' % actor.name)
                writeLog('Type:          %s' % actor.type)
                writeLog('Presence:      %s' % actor.present)
                writeLog('Device ID:     %s' % actor.device_id)
                writeLog('Temperature:   %s' % actor.temperature)
                writeLog('State:         %s' % actor.state)
                writeLog('Icon:          %s' % actor.icon)
                writeLog('Power:         %s' % actor.power)
                writeLog('Consumption:   %s' % actor.energy)
                writeLog('soll Temp.:    %s' % actor.set_temp)
                writeLog('comfort Temp.: %s' % actor.comf_temp)
                writeLog('lower Temp.:   %s' % actor.lowering_temp)
                writeLog('Battery:       %s' % actor.battery)
                writeLog('Battery low:   %s' % actor.batterylow)
                writeLog('>>>>')

        xbmcplugin.endOfDirectory(handle=params['handle'], updateListing=True)


class FritzBox:

    class FbInvalidChallengeException(Exception):
        pass

    class FbBadRequestException(Exception):
        pass

    def __init__(self):
        self.base_url = '%s%s' % (fbtls, fbserver)
        self.rights = None
        self.established = False

        self.SID = fbsid
        self.INVALID = '0000000000000000'
        self.login_url = '/login_sid.lua'
        blocktime = 0

        url = '%s%s' % (self.base_url, self.login_url)
        self.session = requests.Session()
        try:
            sid, challenge = self.getFbSID(url, self.SID)
            if sid == self.INVALID:
                writeLog('SID invalid or session expired, make challenge')
                sid, blocktime = self.makeChallenge(url, challenge, fbuser, fbpasswd)
                if sid == self.INVALID and blocktime > 0:
                    raise self.FbInvalidChallengeException()
                else:
                    writeLog('new SID: %s' % sid)
                    self.established = True
            elif sid == fbsid:
                writeLog('Validation Ok')
                self.established = True
            self.SID = sid
            addon.setSetting('SID', self.SID)
            return

        except UnicodeDecodeError:
            writeLog('UnicodeDecodeError, special chars not allowed in password challenge', level=xbmc.LOGERROR)
            notifyOSD(addonName, LS(30016), icon=xbmcgui.NOTIFICATION_ERROR)
        except (requests.exceptions.ConnectionError, TypeError):
            writeLog('FritzBox unreachable', level=xbmc.LOGERROR)
            notifyOSD(addonName, LS(30010))
        except self.FbInvalidChallengeException:
            writeLog("Login blocked for %s seconds" % blocktime, xbmc.LOGERROR)
            notifyOSD(addonName, LS(30012) % blocktime)
        exit()

    def resetFbSession(self, params):
        writeLog('Reset Session ID')
        addon.setSetting('SID', self.INVALID)
        exit()

    def getFbSID(self, url, sid=None, timeout=5):
        writeLog('Connecting to %s' % url)
        if sid is None or sid == self.INVALID:
            response = self.session.get(url, timeout=timeout, verify=False)
        else:
            writeLog('Validate SID %s' % sid)
            response = self.session.get(url, params={'sid': sid}, timeout=timeout, verify=False)

        response.raise_for_status()
        try:
            xml = ElementTree.fromstring(response.text)
            return xml.find('SID').text, xml.find('Challenge').text
        except requests.RequestException as e:
            writeLog('Bad request or server error: %s - %s' % (response.status_code, e.response))
            notifyOSD(addonName, LS(30011), xbmcgui.NOTIFICATION_ERROR, time=3000)
        exit()

    def makeChallenge(self, url, challenge, fbuser, fbpasswd, timeout=5):
        login_challenge = (challenge + '-' + fbpasswd).encode('utf-16le')
        login_hash = hashlib.md5(login_challenge).hexdigest()
        response = self.session.get(url, params={'username': fbuser, 'response': challenge + '-' + login_hash}, timeout=timeout)
        response.raise_for_status()
        try:
            xml = ElementTree.fromstring(response.text)
            return xml.find('SID').text, int(xml.find('BlockTime').text)
        except requests.RequestException as e:
            writeLog('Bad request or server error: %s - %s' % (response.status_code, e.response))
            notifyOSD(addonName, LS(30011), xbmcgui.NOTIFICATION_ERROR, time=3000)
        exit()

    def sendCommand(self, params):

        if self.SID is None:
            writeLog('Not logged in or no connection to FritzBox', level=xbmc.LOGERROR)
            return None

        params.update({'sid': self.SID})
        try:
            response = self.session.get(self.base_url + '/webservices/homeautoswitch.lua',
                                        params=params, verify=False, timeout=5)
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, TypeError) as e:
            writeLog('Bad request or timed out', level=xbmc.LOGERROR)
            writeLog(str(e), level=xbmc.LOGERROR)
            notifyOSD(addonName, LS(30014), xbmcgui.NOTIFICATION_ERROR, time=3000)
            return None

        xbmcgui.Window(10000).setProperty('fritzact.timestamp', str(round(int(time()), -1)))
        return response.text.strip()

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

    def get_actors(self, params=dict({})):

        # Returns a list of Actor objects for querying SmartHome devices.
        actors = list()
        fbParams = dict({'switchcmd': 'getdevicelistinfos'})

        _devicelist = self.sendCommand(fbParams)
        if _devicelist is not None:

            if enableExtLog: writeLog(prettify(_devicelist))

            devices = ElementTree.fromstring(_devicelist.encode('utf-8'))
            if len(list(devices)) > 0:
                for device in devices:

                    actor = Device(device)
                    if (params.get('devtype', None) is not None and
                        params['devtype'] != actor.type) or actor.ain is None: continue
                    if not unknownAIN and actor.unknown: continue
                    actors.append(actor)
            else:
                writeLog('no device list available', xbmc.LOGDEBUG)
                notifyOSD(addonName, LS(30015))

        writeLog('Infos of %s devices collected' % len(actors))
        return actors

    def exec(self, params):

        fbDict = dict({'on': 'setswitchon', 'off': 'setswitchoff', 'toggle': 'setswitchtoggle', 'temp': 'sethkrtsoll'})
        fbParams = dict({'switchcmd': fbDict.get(params['action']), 'ain': params['ain']})

        # check if readonly AIN
        if params['ain'] in readonlyAIN:
            notifyOSD(addonName, LS(30013), xbmcgui.NOTIFICATION_WARNING, time=3000)
            return

        if params['action'] == 'temp':
            if params.get('param', None) is None:
                actor = next((item for item in actors if item.ain == params['ain']), None)
                params.update({'param': actor.bin_slider, 'label': actor.name})

            slider = Slider.SliderWindow.createSliderWindow()
            slider.label = LS(30035) % params.get('label', '[unknown]')
            slider.initValue = (params['param'] - 16) * 100 / 40
            slider.doModal()
            slider.close()

            _sliderBin = int(slider.retValue) * 2
            del slider

            if params['param'] == _sliderBin: return
            else:
                fbParams.update({'param': str(_sliderBin)})

        return self.sendCommand(fbParams)

# _______________________________
#
#           M A I N
# _______________________________


fritz = FritzBox()
args = sys.argv

if len(args) > 1:
    params = dict()

    if args[0][0:6] == 'plugin':
        params.update({'url': args[0], 'handle': int(args[1])})
        args.pop(0)
        args[1] = args[1][1:]

    params.update(dict(parse_qsl(args[1])))
    writeLog('Parameters: %s' % params)

    actors = fritz.get_actors(params)

    actionDict = dict(
        {'reset_session': fritz.resetFbSession,
         'info': show_info,
         'toggle': fritz.exec,
         'on': fritz.exec,
         'off': fritz.exec,
         'temp': fritz.exec,
         'preferredAIN': build_devlist,
         'readonlyAIN': build_devlist,
         'default': build_widget
         }
    )
    actionDict.get(params.get('action', 'default'))(params)

else:

    actors = fritz.get_actors()
    if addon.getSetting('preferredAIN') != '':
        ain = addon.getSetting('preferredAIN')
    elif len(actors) == 1 and actors[0].is_switch:
        ain = actors[0].ain
    else:
        _devlist = list()
        for device in actors:
            L2 = build_notificationlabel(device, info=False)
            if L2 is None: continue

            liz = xbmcgui.ListItem(label=device.name, label2=L2)
            liz.setArt({'icon': device.icon})
            liz.setProperty('ain', device.ain)
            liz.setProperty('name', device.name)
            liz.setProperty('type', device.type)
            if device.type == 'switch':
                liz.setProperty('action', 'toggle')
            elif device.type == 'thermostat':
                liz.setProperty('action', 'temp')
                liz.setProperty('slider', str(device.bin_slider))
            _devlist.append(liz)

        if len(_devlist) > 0:
            dialog = xbmcgui.Dialog()
            _idx = dialog.select(LS(30038), _devlist, useDetails=True)
            if _idx > -1:
                params = dict(
                    {'action': _devlist[_idx].getProperty('action'),
                     'ain': _devlist[_idx].getProperty('ain'),
                     'label': _devlist[_idx].getProperty('name'),
                     'devtype': _devlist[_idx].getProperty('type')
                     }
                )
                if _devlist[_idx].getProperty('type') == 'thermostat':
                    params.update({'param': int(_devlist[_idx].getProperty('slider'))})
                fritz.exec(params)
