import multiprocessing as mulproc

import simtk.openmm.app  as app

from wepy.WExplore import Walker_chr

print("HELLO")
print('Reading psf file ..')
psf = app.CharmmPsfFile('fixed_seh.psf')

print('Reading pdb file ..')
pdb = app.PDBFile('seh_tppu_mdtraj.pdb')

print('Reading ff parameters')
params = app.CharmmParameterSet('top_all36_cgenff.rtf', 'par_all36_cgenff.prm',
                                'top_all36_prot.rtf', 'par_all36_prot.prm',
                                'tppu.str', 'toppar_water_ions.str')
# set WE parameters
n_walkers = 3
n_workers = 2
n_cycles = 2
n_atoms = 5097

initial = True
queue = mulproc.Queue()
manager = mulproc.Manager()
Walkers_List = manager.list()

for i in range (n_walkers):
    new_walker = Walker_chr()
    new_walker.Walker_ID = i
    new_walker.Weight = 1 / n_walkers
    new_walker.restartpoint = None
    Walkers_List.append(new_walker)


walkerwt = [ 1/n_walkers for i in range(n_walkers)]
mergedist = 0.25 # 2.5 A
# Make list of Walkers
walkerwt=[]
for i in range(n_cycles):
    walkers_pool = [ run_walker(params, psf.topology, i , initial)
                     for i in range(n_walkers) ]

    free_workers= mulproc.Queue()
    Lock = mulproc.Semaphore (n_workers)

    for i in range (n_workers):
        free_workers.put(i)


    for p in walkers_pool:
        p.start()


    for p in walkers_pool :
        p.join()


    for w in Walkers_List:
        print ('Rsult ID= {} and Weight = {}\n'.format(w.Walker_ID ,w.Weight))
    initial = False



    a2a = np.zeros((n_walkers,n_walkers))

# Calculating a2a Distance Matrix

    for i in range(n_walkers):
        walkerwt.append( Walkers_List[i].Weight )
        for j in range (i+1, n_walkers):
            Cal = Calculate()
            a2a[i][j] = Cal.Calculate_Rmsd(Walkers_List[i].positions, Walkers_List[j].positions)


    print (a2a)

  # merge and clone!

    mcf= mergeclone.decision_maker(a2a, walkerwt, n_walkers, mergedist)
    mcf.mergeclone()
    #for i in range(n_walkers):
     #   print (' WalkerId ={ }  Weight = {}  amp= {}  parent= {} '.format( i, mcf.walkerwt[i], mcf.amp[i] , mcf#.copy_struct[i]))

#   print (a2a)
