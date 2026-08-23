// #ifndef __MEM_NVMAIN_MEMORY_HH__
// #define __MEM_NVMAIN_MEMORY_HH__

// #include "mem/abstract_mem.hh"
// #include "mem/port.hh"
// #include "params/NVMainMemory.hh"
// #include "NVM/nvmain.h"
// #include "src/Config.h"
// #include "src/SimInterface.h"
// #include "SimInterface/NullInterface/NullInterface.h"

// namespace gem5 {
// namespace memory {

// class NVMainMemory : public AbstractMemory
// {
//   private:
//     NVM::NVMain *nvmain_engine;
//     NVM::Config *nvmain_config;
//     class NVMainPort : public ResponsePort {
//       private:
//         NVMainMemory *mem;
//       public:
//         // Modern constructor: just name and owner
//         NVMainPort(const std::string& _name, NVMainMemory* _mem)
//             : ResponsePort(_name), mem(_mem) {}
//       protected:
//         Tick recvAtomic(PacketPtr pkt) override { return mem->recvAtomic(pkt); }
//         void recvFunctional(PacketPtr pkt) override { mem->recvFunctional(pkt); }
//         bool recvTimingReq(PacketPtr pkt) override { return mem->recvTimingReq(pkt); }
//         void recvRespRetry() override { }

//         AddrRangeList getAddrRanges() const override { 
//             return {mem->getAddrRange()}; 
//         }
//     };

//     NVMainPort port;

//   public:
//     typedef NVMainMemoryParams Params;
//     NVMainMemory(const Params &p);
//     virtual ~NVMainMemory();
//     void init() override;

//     Port &getPort(const std::string &if_name, PortID idx = InvalidPortID) override;

//     Tick recvAtomic(PacketPtr pkt);
//     void recvFunctional(PacketPtr pkt);
//     bool recvTimingReq(PacketPtr pkt);
// };

// } // namespace memory
// } // namespace gem5

// #endif

#ifndef __MEM_NVMAIN_MEMORY_HH__
#define __MEM_NVMAIN_MEMORY_HH__

#include "mem/abstract_mem.hh"
#include "params/NVMainMemory.hh"

namespace gem5 {
namespace memory {

class NVMainMemory : public AbstractMemory
{
  public:
    NVMainMemory(const NVMainMemoryParams &p);
    virtual ~NVMainMemory();

    Port &getPort(const std::string &if_name, PortID idx = InvalidPortID) override;
    void init() override;
};

} // namespace memory
} // namespace gem5

#endif