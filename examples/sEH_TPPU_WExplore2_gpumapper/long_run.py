import sys

import simtk.openmm.app as omma 
import simtk.openmm as omm
import simtk.unit as unit

import mdtraj as mdj
 
import scoop.futures


from wepy.openmm_sim_manager import OpenmmManager
from wepy.resampling.wexplore2 import WExplore2Resampler, UnbindingBC
from wepy.openmm import OpenMMRunner, OpenMMWalker ,OpenMMRunnerParallel
from wepy.gpumapper import GpuMapper

import numpy as np
import networkx as nx

from wepy.walker import Walker
from wepy.resampling.clone_merge import clone_parent_table, clone_parent_panel

from wepy.trajectory import trajectory_save




def print_initial_state(init_walkers,n_walkers):


    result_template_str = "|".join(["{:^10}" for i in range(n_walkers + 1)])

    # print the initial walkers
    print("The initial walkers:")

     # slots
    slot_str = result_template_str.format("slot", *[i for i in range(n_walkers)])
    print(slot_str)
 
    walker_weight_str = result_template_str.format("weight",
                                                    *[str(walker.weight) for walker in init_walkers])
    print(walker_weight_str)

def make_initial_minimized_state():
    psf = omma.CharmmPsfFile('sEH_TPPU_system.psf')

    # load the coordinates
    pdb = mdj.load_pdb('sEH_TPPU_system.pdb')

    # to use charmm forcefields get your parameters
    params = omma.CharmmParameterSet('all36_cgenff.rtf',
                                         'all36_cgenff.prm',
                                         'all36_prot.rtf',
                                         'all36_prot.prm',
                                         'tppu.str',
                                         'toppar_water_ions.str')

    # set the box size lengths and angles
    psf.setBox(82.435, 82.435, 82.435, 90, 90, 90)

        # create a system using the topology method giving it a topology and
        # the method for calculation
    system = psf.createSystem(params,
                                  nonbondedMethod=omma.CutoffPeriodic,
                                   nonbondedCutoff=1.0 * unit.nanometer,
                                  constraints=omma.HBonds)
    topology = psf.topology
        
    print("\nminimizing\n")
    # set up for a short simulation to minimize and prepare
    # instantiate an integrator
    integrator = omm.LangevinIntegrator(300*unit.kelvin,
                                            1/unit.picosecond,
                                            0.002*unit.picoseconds)
    # instantiate a OpenCL platform, in other platforms we can not have multiple simulation context 
    platform = omm.Platform.getPlatformByName('OpenCL') 

     # instantiate a simulation object
    simulation = omma.Simulation(psf.topology, system, integrator,platform)
    # initialize the positions
    simulation.context.setPositions(pdb.openmm_positions(frame=0))
    # minimize the energy
    simulation.minimizeEnergy()
    # run the simulation for a number of initial time steps
    simulation.step(1000)
    print("done minimizing\n")

        # get the initial state from the context
    minimized_state = simulation.context.getState(getPositions=True,
                                                  getVelocities=True,

                                                  getParameters=True)
    print ('finished initialization')
    return minimized_state, system, topology, pdb
 
if __name__ == "__main__":

    
    minimized_state, system, topology, pdb = make_initial_minimized_state()
    # set up parameters for running the simulation
    num_walkers = 48
    num_workers = 8
    # initial weights
    init_weight = 1.0 / num_walkers
     # make a generator for the in itial walkers
    init_walkers = [OpenMMWalker(minimized_state, init_weight) for i in range(num_walkers)]
    print_initial_state(init_walkers, num_walkers)
    
    # set up the OpenMMRunner with your system
    runner = OpenMMRunnerParallel(system, topology)
    # selecting ligand atoms index and protien atom index and binding_site_idxs for resampler and boundary conditions
    pdb = pdb.remove_solvent()
    lig_idxs = pdb.topology.select('resname "2RV"')
    atom_idxs = [atom.index for atom in pdb.topology.atoms]
    protein_idxs = np.delete(atom_idxs, lig_idxs)
    
    # selects protien atoms which have less than 2.5 A from ligand atoms
    binding_selection_idxs = mdj.compute_neighbors(pdb, 0.8, lig_idxs)
    binding_selection_idxs = np.delete(binding_selection_idxs, lig_idxs)

   

    # set up the Resampler (with parameters if needed)

    resampler = WExplore2Resampler(seed=1301, pmax=0.1, topology= pdb.topology,
                                   ligand_idxs=lig_idxs, binding_site_idxs=binding_selection_idxs )

    # instantiate a hpcc object
    gpumapper  = GpuMapper(num_walkers, num_workers)
    
    # makes ref_traj and selects lingand_atom and protein atom  indices 
    # instantiate a wexplore2unbindingboudaryconditiobs    
    wexplore2_ubc = UnbindingBC(initial_state=init_walkers[0], cutoff_distance=1.0,
                                                        topology=pdb.topology, ligand_idxs=lig_idxs,
                                                        binding_site_idxs=protein_idxs)
    # Instantiate a simulation manager
    sim_manager = OpenmmManager(init_walkers,
                          num_workers,
                          runner=runner,
                          resampler=resampler,
                          ubc = wexplore2_ubc,      
                          work_mapper=gpumapper.map)
    n_steps = 10000
    n_cycles = 2000

    # run a simulation with the manager for n_steps cycles of length 1000 each
    steps = [ n_steps for i in range(n_cycles)]
    sim_manager.run_simulation(n_cycles, 
                               steps,
                               debug_prints=True)