import m5
from m5.objects import *
import argparse

# 1. Parse our custom arguments
parser = argparse.ArgumentParser(description="MBMM gem5+NVMain Execution Script")
parser.add_argument("--cmd", type=str, required=True, help="Executable path")
parser.add_argument("--options", type=str, default="", help="Executable options")
parser.add_argument("--nvmain-config", type=str, required=True, help="Path to NVMain config")
parser.add_argument("--maxinsts", type=int, default=10000000, help="Max instructions to simulate")
args = parser.parse_args()

# 2. Build the System Motherboard
system = System()
system.clk_domain = SrcClockDomain(clock='1GHz', voltage_domain=VoltageDomain())
system.mem_mode = 'timing'
system.mem_ranges = [AddrRange('2GB')]

# 3. Setup CPU and Memory Bus
system.cpu = TimingSimpleCPU()
system.membus = SystemXBar()

# Connect CPU to the bus (no caches for this baseline bridge test)
system.cpu.icache_port = system.membus.cpu_side_ports
system.cpu.dcache_port = system.membus.cpu_side_ports

# X86 specific Interrupt Controller setup
system.cpu.createInterruptController()
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports
system.system_port = system.membus.cpu_side_ports

# 4. Integrate NVMain ReRAM Module
# Setting system.mem_ctrl explicitly fixes the "orphan node" error
system.mem_ctrl = NVMainMemory()
system.mem_ctrl.range = system.mem_ranges[0]
system.mem_ctrl.nvmain_config = args.nvmain_config

# Wire the ReRAM module to the memory bus
system.mem_ctrl.port = system.membus.mem_side_ports

# 5. Workload Setup (SPEC MCF)
process = Process()
process.executable = args.cmd
process.cmd = [args.cmd, args.options]
system.cpu.workload = process
system.cpu.createThreads()

# Modern gem5 requirement for Syscall Emulation mode
system.workload = SEWorkload.init_compatible(args.cmd)

# 6. Execute Simulation
root = Root(full_system=False, system=system)
m5.instantiate()

print(f"\n--- Starting MBMM Simulation: {args.cmd} ---")
exit_event = m5.simulate(args.maxinsts)
print(f"--- Exited @ tick {m5.curTick()} | Reason: {exit_event.getCause()} ---\n")