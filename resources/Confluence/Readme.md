<h1>Informations of this site are outdated!</h1>

<h2>Fritz!Box SmartHome - Switching Your FritzDECT</h2>
<h3>Anmerkungen zur Integration in den Confluence Skin</h3>

Das Plugin ist als Widget konzipiert, welches im Home unter dem Punkt Programme abgelegt wird. Damit steht es unmittelbar nach dem Start von Kodi zur Verfügung und die Steckdosen sind mit wenigen Aktionen der Fernbedienung erreichbar.

Dazu muss es allerdings zunächst in den Einstellungen konfiguriert werden. AVM verlangt ab OS > 5.50 eine komplette Anmeldung (Nutzer, Passwort). Es empfiehlt sich, für Smart Home einen eigenen Nutzer + Passwort anzulegen und hier zu verwenden.

Zum Einbinden in den Confluence sind einige Änderungen am Skin erforderlich.

* Kopieren des Widgets in den Confluence Skin:

```
cd /usr/share/kodi/addons/skin.confluence/720p
```
bis Kodi Jarvis (V16.x):
```
sudo cp $HOME/.kodi/addons/script.program.fritzact/resources/Confluence/script-fritzact.v16.xml script-fritzact.xml
```
Ab Kodi Krypton wird als Standardskin Estuary/Estouchy verwendet. Confluence muss aus einem Repository installiert werden, die Dateien liegen daher im Addon-Verzeichnis der Installation:
```
cd $HOME/.kodi/addons/skin.confluence/720p
cp $HOME/.kodi/addons/script.program.fritzact/resources/Confluence/script-fritzact.v17.xml script-fritzact.xml
```

* Einbinden der XML-Datei als Include in den Home-Bereich (Jarvis)

```
sudo nano includes.xml
```
bzw. Krypton:
```
nano Includes.xml
```
und unterhalb der Zeile `<include file="IncludesHomeRecentlyAdded.xml" />` folgendes einfügen:

    <include file="script-fritzact.xml" />
    
* Das Include im Hauptfenster anmelden

```
sudo nano IncludesHomeRecentlyAdded.xml
```

  und innerhalb der ControlGroup mit der ID 9003 folgenden Eintrag (als neue Zeile) hinzufügen:
   
```
<include>SmartHome</include>
```
   
   Beispiel:
   
```
<?xml version="1.0" encoding="UTF-8"?>
<includes>
  <include name="HomeRecentlyAddedInfo">
      <control type="group" id="9003">
          <include>SmartHome</include>
          <onup>20</onup>
          ...
```
