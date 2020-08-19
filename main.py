##################################################
import network
import time
from umqtt.robust import MQTTClient
import os
import sys
import _thread
import machine
from machine import Pin
from machine import ADC
from math import log
import math
import ssd1306
from machine import I2C, Pin


# definition of the reference temperature
reference_temp = 18
current_temp = 0
p12 = machine.Pin(12)
cooling_pump = machine.PWM(p12)
intensity_av = 0
concentration = 8000
Thread_website = False
Offline = True
Thread_cooling = False
Thread_feeding = False

def website():
    
    global Thread_website
    # WiFi connection information
    WIFI_SSID = 'iPhone'
    WIFI_PASSWORD = 'qwerty123'
    
    # the following function is the callback which is 
    # called when subscribed data is received
    def cb(topic, msg):
        print("Topic: " + str(topic))
        if topic == b'DB4_Group_1/feeds/target_temp':
            rf(topic, msg)
        else:
            ac(topic, msg)
    def rf(topic, msg):
        global reference_temp
        print('Received Data:  Topic = {}, Msg = {}'.format(topic, msg))
        reference_temp = float(str(msg,'utf-8'))
        print('Reference temperature = {} degrees Celsius'.format(reference_temp))
        
    def ac(topic, msg):
        global concentration
        print('Received Data:  Topic = {}, Msg = {}'.format(topic, msg))
        concentration = float(str(msg,'utf-8'))
        print('Concentration = {} cells'.format(concentration))
    
    # turn off the WiFi Access Point
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(False)
    
    # connect the device to the WiFi network
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect(WIFI_SSID, WIFI_PASSWORD)
    
    # wait until the device is connected to the WiFi network
    MAX_ATTEMPTS = 20
    attempt_count = 0
    while not wifi.isconnected() and attempt_count < MAX_ATTEMPTS:
        attempt_count += 1
        time.sleep(1)
    
    if attempt_count == MAX_ATTEMPTS:
        print('could not connect to the WiFi network')
     #   sys.exit()
    
    # create a random MQTT clientID 
    random_num = int.from_bytes(os.urandom(3), 'little')
    mqtt_client_id = bytes('client_'+str(random_num), 'utf-8')
    
    # connect to Adafruit IO MQTT broker using unsecure TCP (port 1883)
    # 
    # To use a secure connection (encrypted) with TLS: 
    #   set MQTTClient initializer parameter to "ssl=True"
    #   Caveat: a secure connection uses about 9k bytes of the heap
    #         (about 1/4 of the micropython heap on the ESP8266 platform)
    ADAFRUIT_IO_URL = b'io.adafruit.com' 
    ADAFRUIT_USERNAME = b'DB4_Group_1'
    ADAFRUIT_IO_KEY = b'aio_GSaI01qTs88BI3goMvHRjADB7mkP'
    
    ADAFRUIT_IO_TEMP = b'target_temp'
    ADAFRUIT_IO_TEMP_CHART = b'temp_measurements'
    ADAFRUIT_IO_MOTOR_FREQ = b'motor_freq'
    ADAFRUIT_IO_ALGAE_OD = b'algae_od'
    ADAFRUIT_IO_ALGAE_FEED_RATE = b'algae_feed_rate'
    
    mqtt_motor_freq = bytes('{:s}/feeds/{:s}'.format(ADAFRUIT_USERNAME, ADAFRUIT_IO_MOTOR_FREQ), 'utf-8')
    mqtt_temp_chart = bytes('{:s}/feeds/{:s}'.format(ADAFRUIT_USERNAME, ADAFRUIT_IO_TEMP_CHART), 'utf-8')
    mqtt_ref_temp = bytes('{:s}/feeds/{:s}'.format(ADAFRUIT_USERNAME, ADAFRUIT_IO_TEMP), 'utf-8')   
    mqtt_algae_od = bytes('{:s}/feeds/{:s}'.format(ADAFRUIT_USERNAME, ADAFRUIT_IO_ALGAE_OD), 'utf-8')
    mqtt_algae_feed_rate = bytes('{:s}/feeds/{:s}'.format(ADAFRUIT_USERNAME, ADAFRUIT_IO_ALGAE_FEED_RATE), 'utf-8')
    
    
    client = MQTTClient(client_id=mqtt_client_id, 
                        server=ADAFRUIT_IO_URL, 
                        user=ADAFRUIT_USERNAME, 
                        password=ADAFRUIT_IO_KEY,
                        ssl=False)
    
    try:            
        client.connect()
    except Exception as e:
        print('could not connect to MQTT server {}{}'.format(type(e).__name__, e))
        sys.exit()
    
    #client.set_callback(cb)
    #client.set_callback(ac)                    
    #client.subscribe(mqtt_ref_temp)
    #client.subscribe(mqtt_algae_feed_rate)
    client.set_callback(cb)
    client.subscribe(mqtt_ref_temp)
    mqtt_ref_temp_get = bytes('{:s}/get'.format(mqtt_ref_temp), 'utf-8')    
    client.publish(mqtt_ref_temp_get, '\0') 
    
    client.subscribe(mqtt_algae_feed_rate)
    mqtt_algae_feed_rate_get = bytes('{:s}/get'.format(mqtt_algae_feed_rate), 'utf-8')    
    client.publish(mqtt_algae_feed_rate_get, '\0')
    
    #mqtt_ref_temp_get = bytes('{:s}/get'.format(mqtt_ref_temp), 'utf-8')    
    #client.publish(mqtt_ref_temp_get, '\0')  

    #mqtt_algae_feed_rate_get = bytes('{:s}/get'.format(mqtt_algae_feed_rate), 'utf-8')    
    #client.publish(mqtt_algae_feed_rate_get, '\0')
    # wait until data has been Published to the Adafruit IO feed

    while True:
        Thread_website = True
        lock.acquire()
        for i in range(10):
            try:
                client.check_msg()
            except KeyboardInterrupt:
                print('Ctrl-C pressed...exiting')
                client.disconnect()
                sys.exit()
            time.sleep_ms(10)
        
        cooling_motor_data = cooling_pump.freq()
        client.publish(mqtt_motor_freq,    
                bytes(str(cooling_motor_data), 'utf-8'), 
                qos=0) 
     
        client.publish(mqtt_temp_chart,    
                bytes(str(current_temp), 'utf-8'), 
                qos=0) 
        
        client.publish(mqtt_algae_od,    
                bytes(str(intensity_av), 'utf-8'), 
                qos=0)
        lock.release()
        time.sleep(7)
