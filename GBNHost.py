from Simulator import Simulator, Packet, EventEntity
from enum import Enum
from struct import pack, unpack



class GBNHost():

    # The __init__ method accepts:
    # - a reference to the simulator object
    # - the name for this entity (EntityType.A or EntityType.B)
    # - the interval for this entity's timer
    # - the size of the window used for the Go-Back-N algorithm
    def __init__(self, simulator, entity, timer_interval, window_size):
        
        # These are important state values that you will need to use in your code
        self.simulator = simulator
        self.entity = entity
        
        # Sender properties
        self.timer_interval = timer_interval        # The duration the timer lasts before triggering
        self.window_size = window_size              # The size of the seq/ack window
        self.last_ACKed = 0                         # The last ACKed packet. This starts at 0 because no packets 
                                                    # have been ACKed
        self.current_seq_number = 1                 # The SEQ number that will be used next
        self.app_layer_buffer = []                  # A buffer that stores all data received from the application 
                                                    #layer that hasn't yet been sent
        self.unACKed_buffer = {}                    # A buffer that stores all sent but unACKed packets

        # Receiver properties
        self.expected_seq_number = 1                # The next SEQ number expected
        self.last_ACK_pkt = self.createACK(0)       # The last ACK pkt sent. 
                                                    # TODO: This should be initialized to an ACK response with an
                                                    #       ACK number of 0. If a problem occurs with the first
                                                    #       packet that is received, then this default ACK should 
                                                    #       be sent in response, as no real packet has been rcvd yet
        self.max_seq_number = 0

    ###########################################################################################################
    ## Core Interface functions that are called by Simulator

    # This function implements the SENDING functionality. It should implement retransmit-on-timeout. 
    # Refer to the GBN sender flowchart for details about how this function should be implemented
    # NOTE: DIFFERENCE FROM GBN FLOWCHART
    #       If this function receives data to send while it does NOT have an open slot in the sending window,
    #       it should store this data in self.app_layer_buffer. This data should be immediately sent
    #       when slots open up in the sending window.



    #pkt = pack("!iiH>i%is" % len(payload), # build string with a number, seq_num, 0, 0x0000, False, len(payload), payload.encode())
    def receive_from_application_layer(self, payload):


        if self.current_seq_number < (self.last_ACKed +  self.window_size):
            
            #create packet
            pkt = self.create_packet(payload)

            self.send_packet(pkt)

            #check if base packet
            if self.last_ACKed + 1 == self.current_seq_number:
                self.simulator.start_timer(self.entity, self.timer_interval)
            
            self.current_seq_number += 1
        else:
            self.app_layer_buffer.append(payload)


    # This function implements the RECEIVING functionality. This function will be more complex that
    # receive_from_application_layer(), as it must process both packets containing new data, and packets
    # containing ACKs. You will need to handle received data differently depending on if it is an ACK
    # or a packet containing data. 
    # Refer to the GBN receiver flowchart for details about how to implement responding to data pkts, and
    # refer to the GBN sender flowchart for details about how to implement responidng to ACKs
    def receive_from_network_layer(self, byte_data):

        isCorrupt = None
        tcp_header = None
        tcp_payload = None
        #unpack byte_data
        
        try:

            isCorrupt = (self.getChecksum(byte_data) != 0)
            
            if isCorrupt == False:
                tcp_header = unpack("!iiH?i", byte_data[:15])
                tcp_payload = self.unpack_packet(tcp_header, byte_data)
            #Corrupt when != 0
            
         
        except:
            isCorrupt = True
        #check for corruption
        

    

        #pkt = pack("!iiH?i%is" % tcp_header[4], tcp_payload[0], tcp_payload[1], 0x0000, tcp_payload[3], tcp_payload[4], tcp_payload[5])
        #isCorrupt = self.checkChecksum(pkt, tcp_payload[2])


       
        if isCorrupt:
            print(str(self.entity) + ":\t has received COURRUPTION")

            self.simulator.to_layer3(self.entity, self.last_ACK_pkt, True)
        




        if isCorrupt == False:

        # [ SEQ# , ACK# , CHECKSUM , ACK_FLAG , PAY_LEN, PAYLOAD ] 
            formatted_data = self.createMap(tcp_payload)
            
            #determine to invoke GBN_receiver or GBN_sender
            if formatted_data["ACK_FLAG"]:
                #GBN_Sender Functionality
                print(":\t has received the ACKNOWLEDGEMENT: " + str(formatted_data["ACK#"]))
                #Did the last ack packet acknowledge my data

                #remove packet from buffer
                #I can remove all remove all unacked data upto the formatted_data[ACK#]
                for ack_num in range(self.last_ACKed, formatted_data["ACK#"]+1):
                    if ack_num in self.unACKed_buffer:
                        self.simulator.stop_timer(self.entity)
                        del self.unACKed_buffer[ack_num] 

                if formatted_data["ACK#"] > self.last_ACKed:
                    print(":\t ACKNOWLEDGEMENT CORRECT")
                     
                    #Increase the base to the the acked packet
                    self.last_ACKed = formatted_data["ACK#"]
                    
                    #send data awaiting to be sent in append buffer.
                    if len(self.app_layer_buffer) > 0:
                        self.simulator.start_timer(self.entity, self.timer_interval)
                        self.fill_window()
                    #check for if data is still unAcked
                    if len(self.unACKed_buffer) > 0:
                        self.simulator.stop_timer(self.entity)
                        self.simulator.start_timer(self.entity, self.timer_interval)
                else:
                    print(":\t ACKNOWLEDGEMENT OUT OF ORDER")
                    #self.simulator.stop_timer(self.entity)
                    #self.simulator.start_timer(self.entity, self.simulator.timer_interval)
                   
            else:
                #GBN_Receiver Functionality
                print(":\t has received the message: " + formatted_data["PAYLOAD"])
                print(":\t message SEQ#: " + str(formatted_data["SEQ#"]))
                #send data to applicaiton
                is_ack = True
                #check if I'm expecting this data
                if formatted_data["SEQ#"] == self.expected_seq_number:
                    self.simulator.to_layer5(self.entity, formatted_data["PAYLOAD"])
                    #send acknowledgement to sending Entity
                    ack_packet = self.createACK(self.expected_seq_number)
                    self.simulator.to_layer3(self.entity, ack_packet, is_ack)
                    #increase expectedseqnum
                    self.expected_seq_number = formatted_data["SEQ#"] + 1
                    self.last_ACK_pkt = ack_packet           
                else:
                    self.simulator.to_layer3(self.entity, self.last_ACK_pkt, is_ack)

                

                


    # This function is called by the simulator when a timer interrupt is triggered due to an ACK not being 
    # received in the expected time frame. All unACKed data should be resent, and the timer restarted
    def timer_interrupt(self):
        
        self.simulator.start_timer(self.entity, self.simulator.timer_interval)

        for pkt in self.unACKed_buffer.values():
            self.simulator.to_layer3(self.entity, pkt)

        if len(self.unACKed_buffer) == 0:
            self.simulator.stop_timer(self.entity)
        
        
        

    #compute checksum on string 
    def getChecksum(self, pkt):
    
        checksum = 0

        #if packet length is odd in bytes
        if len(pkt) % 2 != 0:
            pkt += b'\x00'

        #get ones comp
        for i in range(0, len(pkt), 2):
            
            #create 16 bit word
            word = pkt[i] << 8 | pkt [i+1]

            #add it to the checkSum
            checksum += word
            #add back the carry bit
            checksum = (checksum & 0xffff) + (checksum >> 16)


  

        checksum = ~checksum


        return checksum & 0xFFFF

    #check if pkt has correct checksum value
    def checkChecksum(self, pkt, checksum):

        #if packet length is odd in bytes
        if len(pkt) % 2 != 0:
            pkt += b'\x00'

        total = 0      
        #get ones comp
        for i in range(0, len(pkt), 2):
            
            #create 16 bit word
            word = pkt[i] << 8 | pkt [i+1]

            #add it to the checkSum
            total += word
            #add back the carry bit
            total = (total & 0xffff) + (total >> 16)
        
        total += checksum

        #total should be equal to 65535
        if total == 65535 :
            return False

        return True

    def createMap(self, data):
        # [ SEQ# , ACK# , CHECKSUM , ACK_FLAG , PAY_LEN, PAYLOAD ] 
        extraction = {}
        extraction["SEQ#"] = data[0]
        extraction["ACK#"] = data[1]
        extraction["CHECKSUM"] = data[2]
        extraction["ACK_FLAG"] = data[3]
        extraction["PAY_LEN"] = data[4]
        extraction["PAYLOAD"] = data[5].decode()

        return extraction

    #create ACK packet with corresponding ACK_NuM
    def createACK(self, ACK_NUM,):
        
        packet = pack("!iiH?i", 0, ACK_NUM, 0x0000, True, 0)
        checksum = self.getChecksum(packet)
        return pack("!iiH?i", 0, ACK_NUM, checksum, True, 0)
    
    #unpack the byte_data transmitted from layer_3
    def unpack_packet(self, tcp_header,  byte_data):
        is_ack = tcp_header[3]

        if is_ack:
            #if ack_packet
            tcp_payload = tcp_header + ("".encode(),)
        else:

            try:
                tcp_payload = unpack("!iiH?i%is" % tcp_header[4], byte_data)
            except:
                tcp_payload = None

        return tcp_payload


    #Create TCP packet 
    def create_packet(self, payload):
        #Calculate Checksum      
        pkt = pack("!iiH?i%is" % len(payload), self.current_seq_number, 0, 0x0000, False, len(payload), payload.encode())
        checksum = self.getChecksum(pkt) 


        # populate header
        # [ SEQ# , ACK # , Checksum , ACK Flag , Payload Length in bytes, Payload] 
        pkt = pack("!iiH?i%is" % len(payload), self.current_seq_number, 0, checksum, False, len(payload), payload.encode())
        return pkt

    
    #send TCP packet
    def send_packet(self, packet):
        #send packed pkt to layer 3
        self.simulator.to_layer3(self.entity, packet)
        #append packet to unAcked_buffer
        self.unACKed_buffer[self.current_seq_number] = packet

    #Fill the sliding window with data from 'self.app_layer_buffer'
    def fill_window(self):

        #see if data is available for sending.
        while len(self.app_layer_buffer) > 0:
            
            #How much space is in the window
            window_space = (self.last_ACKed + self.window_size) - self.current_seq_number
            if window_space > 0:
                #get next buffered message to send
                payload = self.app_layer_buffer.pop(0)
                message = self.create_packet(payload)
                print(":\t SEND NEW MESSAGE: " + payload)
                self.send_packet(message)
              
                self.current_seq_number += 1
            else:
                break
            

