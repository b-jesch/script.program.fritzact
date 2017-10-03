<h1>Fritz!Box SmartHome - Switching Your FritzDECT</h1>
<h2>Anmerkungen zur Verwendung und Integration in den Confluence Skin</h2>

Die FritzBox bietet über die sogenannte AHA-HTTP-API, die Möglichkeit, DECT Steckdosen und Heizungsthermostaten (Comet) fernzuschalten. Dieses Addon nutzt diese Möglichkeit und stellt u.a. den Schaltzustand der Steckdosen und Thermostate in Kodi dar.

Das Addon ist als Widget konzipiert, welches im Home unter dem Punkt Programme abgelegt wird. Damit steht es unmittelbar nach dem Start von Kodi zur Verfügung und die Steckdosen sind mit wenigen Aktionen der Fernbedienung erreichbar.

Dazu muss es allerdings zunächst in den Einstellungen konfiguriert werden. AVM verlangt ab OS > 6.50 eine full qualified Authentication (Nutzer, Passwort). Es empfiehlt sich, für Smart Home einen eigenen Nutzer anzulegen und hier zu verwenden (Sniffing).

Zum Einbinden in den Confluence sind einige Änderungen am Skin erforderlich. Diese sind in der [Readme.md](resources/Confluence/Readme.md) im Ordner resources/Confluence nochmal genau beschrieben.

Ansonsten lässt sich in den Settings des Addons ein bevorzugtes Gerät angeben, welches beim Aufruf des Addons den Status wechselt (toggelt).