#############


# lock
lock = _thread.allocate_lock()    
    
# Initialisation of the PID
    
# read_temp


adc_V_lookup = [0.0, 0.003088235, 0.006176471, 0.009264706, 0.01235294, 0.01544118, 0.01852941, 0.02161765, 0.02470588, 0.02779412, 0.03088236, 0.03397059, 0.03705883, 0.04014706, 0.0432353, 0.04632353, 0.04941177, 0.05352942, 0.05764706, 0.06176471, 0.06485295, 0.06794118, 0.07102942, 0.07411765, 0.07720589, 0.08029412, 0.08338236, 0.08647059, 0.08955883, 0.09264707, 0.0957353, 0.09882354, 0.1019118, 0.105, 0.1080882, 0.1111765, 0.1142647, 0.117353, 0.1204412, 0.1235294, 0.1266177, 0.1297059, 0.1327941, 0.1358824, 0.1389706, 0.1420588, 0.1451471, 0.1482353, 0.1523529, 0.1564706, 0.1605882, 0.1636765, 0.1667647, 0.1698529, 0.1729412, 0.1760294, 0.1791177, 0.1822059, 0.1852941, 0.1883824, 0.1914706, 0.1945588, 0.1976471, 0.2007353, 0.2038235, 0.2069118, 0.21, 0.2141177, 0.2182353, 0.222353, 0.2248235, 0.2272941, 0.2297647, 0.2322353, 0.2347059, 0.2388236, 0.2429412, 0.2470588, 0.2501471, 0.2532353, 0.2563236, 0.2594118, 0.2625, 0.2655883, 0.2686765, 0.2717647, 0.274853, 0.2779412, 0.2810294, 0.2841177, 0.2872059, 0.2902942, 0.2933824, 0.2964706, 0.2995588, 0.3026471, 0.3057353, 0.3088235, 0.3129412, 0.3170588, 0.3211765, 0.3236471, 0.3261177, 0.3285882, 0.3310588, 0.3335294, 0.3376471, 0.3417647, 0.3458824, 0.3489706, 0.3520588, 0.3551471, 0.3582353, 0.3613235, 0.3644118, 0.3675, 0.3705883, 0.3730588, 0.3755294, 0.378, 0.3804706, 0.3829412, 0.3891177, 0.3952941, 0.3983824, 0.4014706, 0.4045588, 0.4076471, 0.4101177, 0.4125883, 0.4150588, 0.4175294, 0.42, 0.4230883, 0.4261765, 0.4292647, 0.432353, 0.4354412, 0.4385294, 0.4416177, 0.4447059, 0.4477942, 0.4508824, 0.4539706, 0.4570589, 0.4611764, 0.4652942, 0.4694118, 0.4725, 0.4755883, 0.4786765, 0.4817647, 0.4842353, 0.4867059, 0.4891765, 0.4916471, 0.4941177, 0.4982353, 0.502353, 0.5064706, 0.5095589, 0.5126471, 0.5157353, 0.5188236, 0.5219118, 0.525, 0.5280883, 0.5311765, 0.5352941, 0.5394118, 0.5435295, 0.5466177, 0.5497059, 0.5527942, 0.5558824, 0.5589706, 0.5620589, 0.5651471, 0.5682353, 0.5713236, 0.5744118, 0.5775001, 0.5805883, 0.5847059, 0.5888236, 0.5929412, 0.5960294, 0.5991177, 0.6022058, 0.6052941, 0.6077647, 0.6102353, 0.6127059, 0.6151765, 0.6176471, 0.6217647, 0.6258824, 0.63, 0.6330882, 0.6361765, 0.6392647, 0.642353, 0.6454412, 0.6485294, 0.6516176, 0.6547059, 0.6577941, 0.6608824, 0.6639706, 0.6670588, 0.670147, 0.6732353, 0.6763235, 0.6794118, 0.6825, 0.6855883, 0.6886765, 0.6917647, 0.6958824, 0.7, 0.7041177, 0.7072059, 0.7102942, 0.7133823, 0.7164706, 0.7195588, 0.7226471, 0.7257353, 0.7288236, 0.7312942, 0.7337647, 0.7362353, 0.7387059, 0.7411765, 0.7452941, 0.7494118, 0.7535295, 0.7566176, 0.7597059, 0.7627941, 0.7658824, 0.7689706, 0.7720589, 0.7751471, 0.7782353, 0.7807059, 0.7831765, 0.785647, 0.7881176, 0.7905883, 0.7936765, 0.7967648, 0.7998529, 0.8029412, 0.805, 0.8070589, 0.8091177, 0.8111765, 0.8132354, 0.8152942, 0.8183824, 0.8214706, 0.8245588, 0.8276471, 0.8307353, 0.8338236, 0.8369118, 0.8400001, 0.8441177, 0.8482353, 0.852353, 0.8548235, 0.8572942, 0.8597647, 0.8622354, 0.8647059, 0.8688236, 0.8729412, 0.8770589, 0.8801471, 0.8832354, 0.8863235, 0.8894118, 0.8925, 0.8955883, 0.8986765, 0.9017648, 0.904853, 0.9079412, 0.9110294, 0.9141177, 0.9172059, 0.9202942, 0.9233824, 0.9264707, 0.9295588, 0.9326471, 0.9357353, 0.9388236, 0.9419118, 0.9450001, 0.9480883, 0.9511765, 0.9542647, 0.957353, 0.9604412, 0.9635295, 0.9666177, 0.969706, 0.9727942, 0.9758824, 0.9789706, 0.9820589, 0.9851471, 0.9882354, 0.9913236, 0.9944118, 0.9975, 1.000588, 1.004706, 1.008824, 1.012941, 1.015412, 1.017882, 1.020353, 1.022824, 1.025294, 1.028382, 1.031471, 1.034559, 1.037647, 1.041765, 1.045882, 1.05, 1.052471, 1.054941, 1.057412, 1.059882, 1.062353, 1.066471, 1.070588, 1.074706, 1.077794, 1.080882, 1.083971, 1.087059, 1.090147, 1.093235, 1.096324, 1.099412, 1.1025, 1.105588, 1.108677, 1.111765, 1.114853, 1.117941, 1.121029, 1.124118, 1.127206, 1.130294, 1.133382, 1.136471, 1.140588, 1.144706, 1.148824, 1.151294, 1.153765, 1.156235, 1.158706, 1.161177, 1.164265, 1.167353, 1.170441, 1.17353, 1.177647, 1.181765, 1.185882, 1.188971, 1.192059, 1.195147, 1.198235, 1.201324, 1.204412, 1.2075, 1.210588, 1.213059, 1.215529, 1.218, 1.220471, 1.222941, 1.226029, 1.229118, 1.232206, 1.235294, 1.238382, 1.241471, 1.244559, 1.247647, 1.251765, 1.255882, 1.26, 1.262471, 1.264941, 1.267412, 1.269882, 1.272353, 1.276471, 1.280588, 1.284706, 1.287794, 1.290882, 1.293971, 1.297059, 1.299529, 1.302, 1.304471, 1.306941, 1.309412, 1.3125, 1.315588, 1.318676, 1.321765, 1.325882, 1.33, 1.334118, 1.337206, 1.340294, 1.343382, 1.346471, 1.349559, 1.352647, 1.355735, 1.358824, 1.361294, 1.363765, 1.366235, 1.368706, 1.371176, 1.375294, 1.379412, 1.383529, 1.386618, 1.389706, 1.392794, 1.395882, 1.398971, 1.402059, 1.405147, 1.408235, 1.411324, 1.414412, 1.4175, 1.420588, 1.423059, 1.425529, 1.428, 1.430471, 1.432941, 1.437059, 1.441177, 1.445294, 1.448382, 1.451471, 1.454559, 1.457647, 1.460735, 1.463824, 1.466912, 1.47, 1.474118, 1.478235, 1.482353, 1.485441, 1.488529, 1.491618, 1.494706, 1.497794, 1.500882, 1.503971, 1.507059, 1.510147, 1.513235, 1.516324, 1.519412, 1.5225, 1.525588, 1.528677, 1.531765, 1.534853, 1.537941, 1.541029, 1.544118, 1.548235, 1.552353, 1.556471, 1.558941, 1.561412, 1.563882, 1.566353, 1.568824, 1.571912, 1.575, 1.578088, 1.581177, 1.584265, 1.587353, 1.590441, 1.593529, 1.596618, 1.599706, 1.602794, 1.605882, 1.608353, 1.610824, 1.613294, 1.615765, 1.618235, 1.621324, 1.624412, 1.6275, 1.630588, 1.633677, 1.636765, 1.639853, 1.642941, 1.647059, 1.651177, 1.655294, 1.658382, 1.661471, 1.664559, 1.667647, 1.670735, 1.673824, 1.676912, 1.68, 1.682471, 1.684941, 1.687412, 1.689882, 1.692353, 1.696471, 1.700588, 1.704706, 1.707794, 1.710882, 1.713971, 1.717059, 1.721177, 1.725294, 1.729412, 1.731882, 1.734353, 1.736824, 1.739294, 1.741765, 1.745882, 1.75, 1.754118, 1.756588, 1.759059, 1.76153, 1.764, 1.766471, 1.772647, 1.778824, 1.781294, 1.783765, 1.786235, 1.788706, 1.791177, 1.794265, 1.797353, 1.800441, 1.80353, 1.806618, 1.809706, 1.812794, 1.815882, 1.818971, 1.822059, 1.825147, 1.828235, 1.831324, 1.834412, 1.8375, 1.840588, 1.843677, 1.846765, 1.849853, 1.852941, 1.85603, 1.859118, 1.862206, 1.865294, 1.869412, 1.87353, 1.877647, 1.880735, 1.883824, 1.886912, 1.89, 1.893088, 1.896177, 1.899265, 1.902353, 1.905441, 1.908529, 1.911618, 1.914706, 1.918823, 1.922941, 1.927059, 1.929529, 1.932, 1.934471, 1.936941, 1.939412, 1.943529, 1.947647, 1.951765, 1.954853, 1.957941, 1.96103, 1.964118, 1.968235, 1.972353, 1.976471, 1.979559, 1.982647, 1.985735, 1.988824, 1.991294, 1.993765, 1.996235, 1.998706, 2.001177, 2.005294, 2.009412, 2.01353, 2.016, 2.018471, 2.020941, 2.023412, 2.025882, 2.028971, 2.032059, 2.035147, 2.038235, 2.041324, 2.044412, 2.0475, 2.050588, 2.053677, 2.056765, 2.059853, 2.062941, 2.06603, 2.069118, 2.072206, 2.075294, 2.078382, 2.081471, 2.084559, 2.087647, 2.091765, 2.095882, 2.1, 2.102471, 2.104941, 2.107412, 2.109882, 2.112353, 2.116471, 2.120588, 2.124706, 2.127794, 2.130883, 2.133971, 2.137059, 2.140147, 2.143235, 2.146324, 2.149412, 2.1525, 2.155588, 2.158677, 2.161765, 2.164853, 2.167941, 2.17103, 2.174118, 2.178235, 2.182353, 2.186471, 2.188529, 2.190588, 2.192647, 2.194706, 2.196765, 2.198824, 2.205, 2.211177, 2.214265, 2.217353, 2.220441, 2.22353, 2.226618, 2.229706, 2.232794, 2.235883, 2.238353, 2.240824, 2.243294, 2.245765, 2.248235, 2.251324, 2.254412, 2.2575, 2.260588, 2.264706, 2.268824, 2.272941, 2.27603, 2.279118, 2.282206, 2.285294, 2.288383, 2.291471, 2.294559, 2.297647, 2.300735, 2.303824, 2.306912, 2.31, 2.313088, 2.316177, 2.319265, 2.322353, 2.325441, 2.32853, 2.331618, 2.334706, 2.337177, 2.339647, 2.342118, 2.344588, 2.347059, 2.351177, 2.355294, 2.359412, 2.361882, 2.364353, 2.366824, 2.369294, 2.371765, 2.374853, 2.377941, 2.381029, 2.384118, 2.386588, 2.389059, 2.39153, 2.394, 2.396471, 2.399559, 2.402647, 2.405735, 2.408823, 2.411912, 2.415, 2.418088, 2.421176, 2.423647, 2.426118, 2.428588, 2.431059, 2.433529, 2.436618, 2.439706, 2.442794, 2.445882, 2.448971, 2.452059, 2.455147, 2.458235, 2.462353, 2.466471, 2.470588, 2.473059, 2.475529, 2.478, 2.480471, 2.482941, 2.486029, 2.489118, 2.492206, 2.495294, 2.497765, 2.500235, 2.502706, 2.505177, 2.507647, 2.511765, 2.515882, 2.52, 2.522471, 2.524941, 2.527412, 2.529882, 2.532353, 2.535441, 2.538529, 2.541618, 2.544706, 2.547794, 2.550882, 2.553971, 2.557059, 2.560147, 2.563235, 2.566324, 2.569412, 2.5725, 2.575588, 2.578676, 2.581765, 2.584235, 2.586706, 2.589177, 2.591647, 2.594118, 2.597206, 2.600294, 2.603382, 2.606471, 2.609559, 2.612647, 2.615735, 2.618824, 2.621294, 2.623765, 2.626235, 2.628706, 2.631176, 2.634265, 2.637353, 2.640441, 2.643529, 2.646618, 2.649706, 2.652794, 2.655882, 2.658353, 2.660824, 2.663294, 2.665765, 2.668235, 2.672353, 2.676471, 2.680588, 2.682647, 2.684706, 2.686765, 2.688824, 2.690882, 2.692941, 2.697059, 2.701177, 2.705294, 2.707765, 2.710235, 2.712706, 2.715177, 2.717647, 2.720735, 2.723824, 2.726912, 2.73, 2.732059, 2.734118, 2.736176, 2.738235, 2.740294, 2.742353, 2.745441, 2.748529, 2.751618, 2.754706, 2.758824, 2.762941, 2.767059, 2.769529, 2.772, 2.774471, 2.776941, 2.779412, 2.781471, 2.78353, 2.785588, 2.787647, 2.789706, 2.791765, 2.794853, 2.797941, 2.801029, 2.804118, 2.806588, 2.809059, 2.81153, 2.814, 2.816471, 2.818941, 2.821412, 2.823883, 2.826353, 2.828824, 2.830883, 2.832941, 2.835, 2.837059, 2.839118, 2.841177, 2.844265, 2.847353, 2.850441, 2.853529, 2.856, 2.858471, 2.860941, 2.863412, 2.865882, 2.868353, 2.870824, 2.873294, 2.875765, 2.878235, 2.880294, 2.882353, 2.884412, 2.886471, 2.88853, 2.890588, 2.893677, 2.896765, 2.899853, 2.902941, 2.904706, 2.906471, 2.908235, 2.91, 2.911765, 2.91353, 2.915294, 2.917765, 2.920235, 2.922706, 2.925177, 2.927647, 2.930118, 2.932588, 2.935059, 2.93753, 2.94, 2.941765, 2.94353, 2.945294, 2.947059, 2.948823, 2.950588, 2.952353, 2.954412, 2.956471, 2.958529, 2.960588, 2.962647, 2.964706, 2.967176, 2.969647, 2.972118, 2.974588, 2.977059, 2.978824, 2.980588, 2.982353, 2.984118, 2.985882, 2.987647, 2.989412, 2.991882, 2.994353, 2.996824, 2.999294, 3.001765, 3.003824, 3.005883, 3.007941, 3.01, 3.012059, 3.014118, 3.015882, 3.017647, 3.019412, 3.021177, 3.022941, 3.024706, 3.026471, 3.028235, 3.03, 3.031765, 3.03353, 3.035294, 3.037059, 3.038824, 3.040883, 3.042941, 3.045, 3.047059, 3.049118, 3.051177, 3.054265, 3.057353, 3.060441, 3.106765]

