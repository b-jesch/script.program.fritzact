# -*- coding: utf-8 -*-

# https://raw.githubusercontentoolscom/robwebset/scriptoolssonos/master/defaultoolspy

import os
import xbmcgui

from . import tools

ACTION_LEFT = 1
ACTION_RIGHT = 2
ACTION_SELECT = 7
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

BaseWindow = xbmcgui.WindowXMLDialog


class SliderWindow(BaseWindow):
    LABEL_ID = 10
    SLIDER_ID = 11
    SLIDERVAL_ID = 12

    SLIDERSTEP = 2.5

    def __init__(self, *args, **kwargs):

        self.initValue = None
        self.curValue = None
        self.retValue = None
        self.label = None

    @staticmethod
    def createSliderWindow():
        return SliderWindow('DialogSlider.xml', os.getcwd())

    def onAction(self, action):

        tools.writeLog('Action received: ID %s' % str(action.getId()))
        val = None
        if (action == ACTION_PREVIOUS_MENU) or (action == ACTION_NAV_BACK) or (action == ACTION_SELECT):
            self.close()
        else:
            if action == ACTION_LEFT or ACTION_RIGHT:
                Slider = self.getControl(SliderWindow.SLIDER_ID)
                currentSliderValue = Slider.getPercent()
                if abs(currentSliderValue - self.curValue) < SliderWindow.SLIDERSTEP:
                    if action == ACTION_LEFT and currentSliderValue >= SliderWindow.SLIDERSTEP:
                        val = self.curValue - SliderWindow.SLIDERSTEP
                    elif action == ACTION_RIGHT and currentSliderValue <= 100 - SliderWindow.SLIDERSTEP:
                        val = self.curValue + SliderWindow.SLIDERSTEP
                self.updateSliderWindow(val)

    def onInit(self):
        tools.writeLog('Init slider window')
        self.getControl(SliderWindow.LABEL_ID).setLabel(self.label)
        self.updateSliderWindow(val=self.initValue)

    @classmethod
    def onClick(cls, controlID):
        if controlID == SliderWindow.SLIDER_ID:
            pass

    def close(self):
        BaseWindow.close(self)
        tools.writeLog('Close slider window')

    def updateSliderWindow(self, val=None):

        if val is not None:
            self.getControl(SliderWindow.SLIDER_ID).setPercent(val)
            self.curValue = val
            tools.writeLog('set slider value to %s percent' % (val))

        self.retValue = (self.getControl(SliderWindow.SLIDER_ID).getPercent() * 20.0) / 100 + 8
        self.getControl(SliderWindow.SLIDERVAL_ID).setLabel('{:0.1f}'.format(self.retValue) + ' °C')
