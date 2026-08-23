#include "sim/eventq.hh"
#include "sim/core.hh"
#include "mem/NVMainMemory.hh"
#include "base/trace.hh"
#include "mem/abstract_mem.hh"
#include "params/NVMainMemory.hh"

namespace gem5 {
namespace memory {

NVMainMemory::NVMainMemory(const NVMainMemoryParams &p) : AbstractMemory(p) {}
NVMainMemory::~NVMainMemory() {}

Port &NVMainMemory::getPort(const std::string &if_name, PortID idx) 
{ 
    return AbstractMemory::getPort(if_name, idx); 
}

void NVMainMemory::init() { AbstractMemory::init(); }

} // namespace memory
} // namespace gem5

// namespace gem5 {
// namespace memory {

// NVMainMemory::NVMainMemory(const NVMainMemoryParams &p)
//     : AbstractMemory(p),
//       port(name() + ".port", this)
// {
//     // 1. Initialize Config
//     nvmain_config = new NVM::Config();
//     nvmain_config->Read(p.nvmain_config); 

//     // 2. Instantiate Engine
//     nvmain_engine = new NVM::NVMain();
    
//     // 3. Create a static global interface to survive the constructor 
//     //    without changing the class size in the header file.
//     static NVM::NullInterface global_null_intf;
//     nvmain_config->SetSimInterface(&global_null_intf);
    
//     // 4. Boot the NVMain engine
//     nvmain_engine->SetConfig(nvmain_config, "defaultMemory", true);

//     std::cout << "MBMM Bridge: Successfully instantiated NVMain using config: " 
//               << p.nvmain_config << std::endl;
// }

// NVMainMemory::~NVMainMemory()
// {

// }

// Port &
// NVMainMemory::getPort(const std::string &if_name, PortID idx)
// {
//     if (if_name == "port") {
//         return port;
//     } else {
//         return AbstractMemory::getPort(if_name, idx);
//     }
// }

// Tick 
// NVMainMemory::recvAtomic(PacketPtr pkt) 
// { 
//     access(pkt);
//     return 0; 
// }

// void 
// NVMainMemory::recvFunctional(PacketPtr pkt) 
// { 
//     // In gem5 v25.1, we simply call access(pkt). 
//     // The packet's internal state handles the rest.
//     access(pkt);
// }

// bool 
// NVMainMemory::recvTimingReq(PacketPtr pkt) 
// { 
//     // 1. Perform the functional access to the backing host memory.
//     // THIS IS CRITICAL: It actually fills the packet with the real MCF instructions/data!
//     access(pkt);

//     // 2. Only construct a response if the CPU actually expects one
//     if (pkt->needsResponse()) {
//         pkt->makeResponse();
        
//         // 3. Placeholder 50ns delay (50000 ticks @ 1THz)
//         Tick response_time = gem5::curTick() + 50000;

//         // 4. Schedule the response back to the CPU
//         schedule(new gem5::EventFunctionWrapper(
//             [this, pkt]{ port.sendTimingResp(pkt); },
//             name() + ".responseEvent", 
//             true // Auto-delete this event after it fires
//         ), response_time);
//     }
    
//     // Always accept the packet
//     return true;
// }

// void
// NVMainMemory::init()
// {
//     // 1. Initialize the base AbstractMemory class
//     AbstractMemory::init();
    
//     // 2. Broadcast our Address Range to the system crossbar
//     if (port.isConnected()) {
//         port.sendRangeChange();
//     }
// }
// } // namespace memory
// } // namespace gem5
