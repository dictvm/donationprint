#!/usr/bin/python
import os
import sys
import syslog
import usb.core
import usb.util
import daemon
import csv

with daemon.DaemonContext():

	VENDOR_ID = 0x0801
	PRODUCT_ID = 0x0002
	DATA_SIZE = 337

	syslog.syslog("Starting application.")

	device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
	if device is None:
		syslog.syslog(syslog.LOG_ERR, "Could not find MagTek USB HID Swipe Reader.")
		sys.exit("Could not find MagTek USB HID Swipe Reader.")

	if device.is_kernel_driver_active(0):
		try:
			device.detach_kernel_driver(0)
		except usb.core.USBError as e:
			syslog.syslog(syslog.LOG_ERR, "Could not detach kernel driver: %s" % str(e))
			sys.exit("Could not detatch kernel driver: %s" % str(e))

	try:
		device.set_configuration()
		device.reset()
	except usb.core.USBError as e:
		syslog.syslog(syslog.LOG_ERR, "Could not set configuration: %s" % str(e))
		sys.exit("Could not set configuration: %s" % str(e))
	endpoint = device[0][(0,0)][0]

	data = []
	swiped = False
    code = "DE"
	syslog.syslog("Ready. Awaiting card!")

	def printform(account,bank):
		filepath = sys.path[0]
		os.system("sed -e 's/##account##/%s/g' -e 's/##bank##/%s/g' %s/bon.svg | inkscape --without-gui --export-ps=/dev/stdout /dev/stdin | lp -d Star_TSP143_" % (account, bank, filepath))

	def printthanks():
		filepath = sys.path[0]
		os.system("lp -d Star_TSP143_ -o media=om_x72-mmy50-mm_71.96x49.74mm %s/danke.ps" % str(filepath))

	while 1:
		try:
			data += device.read(endpoint.bEndpointAddress, endpoint.wMaxPacketSize)
			swiped = True
			if len(data) >= DATA_SIZE:
				newdata = "".join(map(chr, data))
				account = newdata[241:251]
				bank = newdata[232:240]
				if account.isdigit() and bank.isdigit():
					syslog.syslog("Got working card. Printing form.")

					printform(calc_iban,calc_bic)
					printthanks()
				else:
					syslog.syslog(syslog.LOG_ERR, "Unreadable card. Printing blank bon.")
					printform(" "," ")
					printthanks()
				swiped = False
				data = []

		except usb.core.USBError as e:
			if e.args == ('Operation timed out',) and swiped:
				if len(data) < DATA_SIZE:
					syslog.syslog(syslog.LOG_ERR, "Bad swipe. (%d bytes)" % len(data))
					data = []
					swiped = False
					continue
				else:
					syslog.syslog(syslog.LOG_ERR, "Not enough data grabbed. (%d bytes)" % len(data))
					data = []
					swiped = False
					continue

# portions taken from GPLed code by Tom: http://toms-cafe.de/iban/iban.py
def create_iban(code, bank, account, alternative = 0):
    err = None
    country = country_data(code)
    if not country:
        err = "Unknown Country Code: %s" % code
    elif len(bank) != country.bank_lng():
        err = "Bank/Branch Code length %s is not correct for %s (%s)" % \
              (len(bank), country.name, country.bank_lng())
    elif invalid_bank(country, bank):
        err = "Bank/Branch Code %s is not correct for %s" % \
              (bank, country.name)
    elif len(account) > country.acc_lng():
        err = "Account Number length %s is not correct for %s (%s)" % \
              (len(account), country.name, country.acc_lng())
    elif invalid_account(country, account):
        err = "Account Number %s is not correct for %s" % \
              (account, country.name)
    if err:
        raise IBANError(err)
    return calc_iban(country, bank, account, alternative)

def create_bic(bank):
    err = None
    for line in open("bankid2bic.csv"):
        if bank in line:
        print line.split(",")[1]
    return calc_bic(bank)
