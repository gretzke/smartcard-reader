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
# import card parser
from card.ICC import *
from card.utils import *
# other imports
from time import sleep
import sys

# callbacks for global Event handling
_callbacks = {}





# main function
def main():
    # set event handlers
    Event.on('insert', cardInsert)
    Event.on('remove', cardRemove)
    
    print('Scanning for cards')
    cardmonitor = CardMonitor()
    cardobserver = Observer()
    cardmonitor.addObserver(cardobserver)
    # remove the cardmonitor afterwards
    # cardmonitor.deleteObserver(cardobserver)

    while True:
        continue
    

def cardInsert(atr):
    
    try:
        a = ISO7816()
        a.ATR_scan()
        
    except smartcard.Exceptions.CardConnectionException as e:
        print(e)
        
    return


def cardRemove():
    return


class EMV(ISO7816):
    dbg = 2
    
    # AID RID & PIX codes taken from wikipedia
    AID_RID = {
        (0xA0, 0x00, 0x00, 0x00, 0x03): 'Visa',
        (0xA0, 0x00, 0x00, 0x00, 0x04): 'MasterCard',
        (0xA0, 0x00, 0x00, 0x00, 0x05): 'MasterCard',
        (0xA0, 0x00, 0x00, 0x00, 0x25): 'American Express',
        (0xA0, 0x00, 0x00, 0x00, 0x29): 'LINK ATM (UK)',
        (0xA0, 0x00, 0x00, 0x00, 0x42): 'CB (FR)',
        (0xA0, 0x00, 0x00, 0x00, 0x65): 'JCB (JP)',
        (0xA0, 0x00, 0x00, 0x01, 0x21): 'Dankort (DN)',
        (0xA0, 0x00, 0x00, 0x01, 0x41): 'CoGeBan (IT)',
        (0xA0, 0x00, 0x00, 0x01, 0x52): 'Diners Club', # 'Discover'
        (0xA0, 0x00, 0x00, 0x01, 0x54): 'Banrisul (BR)',
        (0xA0, 0x00, 0x00, 0x02, 0x28): 'SPAN2 (SA)',
        (0xA0, 0x00, 0x00, 0x02, 0x77): 'Interac (CA)',
        (0xA0, 0x00, 0x00, 0x03, 0x33): 'China UnionPay',
        (0xA0, 0x00, 0x00, 0x03, 0x59): 'ZKA (DE)',
        }
    
    AID_Visa_PIX = {
        (0x10, 0x10): 'credit or debit',
        (0x20, 0x10): 'Electron',
        (0x20, 0x20): 'V Pay',
        (0x80, 0x10): 'Plus',
        }
    
    AID_MasterCard_PIX = {
        (0x10, 0x10): 'credit or debit',
        (0x99, 0x99): 'paypass',
        (0x30, 0x60): 'Maestro',
        (0x60, 0x00): 'Cirrus',
        }
    
    AID_ChinaUnionPay_PIX = {
        (0x01, 0x01, 0x01): 'debit',
        (0x01, 0x01, 0x02): 'credit',
        (0x01, 0x01, 0x03): 'quasi credit',
        }
    
    
    def __init__(self):
        '''
        initializes like an ISO7816-4 card with CLA=0x00
        and check available AID (Application ID) read straight after card init
        '''
        ISO7816.__init__(self, CLA=0x00)
        self.AID = []
        
        if self.dbg >= 2:
            log(3, '(UICC.__init__) type definition: %s' % type(self))
            log(3, '(UICC.__init__) CLA definition: %s' % hex(self.CLA))
    
    
    def get_AID(self):
        '''
        checks AID straight after card init, 
        and read available AID (Application ID) referenced
        
        puts it into self.AID
        '''
        # read record to get EMV Application DF supported by the ICC
        recs = []
        SFI = 1 # I dont know exactly why... but it works, at least
        index = 1
        while True:
            ret = self.READ_RECORD(P1=index, P2=(SFI<<3)|4)
            index += 1
            if ret[2] == (0x90, 0x0):
                recs.append(ret[3])
            else:
                break
        
        for rec in recs:
            # try to interpret EMV AID
            if (rec[0], rec[2]) == (0x70, 0x61) and len(rec) >= 11 \
            and rec[6:6+rec[5]] not in self.AID:
                self.AID.append( rec[6:6+rec[5]] )
            if self.dbg:
                log(3, '(EMV.__init__) AID found: %s' % EMV.interpret_AID(self.AID[-1]))
    
    @staticmethod
    def interpret_AID(aid=[]):
        aid = tuple(aid)
        inter = ''
        if aid[:5] in self.AID_RID:
            inter = self.AID_RID[aid[:5]]
            if aid[:5] == (0xA0, 0x00, 0x00, 0x00, 0x03):
                inter += ' - %s' % self.AID_Visa_PIX
            elif aid[:5] in ((0xA0, 0x00, 0x00, 0x00, 0x04), \
                             (0xA0, 0x00, 0x00, 0x00, 0x05)):
                inter += ' - %s' % self.AID_MasterCard_PIX
            elif aid[:5] in (0xA0, 0x00, 0x00, 0x03, 0x33):
                inter += ' - %s' % self.AID_ChinaUnionPay_PIX
        else:
            inter = 'unkown EMV AID'
        
        return inter


class Observer(CardObserver):
    '''
    Class for a simple card observer that detects insertion or removal of cards
    '''
    def update(self, observable, actions):
        (addedcards, removedcards) = actions
        for card in addedcards:
            print("+Inserted: ", toHexString(card.atr))
            Event.emit('insert', toHexString(card.atr))
            
        for card in removedcards:
            print("-Removed:  ", toHexString(card.atr))
            Event.emit('remove')


class SecureChannelConnection(CardConnectionDecorator):
    '''
    mockup of a secure channel connection.
    It merely pretends to cypher/uncypher upon apdu transmission.
    '''

    def __init__(self, cardconnection):
        CardConnectionDecorator.__init__(self, cardconnection)

    def cypher(self, bytes):
        
        # Cypher mock-up; you would include the secure channel logics here.
        
        print('cyphering', toHexString(bytes))
        return bytes

    def uncypher(self, data):
        
        # Uncypher mock-up. Todo: include secure channel logics
        
        print('uncyphering', toHexString(data))
        return data

    def transmit(self, bytes, protocol=None):
        
        # Cypher/uncypher APDUs before transmission
        
        cypheredbytes = self.cypher(bytes)
        data, sw1, sw2 = CardConnectionDecorator.transmit(self, cypheredbytes, protocol)
        if [] != data:
            data = self.uncypher(data)
        return data, sw1, sw2


class Event():

    @staticmethod
    def on(event_name, f):
        _callbacks[event_name] = _callbacks.get(event_name, []) + [f]
        return f

    @staticmethod
    def emit(event_name, *data):
        [f(*data) for f in _callbacks.get(event_name, [])]

    @staticmethod
    def off(event_name, f):
        _callbacks.get(event_name, []).remove(f)
        

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\ncleaning up...')
        sys.exit(0)
