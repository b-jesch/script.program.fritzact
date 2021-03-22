<h1> Fritz!Box SmartHome - Switching Your FritzDECT </h1>
The popular german ADSL device 'Fritz!Box' offers via AHA HTTP API the possibility to control DECT power switches and 
heating thermostats (Comet) on remote. This addon takes advantage of this and controls the switching state of sockets and 
temperature settings of thermostats in Kodi.

All devices can be controlled via a selection list. If only one device is available or if other devices are disabled 
for switching, this device will be switched directly. Same on if a preferred device is specified in the setup.

The addon must be configured via settings menu at first. From OS> 6.50, AVM requires a full authentication (user, password). 
It is recommended that you create an own user and use it for SmartHome. In addition, the communication can be encrypted via TLS.

<h2> Comments on usage and integration into the Confluence Skin </h2>

The addon can be integrated into Confluence as a widget, which resides in the Home menu under in Programs. This makes it
available immediately after the start of Kodi and the actuators can be reached with a few clicks of the remote control. 
However, the integration as a widget requires an integration into the skin. The necessary changes to the skin are described 
in detail in the [Readme.md] (resources/Confluence/Readme.md) folder in the resources/Confluence folder.

For newer skins an integration is possible as a "dynamic list control" widget. To do this, simply implement ```plugin://script.program.fritzact``` 
in your skin setup. Skins must use the "Skinhelper Widget" to do this.


<h2>Extended debugging</h2>

A request to the FritzBox with the parameter `getdevicelistinfos` creates a response with the following XML (example).
This is what You'll see if exended logging is enabled. Additional, all your devices with detailed Properties are listed.
You have to switch on the debug logging of your system. All Properties are written to the widget too (see below). 

 
```
<devicelist version="1">
    <device identifier="08761 0287125" id="16" 
        functionbitmask="896" fwversion="03.37" manufacturer="AVM"
        productname="FRITZ!DECT 200">
        <present>1</present>
        <name>Steckdose Wohnzimmer (Lampe)</name>
        <switch>
            <state>1</state>
            <mode>manuell</mode>
            <lock>0</lock>
        </switch>
        <powermeter>
            <power>0</power>
            <energy>26</energy>
        </powermeter>
        <temperature>
            <celsius>240</celsius>
            <offset>0</offset>
        </temperature>
     </device>
     <!-- nächstes Gerät nach dem gleichen Schema -->
     <device identifier="...">...</device>
</devicelist>
```

```
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] <<<<
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] ----- current state of AIN 14080 0076856 -----
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] Name:          Heizung Küche
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] Type:          thermostat
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] Presence:      1
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] Device ID:     17
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] Temperature:   20.0 °C
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] State:         n/a
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] Icon:          /home/jesch/.kodi/addons/script.program.fritzact/resources/lib/media/comet_on.png
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] Power:         n/a
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] Consumption:   n/a
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] soll Temp.:    17.0 °C
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] comfort Temp.: 21.0 °C
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] lower Temp.:   17.0 °C
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] Battery:       100%
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] Battery low:   0
2021-03-18 11:35:00.021 T:7223    DEBUG <general>: [script.program.fritzact 3.0.0+matrix.1] >>>>
```
    
Further informations (AVM): https://avm.de/fileadmin/user_upload/Global/Service/Schnittstellen/AHA-HTTP-Interface.pdf

<h2>Widget properties</h2>

    ListItem.Label                      Name of actuator
    ListItem.Label2                     AIN
    ListItem.Icon                       Picture of state of the actuator (offline/an/aus)
    ListItem.Property(type)             Type of actuator (switch/thermostat/repeater/group)
    ListItem.Property(present)          Device offline/online
    ListItem.Property(state)            Switch on/off
    ListItem.Property(mode)             Device mode auto/manual
    ListItem.Property(temperature)      Temperature of sensor (Celsius)
    ListItem.Property(power)            Power consumption in 0.01 W
    ListItem.Property(energy)           Consumption since start-up (Wh)
    ListItem.Property(battery)          State of Battery in %
    ListItem.Property(batterylow)       Battery change flag (0 oder 1)
    
<h3>Additional properties of thermostats</h3>

    ListItem.Property(set_temp)         Target temperature
    ListItem.Property(comf_temp)        Comfort temperature (Heating temperature)
    ListItem.Property(lowering_temp)    Lowering temperature

<h2>Methoden/Aufruf</h2>

<h3>Actuator toggling</h3>

```
<onclick>RunScript(script.program.fritzact,action=toggle&amp;ain=$INFO[ListItem.Label2])</onclick>
```

If you want to integrate a button within a skin to switch an actuator directly, you can also do this by specifying the 
AIN (here e.g. 08150 1234567) of the actuator concerned. The AIN of the actuator can be found in the web interface of 
the Fritzbox in the Smarthome area:

```
<control type='button'>
<label>Garage</label>
<onclick>RunScript(script.program.fritzact,action=toggle&amp;ain='08150 1234567')</onclick>
</control>
```

Set actuator on:

```
<onclick>RunScript(script.program.fritzact,action=on&amp;ain=$INFO[ListItem.Label2])</onclick>
```

Set actuator off:

```
<onclick>RunScript(script.program.fritzact,action=off&amp;ain=$INFO[ListItem.Label2])</onclick>
```

Set thermostat:

```
<onclick>RunScript(script.program.fritzact,action=temp&amp;ain=$INFO[ListItem.Label2])</onclick>
```

<h3>Call for dynamic list content</h3>

```
<content target="programs">plugin://script.program.fritzact?ts=$INFO[Window(Home).Property(fritzact.timestamp)]</content>
```

If you only want to display a certain group (switch, thermostat, group), you can set the dynamic List Content 
with the corresponding group via the parameter 'type'. A repeater is classified as a switch.

```
<content target="programs">plugin://script.program.fritzact?ts=$INFO[Window(Home).Property(fritzact.timestamp)]&amp;devtype=switch</content>
```
<h3>Further Informations</h3>

Including the add-on in the skin as a programme add-on toggles the preferred actuator (see Settings), i.e. in the case of several 
installations, the actuators that make sense for the installation can be switched (e.g. Kodi in the living room: preferred 
actuator is an actuator in the living room, Kodi in children's room: preferred actuator is an actuator in the children's room, etc.). 
If no preferred AIN is set in the add-on setup and there is more than one actuator in the Smarthome, a list of all available 
actuators appears from which one can be selected for switching.