NOM_RES = 10000
SER_RES = 9820
TEMP_NOM = 25
NUM_SAMPLES = 25
THERM_B_COEFF = 3950
ADC_MAX = 1023
ADC_Vmax = 3.15

def init_temp_sensor(TENP_SENS_ADC_PIN_NO = 32):
    adc = ADC(Pin(TENP_SENS_ADC_PIN_NO))
    adc.atten(ADC.ATTN_11DB)
    adc.width(ADC.WIDTH_12BIT)
    return adc

def read_temp(temp_sens):
    raw_read = []
    # Collect NUM_SAMPLES
    for i in range(1, NUM_SAMPLES+1):
        raw_read.append(int((temp_sens.read())/4))

    # Average of the NUM_SAMPLES and look it up in the table
    raw_average = sum(raw_read)/NUM_SAMPLES
    #print('raw_avg = ' + str(raw_average))
    #print('V_measured = ' + str(adc_V_lookup[round(raw_average)]))

    # Convert to resistance
    raw_average = ADC_MAX * adc_V_lookup[round(raw_average)]/ADC_Vmax
    resistance = (SER_RES * raw_average) / (ADC_MAX - raw_average)
    #print('Thermistor resistance: {} ohms'.format(resistance))

    # Convert to temperature
    steinhart  = log(resistance / NOM_RES) / THERM_B_COEFF
    steinhart += 1.0 / (TEMP_NOM + 273.15)
    steinhart  = (1.0 / steinhart) - 273.15
    return steinhart

