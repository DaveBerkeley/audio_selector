#!/bin/env python

# Created by Claud.ai

from amaranth import *
from amaranth.lib.cdc import ResetSynchronizer

class GoWinPLL(Elaboratable):
    """
    GoWin rPLL wrapper for GW1NR-9 FPGA.
    
    Parameters:
    -----------
    input_freq : float
        Input clock frequency in MHz
    output_freqs : dict
        Dictionary of {name: freq_mhz} for each output clock domain
        Example: {"fast": 100.0, "slow": 25.0}
 
    Attributes:
    -----------
    clk_in : Signal, input
        Input clock signal
    rst_in : Signal, input
        Input reset signal
    locked : Signal, output
        PLL locked indicator
    
    Clock domains created:
    ----------------------
    For each entry in output_freqs, a clock domain named with the key
    will be created (e.g., "fast", "slow")
    """
    
    def __init__(self, input_freq, output_freqs):
        self.input_freq = input_freq
        self.output_freqs = output_freqs

        # Calculate PLL parameters for each output
        self.pll_params = {}
        for name, freq in output_freqs.items():
            self.pll_params[name] = self._calculate_pll_params(input_freq, freq)

        # I/O
        self.clk_in = Signal()
        self.rst_in = Signal()
        self.locked = Signal()
        
    def _calculate_pll_params(self, fin, fout):
        """
        Calculate PLL parameters for GoWin rPLL.
        
        rPLL equation: fout = fin * FBDIV / (IDIV * ODIV)
        
        Constraints for GW1NR-9:
        - IDIV: 1-64
        - FBDIV: 1-64
        - ODIV: 1, 2, 4, 8, 16, 32, 48, 64, 80, 96, 112, 128
        - VCO freq: 400-1200 MHz (fvco = fin * FBDIV / IDIV)
        """
        odiv_options = [1, 2, 4, 8, 16, 32, 48, 64, 80, 96, 112, 128]
        
        best_error = float('inf')
        best_params = None
        
        for idiv in range(1, 65):
            for fbdiv in range(1, 65):
                fvco = fin * fbdiv / idiv
                
                # Check VCO constraints
                if fvco < 400 or fvco > 1200:
                    continue
                
                for odiv in odiv_options:
                    calc_fout = fin * fbdiv / (idiv * odiv)
                    error = abs(calc_fout - fout)
                    
                    if error < best_error:
                        best_error = error
                        best_params = {
                            'idiv': idiv,
                            'fbdiv': fbdiv,
                            'odiv': odiv,
                            'actual_freq': calc_fout,
                            'error_mhz': error,
                            'error_pct': (error / fout) * 100
                        }
        
        if best_params is None:
            raise ValueError(f"Cannot generate {fout} MHz from {fin} MHz input")

        return best_params

    def elaborate(self, _):
        m = Module()
        
        # Create a single PLL instance for the first output
        # (GoWin PLLs typically support multiple outputs)
        primary_name = list(self.output_freqs.keys())[0]
        primary_params = self.pll_params[primary_name]
        
        # Create output clock signals
        clk_outputs = {}
        for name in self.output_freqs.keys():
            clk_outputs[name] = Signal(name=f"pll_clk_{name}")
        
        # Instantiate the rPLL primitive
        pll_locked = Signal()
        
        m.submodules.pll = Instance("rPLL",
            # Parameters
            p_FCLKIN=str(self.input_freq),
            p_IDIV_SEL=primary_params['idiv'] - 1,  # 0-based
            p_FBDIV_SEL=primary_params['fbdiv'] - 1,  # 0-based
            p_ODIV_SEL=self._odiv_to_sel(primary_params['odiv']),
            p_DYN_IDIV_SEL="false",
            p_DYN_FBDIV_SEL="false",
            p_DYN_ODIV_SEL="false",
            p_PSDA_SEL="0000",
            p_DYN_DA_EN="false",
            p_DUTYDA_SEL="1000",
            p_CLKOUT_FT_DIR=1,
            p_CLKOUTP_FT_DIR=1,
            p_CLKOUT_DLY_STEP=0,
            p_CLKOUTP_DLY_STEP=0,
            p_CLKFB_SEL="internal",
            p_CLKOUT_BYPASS="false",
            p_CLKOUTP_BYPASS="false",
            p_CLKOUTD_BYPASS="false",
            p_DYN_SDIV_SEL=2,
            p_CLKOUTD_SRC="CLKOUT",
            p_CLKOUTD3_SRC="CLKOUT",
            
            # Ports
            i_CLKIN=self.clk_in,
            i_CLKFB=0,
            i_RESET=self.rst_in,
            i_RESET_P=0,
            i_FBDSEL=0,
            i_IDSEL=0,
            i_ODSEL=0,
            i_PSDA=0,
            i_DUTYDA=0,
            i_FDLY=0,
            
            o_CLKOUT=clk_outputs[primary_name],
            o_LOCK=pll_locked,
            o_CLKOUTP=Signal(),  # 90° phase output (unused)
            o_CLKOUTD=Signal(),  # Divided output (unused)
            o_CLKOUTD3=Signal(), # 3x divided output (unused)
        )
        
        m.d.comb += self.locked.eq(pll_locked)
        
        # Create clock domains for each output
        for name, clk_sig in clk_outputs.items():
            # Create the clock domain
            cd = ClockDomain(name)
            m.domains += cd
            m.d.comb += cd.clk.eq(clk_sig)
            
            # Synchronize reset to the new clock domain
            m.submodules += ResetSynchronizer(~pll_locked, domain=name)
        
        return m
    
    def _odiv_to_sel(self, odiv):
        """Convert ODIV value to SEL parameter"""
        odiv_map = {
            1: 0, 2: 1, 4: 2, 8: 3, 16: 4, 32: 5,
            48: 6, 64: 7, 80: 8, 96: 9, 112: 10, 128: 11
        }
        return odiv_map[odiv]
    
    def print_config(self):
        """Print the calculated PLL configuration"""
        print(f"Input frequency: {self.input_freq} MHz")
        print("\nOutput configurations:")
        for name, params in self.pll_params.items():
            target = self.output_freqs[name]
            print(f"\n{name}:")
            print(f"  Target:  {target:.6f} MHz")
            print(f"  Actual:  {params['actual_freq']:.6f} MHz")
            print(f"  Error:   {params['error_mhz']:.6f} MHz ({params['error_pct']:.4f}%)")
            print(f"  IDIV:    {params['idiv']}")
            print(f"  FBDIV:   {params['fbdiv']}")
            print(f"  ODIV:    {params['odiv']}")


# Example usage
if __name__ == "__main__":
    # Example: 27 MHz input, generate multiple clock domains
    pll = GoWinPLL(
        input_freq=27.0,
        output_freqs={
            "sync": 50.0,    # Main system clock
            "audio": 49.152,
            "fast": 49.152 * 2,
        }
    )
 
    pll.print_config()
    
    # In your top-level design, you would use it like:
    # m.submodules.pll = pll
    # m.d.comb += [
    #     pll.clk_in.eq(ClockSignal("sync")),
    #     pll.rst_in.eq(ResetSignal("sync")),
    # ]
    # 
    # Then use the clock domains:
    # m.d.sync += counter.eq(counter + 1)  # Uses "sync" domain
    # m.d.pixel += ...  # Uses "pixel" domain
    # m.d.slow += ...   # Uses "slow" domain

