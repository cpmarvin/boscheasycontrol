# boscheasycontrol
EasyControl Thermostat integration with HomeAssistant

Based on [ EBECO ] (https://github.com/joggs/home_assistant_ebeco)

Custom component for using [Bosch EasyControl ](https://www.bosch-easycontrol.com/gb/en/easycontrol/overview/) thermostats in Home Assistant.


## Install
Use [hacs](https://hacs.xyz/) or copy the files to the custom_components folder in Home Assistant config.
Please see below , this is a POC only

In configuration.yaml:

```
climate:
  - platform: boscheasycontrol
    access_token: "Bearer XXXXX"
    entity_id: "<SERIAL_NR>"
    name: "ROOM1"

```

API details: https://developer.bosch.com/web/bosch-thermotechnology-device-api/overview

You will need an developer account to register your device. For now the access_token is only available while you are log into their website. Hopefuly in the future this will change. 