temp_sens = init_temp_sensor()
    
# Motor setup
# optional way to code
# watch dog timer!
I_sum = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
def pid_update(P,I,D,error,current_temp,reference_temp,prev_error):
    
    global I_sum
    
    Pterm = P * error
    Dterm = D * (error - prev_error)
    
    I_sum.append(error)
    I_sum = I_sum[1:]
    Iterm = I * sum(I_sum)
    
    prev_error = error
    
    # return is Ut
    Ut = Pterm + Dterm + Iterm
    print("reference temp: " + str(reference_temp))
    
    return Ut

# =============================================================================
# def subscription():
#     mqtt_ref_temp_get = bytes('{:s}/get'.format(mqtt_ref_temp), 'utf-8')    
#     client.publish(mqtt_ref_temp_get, '\0')  
# 
#     # wait until data has been Published to the Adafruit IO feed
#     while True:
#         try:
#             client.wait_msg()
#         except KeyboardInterrupt:
#             print('Ctrl-C pressed...exiting')
#             client.disconnect()
#             sys.exit()
#         time.sleep(1)
# =============================================================================
    
def coolingsystem():
    global cooling_pump
    p12 = machine.Pin(12)
    cooling_pump = machine.PWM(p12)
    cooling_pump.freq(0)
    
    i2c = I2C(scl=Pin(22), sda=Pin(23), freq=100000) #defining Pins
    oled = ssd1306.SSD1306_I2C(128, 32, i2c) #accesing the ssd1306 package
    oled.fill(0) #clears display
    oled.show() #refreshes display
    def updateOLED(waterTempText, ODText, RPMText): 		#input should be numbers, int or float, for all 3 variables
        oled.fill(0)						#clears display
        oled.text(("Temp: "+str(waterTempText)+" C"), 0, 0)	#shows water temperature
        oled.text(("Intensity: "+str(ODText)), 0, 10)			#shows OD
        oled.text(("RPM: "+str(RPMText)), 0, 20)		#shows RPM
        oled.show()						#refreshes display
    
    p33 = machine.Pin(33,Pin.OUT)
    p33.value(0)
        
    prev_error = 0
    P = 20000
    I = 1000
    D = 100
    
    global current_temp
    global Thread_cooling
    start_time = time.time()
    count = 0
    while(True):
        Thread_cooling = True
        count = count+1
        time.sleep_ms(1000)
        lock.acquire()
        temp_av = 0
        for i in range(0,200):
            time.sleep_ms(10)
            temp = read_temp(temp_sens)
            temp_av = temp_av + temp
        temp_av = temp_av/200
        
        current_temp = temp_av
        error = current_temp - reference_temp
        
        print('Thermistor temperature: ' + str(current_temp))
    
        PID = int(pid_update(P,I,D,error,current_temp,reference_temp,prev_error))
        if (count%10)==0:
            f = open('Temperature.txt','a')
            f.write(str(time.time()-start_time) + ';' + str(current_temp) + '\n')
            f.close()
        
        print("PID output: " + str(PID))

        if PID > 40000:
            PID = 40000
        elif PID < 1000:
            PID = 1000
            
        if PID <= 5000:
            p33.value(1)
        elif PID > 5000:
            p33.value(0)
            
        print("Power Level for Peltier element: " + str(p33.value()))
        print("Intensity: " + str(intensity_av))
        print("concentration: " + str(concentration))
        updateOLED(current_temp,intensity_av,cooling_pump.freq())
            
        des_motor_freq = PID
        motor_steps = abs(des_motor_freq - cooling_pump.freq())/1000
        motor_steps = int(1+motor_steps)
        for i in range(0,motor_steps):
            time.sleep_ms(10)
            if abs(des_motor_freq - cooling_pump.freq())<1000:
                cooling_pump.freq(cooling_pump.freq() + des_motor_freq - cooling_pump.freq())
                break
            elif (des_motor_freq - cooling_pump.freq()) > 0:
                cooling_pump.freq(cooling_pump.freq() + 1000)
            else:
                cooling_pump.freq(cooling_pump.freq() - 1000)
        print("Motor frequency: " + str(cooling_pump.freq()))
        
        lock.release()
        time.sleep(2)
        

