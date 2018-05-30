#! /usr/bin/env python

# smartcard imports
import smartcard
from smartcard.System import readers
from smartcard.util import toHexString, toBytes
# ATR imports
from smartcard.ATR import ATR
from smartcard.CardType import ATRCardType, AnyCardType
from smartcard.CardRequest import CardRequest
# APDU Tracing imports
from smartcard.CardConnectionObserver import ConsoleCardConnectionObserver
from smartcard.CardConnectionDecorator import CardConnectionDecorator
# Card monitoring
from smartcard.CardMonitoring import CardMonitor, CardObserver

'''
Connects to the first card reader
'''
def simpleConnection():
    
    r = readers()
    # get list of smart card readers
    if len(r) == 0:
        print('No reader found')
        return
    
    print(r)

    connection = r[0].createConnection()

    # connect to first card reader
    try:
        connection.connect()
        print('Card detected')
    except smartcard.Exceptions.NoCardException:
        print('No reader/card connected')
        return
    except smartcard.Exceptions.CardConnectionException as e:
        print(e)
        return


'''
The first answer of a smart card inserted in a smart card reader is call the ATR. The purpose of the ATR is to describe the supported communication parameters.
The smart card reader, smart card reader driver, and operating system will use these parameters to establish a communication with the card. The ATR is described in the ISO7816-3 standard.
The first bytes of the ATR describe the voltage convention (direct or inverse), followed by bytes describing the available communication interfaces and their respective parameters.
These interface bytes are then followed by Historical Bytes which are not standardized, and are useful for transmitting proprietary information such as the card type, the version of the embedded software, or the card state.
Finally these historical bytes are eventually followed by a checksum byte.
'''
def getATR():
    
    atr = ATR([0x3B, 0x9E, 0x95, 0x80, 0x1F, 0xC3, 0x80, 0x31, 0xA0, 0x73, 0xBE, 0x21, 0x13, 0x67, 0x29, 0x02, 0x01, 0x01, 0x81, 0xCD, 0xB9])

    print(atr)
    print('historical bytes: ', toHexString(atr.getHistoricalBytes()))
    print('checksum: ', "0x%X" % atr.getChecksum())
    print('checksum OK: ', atr.checksumOK)
    print('T0  supported: ', atr.isT0Supported())
    print('T1  supported: ', atr.isT1Supported())
    print('T15 supported: ', atr.isT15Supported())    

'''
request a card by a specific card type (ATR)
'''
def requestByATR(atr):
    print('\n========== REQUEST BY ATR ==========\n')
    # example: ATR of German ID Card, only works with ISO 14443 devices
    # cardtype = ATRCardType(toBytes("3B 88 80 01 00 00 00 00 00 00 00 00 09"))
    cardtype = ATRCardType(toBytes(atr))
    # also supports masks
    # cardtype = ATRCardType( toBytes( "3B 15 94 20 02 01 00 00 0F" ), toBytes( "00 00 FF FF FF FF FF FF 00" ) )
    cardrequest = CardRequest(timeout=1, cardType=cardtype)
    try:
        cardservice = cardrequest.waitforcard()
        print('Card detected successfully')
        return True
    except smartcard.Exceptions.CardRequestTimeoutException:
        print('Wrong card type')
        return False
    
    cardservice.connection.connect()
    print(toHexString(cardservice.connection.getATR()))

'''
Card connection observers to trace apdu transmission
'''
def connectionObserver():
    # request any card type
    cardtype = AnyCardType()
    cardrequest = CardRequest(timeout=1, cardType=cardtype)
    cardservice = cardrequest.waitforcard()

    observer=ConsoleCardConnectionObserver()
    cardservice.connection.addObserver(observer)
    
    cardservice.connection.connect()
    print('ATR: ' + toHexString(cardservice.connection.getATR()))
    # get reader used for the connection
    # device = cardservice.connection.getReader()


    GET_RESPONSE = [0XA0, 0XC0, 00, 00 ]
    SELECT = [0xA0, 0xA4, 0x00, 0x00, 0x02]
    DF_TELECOM = [0x7F, 0x10]
    
    apdu = SELECT+DF_TELECOM
    response, sw1, sw2 = cardservice.connection.transmit(apdu)
    if sw1 == 0x9F:
            apdu = GET_RESPONSE + [sw2]
            response, sw1, sw2 = cardservice.connection.transmit(apdu)
    else:
        print('no DF_TELECOM')
