import time
import sched
from modules import IntoitClient, IntoitServer
import threading
import configparser

#Config file loading info
config_file = "configuration.ini"
config_server_section = "server.config"
config_device_section = "device.config"


stop_all_threads = 0

def thread_close(scheduler, client):
    print("Disconnecting ", client.name, " @ ", client.ipv4_addr)

    try:
        scheduler.cancel(client.file_event)
    except:
        pass

    try:
        scheduler.cancel(client.status_event)
    except:
        pass


    client.Close()

def request_status(scheduler, client):
    global stop_all_threads

    if(stop_all_threads == 1):
        scheduler.enter(1, 0, thread_close, (scheduler, client))    
        return

    client.status_event = scheduler.enter(client.status_period, 1, request_status, (scheduler, client))
    client.Request_Status()


def request_file(scheduler, client):
    global stop_all_threads

    if(stop_all_threads == 1):
        scheduler.enter(1, 0, thread_close, (scheduler, client))    
        return

    client.file_event = scheduler.enter(client.file_period, 1, request_file, (scheduler, client))
    client.Request_File()

def client_handler_thread(scheduler, client):
    client.file_event = scheduler.enter(client.file_period, 1, request_file, (scheduler, client))
    client.status_event = scheduler.enter(client.status_period, 1, request_status, (scheduler, client))

    try: 
        scheduler.run()
    except:
        thread_close(scheduler, client)
        return 

#needed config stuff:
    #MAX_threads
    #recording length
    #recording period
    #status period
    #port
    #host ip
    #file_dir

def main():
    global stop_all_threads, config_file, config_device_section, config_server_section

    config = configparser.ConfigParser()
    config.read(config_file)

    host = config.get(config_server_section, 'IP')
    port = config.getint(config_server_section, 'Port')
    
    request_file_period = config.getint(config_server_section, 'RecordingPeriod_s')
    request_status_period = config.getint(config_server_section, 'StatusPeriod_s')
    file_dir = config.get(config_server_section, 'FileDir')

    max_files_per = config.getint(config_server_section, 'MaxFiles')
    MAX_THREADS = config.getint(config_server_section, 'MaxThreads')

    #TODO DCK: Make this a device configuration that gets set during connect handshake  
    recording_length = config.getint(config_device_section, 'RecordingLength_ms')

    schedulers = []
    threads = []
    clients = []

    #int to hold number of running threads
    live_threads = 0

    server_host = IntoitServer.Intoit_Server(host, port)

    while True:
        try: 
            #try connection
            client, address = server_host.Await_Connection()

            #if a client did connect, create new thread to handle client
            if(client != None):
                print("Connected from: ", address) 

                #append to clients and schedulers
                clients.append(IntoitClient.Intoit_Client(client, address, file_dir, max_files_per, request_status_period, request_file_period, recording_length))
                schedulers.append(sched.scheduler(time.time, time.sleep))

                #raise error if we at max threads and close most recent connection
                if(live_threads >= MAX_THREADS):
                    schedulers.pop()
                    clients.pop().Close()
                    raise MemoryError("Max threads reached")


                t = threading.Thread(target=client_handler_thread, args=(schedulers.pop(), clients.pop()))
                t.daemon = True
                t.start()
                threads.append(t)
            
            
            for t in threads:
                #try and join all threads
                t.join(0.01)

            
            #prune threads for alive ones
            threads = [t for t in threads if t.is_alive()]
            live_threads = len(threads)

        except MemoryError:
            printf("Max threads reached, not accepting new connections")
            sleep(10)

        except KeyboardInterrupt:
            print("Closing server...")
            stop_all_threads = 1

            if(len(clients) > 0):
                cleints.pop().Close()


            for t in threads:
                t.join()

            server_host.Close()
            return

            


if __name__ == "__main__":
    print("Running Server")
    main()