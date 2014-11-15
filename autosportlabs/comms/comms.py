import traceback
import threading
import multiprocessing
from Queue import Empty
from time import sleep
class PortNotOpenException(Exception):
    pass

class CommsErrorException(Exception):
    pass



def connection_process_message_reader(rx_queue, connection, should_run):
    print('connection process message reader started')
    
    while should_run.is_set():
        try:
            msg = connection.read_line()
            if msg:
                print('got message: ' + str(msg))
                rx_queue.put(msg)
        except:
            print('Exception in connection_process_message_reader')
            traceback.print_exc()
            #_rx_queue.put('##ERROR##')
            sleep(0.5)
    print('connection process message reader exited')            
            
def connection_process_message_writer(tx_queue, connection, should_run):
    print('connection process message writer started')
    while should_run.is_set():
        try:
            message = tx_queue.get(True, 1.0)
            if message:
                connection.write(message)
        except Empty:
            pass
        except Exception as e:
            print('Exception in connection_process_message_writer ' + str(e))
            traceback.print_exc()
            sleep(0.5)
    print('connection process message writer exited')
    
def connection_message_process(connection, port, rx_queue, tx_queue, command_queue):
    print('connection process starting')

    try:    
        connection.open(port) 
        connection.flushInput()
        connection.flushOutput()
        
        reader_writer_should_run = threading.Event()
        reader_writer_should_run.set()
    
        reader_thread = threading.Thread(target=connection_process_message_reader, args=(rx_queue, connection, reader_writer_should_run))
        reader_thread.start()
        
        writer_thread = threading.Thread(target=connection_process_message_writer, args=(tx_queue, connection, reader_writer_should_run))
        writer_thread.start()
        
        should_run = True
        while should_run:
            try:
                command = command_queue.get()
                if command == 'close':
                    print('connection process: got close command')
                    should_run = False
            except Empty:
                print('no command received')
        print('connection worker exiting')
        
        reader_writer_should_run.clear()
        reader_thread.join()
        writer_thread.join()

        try:
            connection.close()
        except:
            print('Exception closing connection worker connection')
    except Exception as e:
        print("Exception setting up connection process: " + str(type(e)) + str(e))
        traceback.print_exc()
        
    print('connection worker exited')
    
    
class Comms():
    DEFAULT_TIMEOUT = 1.0
    _timeout = DEFAULT_TIMEOUT
    port = None
    _connection = None
    _connection_process = None
    _rx_queue = None
    _tx_queue = None
    _command_queue = None    
    
    
    def __init__(self, **kwargs):
        self.port = kwargs.get('port')
        self._connection = kwargs.get('connection')

    def start_connection_process(self):
        rx_queue = multiprocessing.Queue()
        tx_queue = multiprocessing.Queue()
        command_queue = multiprocessing.Queue()    
        connection_process = multiprocessing.Process(target=connection_message_process, args=(self._connection, self.port, rx_queue, tx_queue, command_queue))
        connection_process.start()
        self._rx_queue = rx_queue
        self._tx_queue = tx_queue
        self._command_queue = command_queue
        self._connection_process = connection_process
        
                                
    def get_available_ports(self):
        return self._connection.get_available_ports()
    
    def isOpen(self):
        return self._connection_process != None and self._connection_process.is_alive()
    
    def open(self):
        connection = self._connection
        print('Opening connection ' + str(self.port))
        self.start_connection_process()
    
    def close(self):
        print('comms.close()')
        connection = self._connection
        if self.isOpen():
            try:
                print('closing connection process')
                self._command_queue.put_nowait('close')
                self._connection_process.join(self._timeout * 2)
                print('connection process joined')
            except:
                print('Timeout joining connection process')

    def read_message(self):
        try:
            return self._rx_queue.get(True, self._timeout)
        except: #returns Empty object if timeout is hit
            return None
    
    def write_message(self, message):
        self._tx_queue.put(message)
                    