def feeding():
    adc1 = machine.ADC(machine.Pin(34))
    LED = machine.Pin(15, machine.Pin.OUT)
    LED.value(1)
    feeding_pump = machine.Pin(27, machine.Pin.OUT)
    global intensity_av
    global Thread_feeding
    #dose = 100000
    ticksML = 13334
    amount_mussel = 2
    start_time = time.time()
    
    # initial fillup
    lock.acquire()
    time.sleep(20)
    intensity_sum = 0
    for j in range(300):
            intensity = adc1.read()
            time.sleep_ms(10)
            intensity_sum = intensity_sum+intensity
    intensity_av = intensity_sum/300
    c = 0
    if intensity_av > 3220:
            intensity_av = 3220
    elif intensity_av < 1220:
        intensity_av = 1220
    intensity_av = intensity_av - 220
    feed = (((8000*3000) - (c*3000))/(-2.409638554*(10**6)*math.log(0.0002513720730*intensity_av)/math.log(10)-8024.096385))
    dose = (feed-11)*ticksML
    f = open('Feed.txt','a')
    f.write(str(time.time()-start_time) + ';' + str(feed) + ';' + str(c) + ';' + str(intensity_av) +'\n')
    f.close()
    for i in range(dose):
        feeding_pump.value(1)
        time.sleep_us(50)
        feeding_pump.value(0)
    lock.release()

    
    while True:
        Thread_feeding = True
        print("motor 2 sleeps!!")
        c = concentration
        for i in range(60):
            f = ((amount_mussel*7.339*(10**6))*math.log((0.001057*c)))/(6*60*3000)
            a = c*math.exp(0.1696/(24*60*60)*10)
            c = a - f
            print("Conc: " + str(c))
            time.sleep(10)
        intensity_sum = 0
        # OD calibration
