from sys import argv, exc_info
from time import sleep
from smbus import SMBus

class veml6075:
	# Register Addresses
	regUVConf = 0x00
	regUVA = 0x07
	regUVB = 0x09
	regUVComp1 = 0x0A
	regUVComp2 = 0x0B
	regID = 0x0C
	# Config Register Bit Masks
	powerOn = 0x00
	powerOff = 0x01
	triggerMeasurement = 0x04
	highDynamic = 0x08
	normalDynamic = 0x00
	integTime50 = 0x00
	integTime100 = 0x10
	integTime200 = 0x20
	integTime400 = 0x30
	integTime800 = 0x40
	integStrings = {0x00 : "50ms", 0x10 : "100ms", 0x20 : "200ms", 0x30 : "400ms", 0x40 : "800ms"}
	# UV Coefficents, Responsivity
	A = 2.22  # UVA visible
	B = 1.33  # UVA infrared
	C = 2.95  # UVB visible
	D = 1.74  # UVB infrared
	UVAresp = 0.001461
	UVBresp = 0.002591
	# Conversion Factors (VEML6075 Datasheet Rev. 1.2, 23-Nov-16)
	UVACountsPeruWcm = 0.93
	UVBCountsPeruWcm = 2.10



	def __init__(self, address):
		self.address = address
		self.integTimeSelect = 0x00
		self.dynamicSelect = 0x00
		self.waitTime = 0.0		
		self.divisor = 0

	def setADCSettings(self, i):
		if i == 0:
			self.integTimeSelect = veml6075.integTime800  # Most Sensitive
			self.dynamicSelect = veml6075.normalDynamic
			self.waitTime = 1.920
			self.divisor = 16
		elif i == 1:
			self.integTimeSelect = veml6075.integTime400
			self.dynamicSelect = veml6075.normalDynamic
			self.waitTime = 0.960
			self.divisor = 8
		elif i == 2:
			self.integTimeSelect = veml6075.integTime200
			self.dynamicSelect = veml6075.normalDynamic
			self.waitTime = 0.480
			self.divisor = 4
		elif i == 3:
			self.integTimeSelect = veml6075.integTime100
			self.dynamicSelect = veml6075.normalDynamic
			self.waitTime = 0.240
			self.divisor = 2
		elif i == 4:
			self.integTimeSelect = veml6075.integTime50
			self.dynamicSelect = veml6075.normalDynamic
			self.waitTime = 0.120
			self.divisor = 1
		elif i == 5:
			self.integTimeSelect = veml6075.integTime800
			self.dynamicSelect = veml6075.highDynamic
			self.waitTime = 1.920
			self.divisor = 16
		elif i == 6:
			self.integTimeSelect = veml6075.integTime400
			self.dynamicSelect = veml6075.highDynamic
			self.waitTime = 0.960
			self.divisor = 8
		elif i == 7:
			self.integTimeSelect = veml6075.integTime200
			self.dynamicSelect = veml6075.highDynamic
			self.waitTime = 0.480
			self.divisor = 4
		elif i == 8:
			self.integTimeSelect = veml6075.integTime100
			self.dynamicSelect = veml6075.highDynamic
			self.waitTime = 0.240
			self.divisor = 2
		elif i == 9:
			self.integTimeSelect = veml6075.integTime50  # Least Sensitive
			self.dynamicSelect = veml6075.highDynamic
			self.waitTime = 0.120
			self.divisor = 1
		else:
			self.error("ADC Configuration, Unkown Sensitivity Option")


	def error(self, message):
		print("Error: Failed "+ message)  # print error with message argument passed to function
		print(exc_info())  # print system exception info (type, value, traceback)
		raise SystemExit	


	def readDeviceID(self):
		try:
			deviceID = bus.read_word_data(self.address, veml6075.regID)
			print ("Device ID | 0x{:04X}" .format(deviceID))
		except:
			self.error("Device ID Read")


	def readUV(self, sensitivity):
		self.setADCSettings(sensitivity)
		bus.write_byte_data(self.address, veml6075.regUVConf, self.integTimeSelect|self.dynamicSelect|veml6075.powerOn)  # Write Dynamic and Integration Time Settings to Sensor 
		sleep(self.waitTime)  # Wait for ADC to finish first and second conversions, discarding the first
		bus.write_byte_data(self.address, veml6075.regUVConf, veml6075.powerOff)  # Power OFF

		rawDataUVA = bus.read_word_data(self.address,veml6075.regUVA)
		rawDataUVB = bus.read_word_data(self.address,veml6075.regUVB)
		rawDataUVComp1 = bus.read_word_data(self.address,veml6075.regUVComp1)  # visible noise
		rawDataUVComp2 = bus.read_word_data(self.address,veml6075.regUVComp2)  # infrared noise

		scaledDataUVA = rawDataUVA / self.divisor
		scaledDataUVB = rawDataUVB / self.divisor
		scaledDataUVComp1 = rawDataUVComp1 / self.divisor
		scaledDataUVComp2 = rawDataUVComp2 / self.divisor

		compensatedUVA = scaledDataUVA - (veml6075.A*scaledDataUVComp1) - (veml6075.B*scaledDataUVComp2)
		compensatedUVB = scaledDataUVB - (veml6075.C*scaledDataUVComp1) - (veml6075.D*scaledDataUVComp2)

		if compensatedUVA < 0:  # Do not allow negative readings which can occur in no UV light environments e.g. indoors
			compensatedUVA = 0
		if compensatedUVB < 0:
			compensatedUVB = 0

		UVAuWcm = compensatedUVA/ veml6075.UVACountsPeruWcm  # convert ADC counts to uWcm^2
		UVBuWcm = compensatedUVB / veml6075.UVBCountsPeruWcm

		UVAIndex = compensatedUVA * veml6075.UVAresp
		UVBIndex = compensatedUVB * veml6075.UVBresp
		UVI = (UVAIndex + UVBIndex) / 2

		print ("{} Integration Time, {} Dynamic" .format(veml6075.integStrings[self.integTimeSelect], "High" if self.dynamicSelect else "Normal"))
		
		print ("\nADC Counts:")
		print ("UVA ---------- {}" .format(rawDataUVA))
		print ("UVB ---------- {}" .format(rawDataUVB))
		print ("UVComp1 ------ {}" .format(rawDataUVComp1))
		print ("UVComp2 ------ {}" .format(rawDataUVComp2))

		print ("\nADC Counts Scaled to 50ms Integration Time:")
		print ("UVA ---------- {}" .format(int(scaledDataUVA)))
		print ("UVB ---------- {}" .format(int(scaledDataUVB)))
		print ("UVComp1 ------ {}" .format(int(scaledDataUVComp1)))
		print ("UVComp2 ------ {}" .format(int(scaledDataUVComp2)))

		print ("\nADC Counts Compensated for Visible and Infrared:")		
		print ("UVA ---------- {}" .format(int(compensatedUVA)))
		print ("UVB ---------- {}" .format(int(compensatedUVB)))

		print ("\nUVA|UVB Radiation:")
		print ("UVA (uWcm) --- {}" .format(int(UVAuWcm)))
		print ("UVB (uWcm) --- {}" .format(int(UVBuWcm)))

		print ("\nUVA|UVB Index:")
		print ("UVA Index ---- {}" .format(round(UVAIndex, 2)))
		print ("UVB Index ---- {}" .format(round(UVBIndex, 2)))
		print ("UVI ---------- {}" .format(round(UVI, 2)))


def main():
	if len(argv) >= 2:  # if the user has passed in an argument use it as the script option
		scriptOption = int(argv[1])
	else:  # else default to most sensitive ADC setting
		scriptOption = 0

	uv = veml6075(0x10)  # instantiate VEML6075 class with address 0x10
	uv.readDeviceID()
	uv.readUV(scriptOption)


if __name__ == "__main__":  # if source file is being executed as the main program
	bus = SMBus(1)
	main()