import logging
from datetime import timedelta

import voluptuous as vol

# Import the device class from the component that you want to support
from homeassistant.components.sensor import DEVICE_CLASS_POWER, PLATFORM_SCHEMA, SensorEntity, STATE_CLASS_MEASUREMENT
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_PASSWORD, POWER_WATT
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

# Home Assistant depends on 3rd party packages for API specific code.
##REQUIREMENTS = ['awesome_lights==1.2.3']

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=15)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default='smappee_overall_consumption'): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
})

class SmappeeGateway():

    def __init__(self, host, password):
        self._host = host
        self._password = password
        self._url = 'http://'+host+'/gateway/apipublic/'
        self._is_valid = None
        self._power_consumption_sum = None
        self._power_consumption_1 = None
        self._power_consumption_2 = None
        self._power_consumption_3 = None
		
        try:
            self.update()
        except:
            raise
     
    @property
    def is_valid(self):
        return self._is_valid
		
    @property
    def power_consumption_sum(self):
        return self._power_consumption_sum
		
    @property
    def power_consumption_1(self):
        return self._power_consumption_1
		
    @property
    def power_consumption_2(self):
        return self._power_consumption_2
		
    @property
    def power_consumption_3(self):
        return self._power_consumption_3
		
    def update(self):
        import requests
        
        for i in range(2):
            try:
                r = requests.post(self._url+'instantaneous', data="loadInstantaneous", timeout=10)
            except:
                self._is_valid = False
                raise Exception('Connection error')

            if r.status_code != requests.codes.ok:
                self._is_valid = False
                raise Exception('Server error')

            if i == 0 and type(r.json()) is dict and r.json()['error']:
                try:
                    self.logon()    
                except:
                    self._is_valid = False
                    raise
            else:
                break
                         
        power_consumption_1 = 0
        power_consumption_2 = 0
        power_consumption_3 = 0
        json_ok = False

        for list_item in r.json():
            if type(list_item) is dict:
                if list_item['key'] == 'phase0ActivePower':
                    power_consumption_1 += int(list_item['value'])
                    json_ok = True
                elif list_item['key'] == 'phase1ActivePower':
                    power_consumption_2 += int(list_item['value'])
                    json_ok = True
                elif list_item['key'] == 'phase2ActivePower':
                    power_consumption_3 += int(list_item['value'])
                    json_ok = True
        
        self._is_valid = json_ok
        if self._is_valid:
            self._power_consumption_1 = int(power_consumption_1 / 1000)
            self._power_consumption_2 = int(power_consumption_2 / 1000)
            self._power_consumption_3 = int(power_consumption_3 / 1000)
            self._power_consumption_sum = self._power_consumption_1 + self._power_consumption_2 + self._power_consumption_3
            
    def logon(self):
        import requests

        try:
            r = requests.post(self._url+'logon', data=self._password, timeout=10)
        except:
            self._is_valid = False
            raise Exception('Connection error')

        if r.status_code != requests.codes.ok:
            self._is_valid = False
            raise Exception('Server error')
        
        try:
            if type(r.json()) is not dict or not r.json()['success']:
                self._is_valid = False
                raise Exception('Login error')    
        except:
            self._is_valid = False
            raise Exception('Login error')    
            
    def logoff(self):
        import requests
        
        try:
            r = requests.post(self._url+'logoff', data="", timeout=10)
        except:
            raise Exception('Connection error')

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Smappee platform."""
##    import smappeegateway

    # Assign configuration variables. The configuration check takes care they are
    # present. 
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    password = config.get(CONF_PASSWORD)

    # Setup connection with devices/cloud
    try:
        gateway = SmappeeGateway(host, password)
    except Exception as ex:
        _LOGGER.error(ex)
        return False

    # Verify that passed in configuration works
    if not gateway.is_valid:
        _LOGGER.error("No valid data received from Smappee")
        return False

    # Add devices
    add_devices([Smappee_Custom(name, gateway, '_sum')], True)
    add_devices([Smappee_Custom(name, gateway, '_phase_1')], True)
    add_devices([Smappee_Custom(name, gateway, '_phase_2')], True)
    add_devices([Smappee_Custom(name, gateway, '_phase_3')], True)



class Smappee_Custom(SensorEntity):

    def __init__(self, name, gateway, phase):
        self._phase = phase
        self._gateway = gateway
        if self._gateway.is_valid:
            if self._phase == '_sum':
                self._attr_state = self._gateway.power_consumption_sum
            elif self._phase == '_phase_1':
                self._attr_state = self._gateway.power_consumption_1
            elif self._phase == '_phase_2':
                self._attr_state = self._gateway.power_consumption_2
            elif self._phase == '_phase_3':
                self._attr_state = self._gateway.power_consumption_3

        self._attr_name = name + phase
        self._attr_unique_id = name + phase
        self._attr_unit_of_measurement = POWER_WATT
        self._attr_state_class = STATE_CLASS_MEASUREMENT
        self._attr_device_class = DEVICE_CLASS_POWER
     
    def update(self):
        """Update state of sensor."""
        try:
            self._gateway.update()
            if self._gateway.is_valid:
                if self._phase == '_sum':
                    self._attr_state = self._gateway.power_consumption_sum
                elif self._phase == '_phase_1':
                    self._attr_state = self._gateway.power_consumption_1
                elif self._phase == '_phase_2':
                    self._attr_state = self._gateway.power_consumption_2
                elif self._phase == '_phase_3':
                    self._attr_state = self._gateway.power_consumption_3
                    
        except Exception as ex:
            _LOGGER.error(ex)
