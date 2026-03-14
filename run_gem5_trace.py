import m5
from m5.objects import *
import argparse

parser = argparse.ArgumentParser(description="MBMM gem5 Trace Generation")
parser.add_argument("--cmd", type=str, required=True, help="Executable path")
parser.add_argument("--options", type=str, default="", help="Executable options")
parser.add_argument("--maxinsts", type=int, default=10000000, help="Max instructions")
args = parser.parse_args()

system = System()
system.clk_domain = SrcClockDomain(clock='1GHz', voltage_domain=VoltageDomain())
system.mem_mode = 'timing'
system.mem_ranges = [AddrRange('2GB')]

system.cpu = TimingSimpleCPU()
system.membus = SystemXBar()

system.cpu.icache_port = system.membus.cpu_side_ports
system.cpu.dcache_port = system.membus.cpu_side_ports

system.cpu.createInterruptController()
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports
system.system_port = system.membus.cpu_side_ports

# Use standard DDR4 to safely execute the workload and dump the trace
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR4_2400_8x8(range=system.mem_ranges[0])
system.mem_ctrl.port = system.membus.mem_side_ports

process = Process()
process.executable = args.cmd
process.cmd = [args.cmd, args.options]
system.cpu.workload = process
system.cpu.createThreads()

system.workload = SEWorkload.init_compatible(args.cmd)

root = Root(full_system=False, system=system)
m5.instantiate()

print(f"\n--- Generating Memory Trace for: {args.cmd} ---")
exit_event = m5.simulate(args.maxinsts)
print(f"--- Trace Generation Exited @ tick {m5.curTick()} | Reason: {exit_event.getCause()} ---\n")