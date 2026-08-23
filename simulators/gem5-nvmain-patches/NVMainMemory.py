from m5.params import *
from m5.proxy import *
from m5.objects.AbstractMemory import *

class NVMainMemory(AbstractMemory):
    type = 'NVMainMemory'
    cxx_header = "mem/NVMainMemory.hh"
    cxx_class = 'gem5::memory::NVMainMemory'
    
    # This is the "plug" the system bus will connect to
    port = ResponsePort("Port for receiving requests from the system bus")
    
    nvmain_config = Param.String("", "Path to NVMain configuration file")