# =============================================================================
#         lock.acquire()
#         time.sleep(20)
#         for i in range(250000):
#             feeding_pump.value(1)
#             time.sleep_us(50)
#             feeding_pump.value(0)
#         f = open('ODdataset.txt','w')
#         for i in range(30):
#             data_av = 0 
#             for j in range(300):
#                 data = adc1.read()
#                 time.sleep_ms(10)
#                 data_av = data_av+data
#             data_av = data_av/300
#             print("OD-value: " + str(data_av))
#             f.write('%d\n' % (data_av))
#         f.close()
#         lock.release()
#         print("ENDDDDDDD")
#         time.sleep(100)
# =============================================================================
        # end of OD calibration
        for j in range(300):
            intensity = adc1.read()
            time.sleep_ms(10)
            intensity_sum = intensity_sum+intensity
        intensity_av = intensity_sum/300
        if intensity_av > 3220:
            intensity_av = 3220
        elif intensity_av < 1220:
            intensity_av = 1220
        intensity_av = intensity_av - 220
        feed = (((8000*3000) - (c*3000))/(-2.409638554*(10**6)*math.log(0.0002513720730*intensity_av)/math.log(10)-8024.096385)/10)
        print("Feed Volume: " + str(feed))
        
        f = open('Feed.txt','a')
        f.write(str(time.time()-start_time) + ';' + str(feed) + ';' + str(c) + ';' + str(intensity_av) +'\n')
        f.close()
        
        # 9.732418 mL per mussel resulted in 33mL
        # total volume times amount of ticks it needs per mL
        dose = feed*ticksML
        lock.acquire()
        print("motor 2 starts")
        time.sleep(5)
        for i in range(dose):
            feeding_pump.value(1)
            time.sleep_us(50)
            feeding_pump.value(0)
        lock.release()
        
def watchdog():
    global Thread_website
    global Thread_cooling
    global Thread_feeding
    global Offline
    while True:
        time.sleep(360)
        print("hello")
        if Offline == False:
            if Thread_website == True:
                Thread_website = False
            elif Thread_website == False:
                print("RESTART")
                cooling_pump.freq(0)
                machine.reset()
        if Thread_cooling == True:
            Thread_cooling = False
        elif Thread_cooling == False:
            print("Restart C")
            cooling_pump.freq(0)
            machine.reset()
        if Thread_feeding == True:
            Thread_feeding = False
        elif Thread_feeding == False:
            print("Restart F")
            cooling_pump.freq(0)
            machine.reset()
            
_thread.start_new_thread(coolingsystem, ())
_thread.start_new_thread(feeding, ())
_thread.start_new_thread(website, ())
#_thread.start_new_thread(watchdog, ())

# =============================================================================
#import os
#os.remove("main.py")
# =============================================================================
