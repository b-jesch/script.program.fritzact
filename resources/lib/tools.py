#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcaddon
import os
import random
import urllib

addon = xbmcaddon.Addon()
addonID = addon.getAddonInfo('id')
addonVersion = addon.getAddonInfo('version')
addonPath = xbmc.translatePath(addon.getAddonInfo('path'))
addonName = addon.getAddonInfo('name')
addonImages = os.path.join(xbmc.translatePath(addonPath), 'resources', 'lib', 'media')
LS = addon.getLocalizedString
IconDefault = os.path.join(addonPath, 'resources', 'lib', 'media', 'default.png')


# de-/encrypt passwords, simple algorithm, but prevent for sniffers and script kiddies

def crypter(pw, key, token):
    _pw = addon.getSetting(pw)
    if _pw == '' or _pw == '*':
        _key = addon.getSetting(key)
        _token = addon.getSetting(token)
        if len(_key) > 2: return "".join([chr(ord(_token[i]) ^ ord(_key[i])) for i in range(int(_key[-2:]))])
        return ''
    else:
        _key = ''
        for d in range((len(pw) / 16) + 1):
            _key += ('%016d' % int(random.random() * 10 ** 16))
        _key = _key[:-2] + ('%02d' % len(_pw))
        _tpw = _pw.ljust(len(_key), 'a')
        _token = "".join([chr(ord(_tpw[i]) ^ ord(_key[i])) for i in range(len(_key))])

        addon.setSetting(key, _key)
        addon.setSetting(token, _token)
        addon.setSetting(pw, '*')

        return _pw

# get parameter hash, convert into parameter/value pairs, return dictionary

def paramsToDict(parameters):
    paramDict = dict()
    if parameters:
        paramPairs = parameters.split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = paramSplits[1]
    return paramDict

# write log messages

def writeLog(message, level=xbmc.LOGDEBUG):
    try:
        xbmc.log('[%s %s] %s' % (addonID, addonVersion, message.encode('utf-8')), level)
    except UnicodeDecodeError:
        xbmc.log('[%s %s] %s' % (addonID, addonVersion, message), level)

# OSD notification (DialogKaiToast)

def notifyOSD(header, message, icon=IconDefault, time=5000):
    xbmcgui.Dialog().notification(header.encode('utf-8'), message.encode('utf-8'), icon, time)