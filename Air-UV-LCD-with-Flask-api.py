#!/usr/bin/env python
from flask import Flask, jsonify, make_response
import veml6075
from sgp30 import SGP30
import smbus
import sys
from PIL import Image, ImageDraw, ImageFont
from ST7789 import ST7789

# Set Up Air Quality Sensor - SGP30
bus = smbus.SMBus(1)
sgp30 = SGP30()

# Create VEML6075 instance and set up
uv_sensor = veml6075.VEML6075(i2c_dev=bus)
uv_sensor.set_shutdown(False)
uv_sensor.set_high_dynamic_range(False)
uv_sensor.set_integration_time('100ms')

#Set up screen
SPI_SPEED_MHZ = 80
screen = ST7789(
    rotation=90,  # Needed to display the right way up
    port=0,       # SPI port
    cs=1,         # SPI port Chip-select channel
    dc=9,         # BCM pin used for data/command
    backlight=13,
    spi_speed_hz=SPI_SPEED_MHZ * 1000 * 1000
)

## Screen size details
width = screen.width
height = screen.height

## Image setup
image = Image.new("RGB", (240, 240), (0, 0, 0))
draw = ImageDraw.Draw(image)

## Set up fonts

mdifont = ImageFont.truetype("/usr/share/fonts/truetype/materialdesignicons-webfont.ttf", 50)
font = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/arial.ttf", 30)

## Display Something While Waiting for the SGP30 Sensor to Warm Up (Can be any 240 x 240 image) 
image = Image.open("/home/pi/pimoroni-pirate.png")
screen.display(image)

# Warm Up SGP30 sensor
def crude_progress_bar():
    sys.stdout.write('.')
    sys.stdout.flush()

sgp30.start_measurement(crude_progress_bar)

## Blank Screen
image = Image.new("RGB", (240, 240), (0, 0, 0))
draw = ImageDraw.Draw(image)
screen.display(image)

def show_text(draw, message, x, y, font, ralign, r, g, b):
	size_x, size_y = font.getsize(message)
	text_y = y - size_y
	text_x = x
	if ralign == True:
		text_x = (360 - size_x) / 2
	else:
		text_x = (120 - size_x) / 2
	draw.text((text_x, text_y), message, font=font, fill=(r, g, b))

## Top Left Icon
show_text(draw, u"\uF7E3", 35, 60, mdifont, False, 0, 200, 250)
## Top Right Icon
show_text(draw, u"\uF096", 160, 60, mdifont, True, 0, 200, 250)
## Bottom Left Icon
show_text(draw, u"\uFF54", 35, 180, mdifont, False, 250 , 250, 0)
## Bottom Right Icon
show_text(draw, u"\uF4e0", 160, 180, mdifont, True, 250 , 250, 0)

## Grid Lines
# Horizontal
draw.line((10,122, 230,122), fill = "grey", width = 3)
# Vertical
draw.line((120,10, 120,230), fill = "grey", width = 3)

screen.display(image)

def blank_top_text_row():
	draw.rectangle(((0, 68), (115, 115)), fill="black")
	draw.rectangle(((130, 68), (235, 115)), fill="black")

def blank_bottom_text_row():
	draw.rectangle(((0, 180), (115, 225)), fill="black")
	draw.rectangle(((130, 180), (235, 225)), fill="black")

app = Flask(__name__)

@app.route('/sensor/co2_voc', methods=['GET'])
def co2_voc():
    split_result = str(sgp30.get_air_quality()).split(' ')
    first = 0
    co2 = 0
    voc = 0
    for i in split_result:
        if i.isdigit() and first == 0:
            co2 = i
            first = 1
        if i.isdigit() and first == 1:
            voc = i
    blank_top_text_row()
    show_text(draw, str(co2), 25, 100, font, False, 255, 255, 255)
    show_text(draw, str(voc), 150, 100, font, True, 255, 255, 255)
    screen.display(image)
    return jsonify({'CO2' : co2, 'VOC' : voc})

@app.route('/sensor/uv_index', methods=['GET'])
def uv_index_readings():
    uva, uvb = uv_sensor.get_measurements()
    uv_comp1, uv_comp2 = uv_sensor.get_comparitor_readings()
    uv_indices = uv_sensor.convert_to_index(uva, uvb, uv_comp1, uv_comp2)
    blank_bottom_text_row()
    show_text(draw, str(float(round(uv_indices[0], 2))), 25, 220, font, False, 255, 255, 255)
    show_text(draw, str(float(round(uv_indices[1], 2))), 150, 220, font, True, 255, 255, 255)
    screen.display(image)
    return jsonify({'uva_index' : float(round(uv_indices[0],3)), 'uvb_index' : float(round(uv_indices[1], 3))})

@app.route('/sensor/uv_raw', methods=['GET'])
def uv_raw_readings():
    uva, uvb = uv_sensor.get_measurements()
    return jsonify({'uva_raw' : uva, 'uvb_raw' : uvb})

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)
