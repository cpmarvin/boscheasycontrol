"""Support for EasyControl wifi-enabled thermostats"""
import asyncio
import datetime
import json
import logging
import aiohttp
import ssl
import async_timeout
import voluptuous as vol
import random

from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    SUPPORT_PRESET_MODE,
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
)
from homeassistant.const import (
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    ATTR_TEMPERATURE,
    PRECISION_HALVES,
    CONF_ACCESS_TOKEN,
    CONF_ENTITY_ID,
    CONF_NAME,
)

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from collections import namedtuple
from enum import Enum

_LOGGER = logging.getLogger(__name__)

PRESET_MANUAL = "Manual"  # Enable Manual mode on the thermostat

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ACCESS_TOKEN): cv.string,
        vol.Required(CONF_ENTITY_ID): cv.string,
        vol.Optional(CONF_NAME, default="BOSCH_NEW"): cv.string,
    }
)


class RequestType(Enum):
    GET = 1
    PUT = 2
    POST = 3


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the thermostat."""
    # _LOGGER.warning("This is the config: %s", config)
    access_token = config[CONF_ACCESS_TOKEN]
    entity_id = config[CONF_ENTITY_ID]
    name = config[CONF_NAME]

    easyControl_data_handler = EasyControl(
        entity_id, access_token, websession=async_get_clientsession(hass)
    )

    dev = []
    device_details = await easyControl_data_handler.get_devices()
    dev.append(
        EasyControlDevice(device_details, easyControl_data_handler, name, entity_id)
    )
    async_add_entities(dev)


class EasyControlDevice(ClimateEntity):
    def __init__(self, device_data, easyControl_data_handler, name, entity_id):
        """Initialize the thermostat."""
        self._name = name
        self._device_data = device_data
        self._easyControl_data_handler = easyControl_data_handler
        self._device_id = entity_id

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

    @property
    def unique_id(self):
        """Return a unique ID based on serial number"""
        return self._device_id

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def hvac_action(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        return HVAC_MODE_HEAT

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """

        return HVAC_MODE_HEAT

    @property
    def icon(self):
        return "mdi:radiator"

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return [HVAC_MODE_HEAT]

    @property
    def temperature_unit(self):
        """Return the unit of measurement which this device uses."""
        return TEMP_CELSIUS

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return 5

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return 35

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._device_data["temperature"]

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._device_data["temperatureSet"]

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return PRECISION_HALVES

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        res = {}
        return res

    @property
    def preset_mode(self):
        """Return preset mode."""
        return PRESET_MANUAL

    @property
    def preset_modes(self):
        """Return valid preset modes."""
        return [PRESET_MANUAL]

    async def async_set_hvac_mode(self, hvac_mode):
        """Set hvac mode.
        if hvac_mode == HVAC_MODE_HEAT:
            await self._ebeco_data_handler.set_powerstate(self._device_data["id"], True)
        elif hvac_mode == HVAC_MODE_OFF:
            await self._ebeco_data_handler.set_powerstate(
                self._device_data["id"], False
            )
        else:
            return
        await self._ebeco_data_handler.update(force_update=True)
        """
        return  # todo not implemented

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature.
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self._ebeco_data_handler.set_room_target_temperature(
            self._device_data["id"], temperature, True
        )
        await self._ebeco_data_handler.update(force_update=True)
        """
        return  # todo not implemented

    async def async_set_preset_mode(self, preset_mode):
        """
        await self._ebeco_data_handler.set_preset_mode(
            self._device_data["id"], preset_mode
        )
        await self._ebeco_data_handler.update(force_update=True)
        """
        return  # todo not implemented

    async def async_update(self):
        """Get the latest data.
        for device in await self._ebeco_data_handler.get_devices():
            if device["id"] == self._device_data["id"]:
        """
        self._device_data = await self._easyControl_data_handler.get_devices()
        return


######


class EasyControl:
    """EasyControl data handler."""

    def __init__(self, sensor_id, access_token, websession):
        """Init EasyControl data handler."""

        self._sensor_id = sensor_id
        self.websession = websession
        self._access_token = access_token
        self._authHeader = {"Authorization": f"{self._access_token}"}
        self._devices = {}
        self._last_updated = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
        self._timeout = 10
        self._url = "https://ews-emea.api.bosch.com/home/sandbox/pointt/v1"

    async def get_devices(self):
        """Get devices."""
        await self.update()
        return self._devices

    async def update(self, force_update=False):
        """Update data."""
        now = datetime.datetime.utcnow()
        if (
            now - self._last_updated < datetime.timedelta(seconds=30)
            and not force_update
        ):
            return
        self._last_updated = now
        await self.fetch_user_devices()

    async def set_room_target_temperature(
        self, device_id, temperature, heating_enabled
    ):
        """Set target temperature"""

        json_data = {
            "id": device_id,
            "powerOn": heating_enabled,
            "temperatureSet": temperature,
        }
        await self._request(
            self._url + "/services/app/Devices/UpdateUserDevice",
            RequestType.PUT,
            json_data=json_data,
        )

    async def set_powerstate(self, device_id, heating_enabled):

        json_data = {
            "id": device_id,
            "powerOn": heating_enabled,
        }
        await self._request(
            self._url + "/services/app/Devices/UpdateUserDevice",
            RequestType.PUT,
            json_data=json_data,
        )

    async def set_preset_mode(self, device_id, preset_mode):
        json_data = {
            "id": device_id,
            "selectedProgram": preset_mode,
        }
        await self._request(
            self._url + "/services/app/Devices/UpdateUserDevice",
            RequestType.PUT,
            json_data=json_data,
        )

    async def fetch_user_devices(self):
        """Get user devices"""

        data = f"{self._url}/gateways/{self._sensor_id}/resource/zones/zn1/temperatureActual"
        _LOGGER.warning("This is the url: %s", data)
        response = await self._request(data, RequestType.GET)

        data_target = f"{self._url}/gateways/{self._sensor_id}/resource/zones/zn1/manualTemperatureHeating"
        response_target = await self._request(data_target, RequestType.GET)

        if response is None or response_target is None:
            self._devices["temperature"] = None
            self._devices["temperatureSet"] = None

        else:
            json_data = await response.json()
            json_data_target = await response_target.json()
            self._devices["temperature"] = json_data["value"]
            self._devices["temperatureSet"] = json_data_target["value"]
            _LOGGER.warning("This is the temperatureSet: %s", json_data_target["value"])

    async def _request(self, url, requesttype, json_data=None, retry=3):

        try:
            with async_timeout.timeout(self._timeout):
                if json_data:
                    if requesttype == RequestType.GET:
                        response = await self.websession.get(
                            url, json=json_data, headers=self._authHeader
                        )
                    elif requesttype == RequestType.POST:
                        response = await self.websession.post(
                            url, json=json_data, headers=self._authHeader
                        )
                    else:
                        response = await self.websession.put(
                            url, json=json_data, headers=self._authHeader
                        )

                else:  # If no json_data
                    if requesttype == RequestType.GET:
                        response = await self.websession.get(
                            url, headers=self._authHeader
                        )
                    elif requesttype == RequestType.POST:
                        response = await self.websession.post(
                            url, headers=self._authHeader
                        )
                    else:
                        response = await self.websession.put(
                            url, headers=self._authHeader
                        )

            if response.status != 200:
                self._access_token = None
                if retry > 0:
                    await asyncio.sleep(1)
                    return await self._request(
                        url, requesttype, json_data, retry=retry - 1
                    )
                return None
        except aiohttp.ClientError as err:

            self._access_token = None
            if retry > 0:
                return await self._request(url, requesttype, json_data, retry=retry - 1)
            raise
        except asyncio.TimeoutError:
            self._access_token = None
            if retry > 0:
                return await self._request(url, requesttype, json_data, retry=retry - 1)

            raise
        return response