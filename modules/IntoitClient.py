import socket
from pathlib import Path
from os import listdir, rename, remove
from os.path import isfile, join

MAX_BUFFER_SIZE = 512

class Intoit_Client:

    name = ''
    err_desc = ''
    err_num = ''
    file_dir = ''

    file_num = 0

    file_event = 0
    status_event = 0

    max_files = 3
    
    def __init__(self, client, addr, file_dir, max_files, status_period, file_period, recording_length):
        self.client_container = client
        self.ipv4_addr = addr
        self.file_dir = file_dir
        self.status_period = status_period
        self.file_period = file_period
        self.recording_length = recording_length
        self.max_files = max_files
        self.Request_Status()
        self.Request_LengthChange()

    def Close(self):
        self.client_container.close()

    def Send_Data(self, binary_string):
        #binary_string = bytes(string_to_send, 'ascii')
        size = len(binary_string).to_bytes(2, 'little')
        return self.client_container.send(size + binary_string)

    def Receive_Data(self):
        #receive size
        received_data = b''
        size = int.from_bytes(self.client_container.recv(2), 'little')
        bytes_left = size
        while bytes_left > 0:
            new_data = self.client_container.recv(size)
            received_data += new_data
            bytes_left -= len(new_data)

        return received_data

    def Get_New_File_Name(self):
        directory = self.file_dir + self.name + "/"
        base_filename = self.name
        files = [f for f in listdir(directory) if isfile(join(directory, f))]

        files = [f for f in files if f.endswith(".wav")]
        #make sure we aren't at max files
        if(len(files) >= self.max_files):
            print("Directory is at max files")
            return "FULL"
        elif(len(files) > 0):
            #if there are files, check if _0 file exists, if it does, new file should be last _i (_2 if _1 is last, _1 if only _0)
            if((base_filename + "_0.wav") not in files):

                for i in range(len(files)):
                    try:
                        rename(directory + base_filename + "_" + str(i+1) + ".wav", directory + base_filename + "_" + str(i) + ".wav")
                    except OSError:
                        pass

            return directory + base_filename + "_" + str(len(files)) + ".wav"

        else:
            #there are no files so return the _0 version
            return directory + base_filename + "_0.wav"
            
    def Receive_File(self, file_dir):

        size = int.from_bytes(self.client_container.recv(4), 'little')
        bytes_left = size

        with open(file_dir, 'wb') as file:
            self.file_num += 1
            while bytes_left > 0:
                new_data = b''
                if(bytes_left > MAX_BUFFER_SIZE):
                    new_data = self.client_container.recv(MAX_BUFFER_SIZE)
                else:
                    new_data = self.client_container.recv(bytes_left)
                
                file.write(new_data)
                bytes_left -= len(new_data)


    #Function to request status:
    #send "REQSTATUS", await "ACK[device name]:[error desc]:[error code]"
    #if no device name stored, store it and create file directory ./[device_name]
    def Request_Status(self):
        request_string = bytes("REQSTAT", 'ascii')
        self.Send_Data(request_string)
        data = self.Receive_Data().decode('ascii')
        if(data == "ACK"):
            pass
        if(data == "NAK"):
            return -1


        data=self.Receive_Data().decode('ascii')
        split_data = data.split(':')

        if(len(split_data) != 3):
            return -1

        
        if(self.name == ''):
            self.name = split_data[0]
            Path(self.file_dir+self.name).mkdir(parents=True, exist_ok=True)
        
        self.err_desc = split_data[1]
        self.err_num = split_data[2]

        print("Device Name: " + self.name + "\tError State: " + self.err_desc)



    def Request_File(self):


        # test code for auto deleting _0 files
   #     try:
  #          remove(self.file_dir + self.name + "/" + self.name + "_0.wav")
 #       except OSError:
#            pass

        file_name = self.Get_New_File_Name()
        if(file_name == "FULL"):
            return

        request_string = bytes("REQFILE", 'ascii')
        self.Send_Data(request_string)
        data = self.Receive_Data().decode('ascii')
        if(data == "ACK"):
            print("Device Name: " + self.name + "\tFile Name: " + file_name)
            self.Receive_File(file_name)
        elif(data == "NAK"):
            pass


    def Request_LengthChange(self):

        request_string = bytes("REQLENG", 'ascii') + self.recording_length.to_bytes(4, 'little')
        self.Send_Data(request_string)
        data = self.Receive_Data().decode('ascii')
        if(data == "ACK"):
            print("Device Name: " + self.name + '\tRecording Length: ' + str(self.recording_length))
        
