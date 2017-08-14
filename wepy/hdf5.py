import h5py
import json

def load_dataset(path):
    return None

class TrajHDF5(object):

    def __init__(self, filename, mode='x', overwrite=True,
                 topology=None,
                 positions=None,
                 time=None,
                 box_vectors=None,
                 velocities=None,
                 positions_unit=None,
                 time_unit=None,
                 box_vectors_unit=None,
                 velocities_unit=None,
                 forces=None,
                 parameters=None,
                 observables=None,
                 forces_units=None,
                 parameters_units=None,
                 observables_units=None
    ):
        """Initializes a TrajHDF5 object which is a format for storing
        trajectory data in and HDF5 format file which can be used on
        it's own or encapsulated in a WepyHDF5 object.

        mode:
        r        Readonly, file must exist
        w        Create file, truncate if exists
        x        Create file, fail if exists
        a        Append mode, file must exist

        If `overwrite` is True then the previous data will be
        re-initialized upon this constructor being called.

        """
        assert mode in ['r', 'w', 'x', 'a'], "mode must be either r, w, x or a"

        self._filename = filename

        # open the file
        h5 = h5py.File(filename, mode)
        self._h5 = h5
        self.closed = False

        # collect the non-topology attributes into a dict
        data = {'positions' : positions,
                'time' : time,
                'box_vectors' : box_vectors,
                'velocities' : velocities,
                'forces' : forces,
                'parameters' : parameters,
                'observables' : observables
               }

        units = {'positions' : positions_unit,
                 'time' : time_unit,
                 'box_vectors' : box_vectors_unit,
                 'velocities' : velocities_unit,
                 'forces' : forces_units,
                 'parameters' : parameters_units,
                 'observables' : observables_units
                }

        # some of these data fields are mandatory and others are
        # optional
        self._mandatory_keys = ['positions']

        # some data fields are compound and have more than one dataset
        # associated with them
        self._compound_keys = ['forces', 'parameters', 'observables']

        if mode in ['w', 'x'] and overwrite:
            # use the hidden init function for writing a new hdf5 file
            self._write_init(topology, data, units)

        elif mode == 'a':
            # use the hidden init function for appending data
            self._append_init(self, data, units)
        else mode == 'r':
            self._read_init(self)

    def _read_init(self):
        raise NotImplementedError

    def _write_init(self, topology, data, units):

        # initialize the topology flag
        self._topology = False
        # set the topology, will raise error internally
        self.topology = topology

        # go through each data field and add them, using the associated units
        for key, value in data.items():

            # initialize the attribute
            attr_key = "_{}".format(key)
            self.__dict__[attr_key] = False

            # if the value is None it was not set and we should just
            # continue without checking silently, unless it is mandatory
            if value is None:
                if key in self._mandatory_keys:
                    raise ValueError("{} is mandatory and must be given a value".format(key))
                else:
                    continue

            # try to add the data using the setter
            try:
                self.__setattr__(key, value)
            except:
                raise ValueError("{} value not valid".format(key))

            ## Units

            # make the key for the unit
            if key in self._compound_keys:
                # if it is compound name it plurally for heterogeneous data
                unit_key = "{}_units".format(key)
            else:
                # or just keep it singular for homogeneous data
                unit_key = "{}_unit".format(key)

            # try to add the units
            try:
                self.__setattr__(unit_key, units[key])
            except:
                raise ValueError("{} unit not valid".format(key))

    def _append_init(self, data, units):
        raise NotImplementedError

    @property
    def filename(self):
        return self._filename

    def close(self):
        if not self.closed:
            self._h5.close()
            self.closed = True

    def __del__(self):
        self.close()

    @property
    def h5(self):
        return self._h5

    @property
    def topology(self):
        return self._h5['topology']

    @topology.setter
    def topology(self, topology):
        try:
            json = json.loads(topology)
            del json
        except:
            raise ValueError("topology must be a valid JSON string")

        self._h5.create_dataset('topology', data=topology)
        self._topology = True

    @property
    def positions(self):
        return self._h5['positions']

    @positions.setter
    def positions(self, positions):
        assert isinstance(positions, np.ndarray), "positions must be a numpy array"
        self._h5.create_dataset('positions', data=positions)
        self._positions = True

    @property
    def time(self):
        return self._h5['time']

    @time.setter
    def time(self, time):
        assert isinstance(time, np.ndarray), "time must be a numpy array"
        self._h5.create_dataset('time', data=time)
        self._time = True

    @property
    def box_vectors(self):
        return self._h5['box_vectors']

    @box_vectors.setter
    def box_vectors(self, box_vectors):
        assert isinstance(box_vectors, np.ndarray), "box_vectors must be a numpy array"
        self._h5.create_dataset('box_vectors', data=box_vectors)
        self._box_vectors = True

    @property
    def velocities(self):
        return self._h5['velocities']

    @velocities.setter
    def velocities(self, velocities):
        assert isinstance(velocities, np.ndarray), "velocities must be a numpy array"
        self._h5.create_dataset('velocities', data=velocities)
        self._velocities = True


    ### These properties are not a simple dataset and should actually
    ### each be groups of datasets, even though there will be a net
    ### force we want to be able to have all forces which then the net
    ### force will be calculated from
    @property
    def forces(self):
        return self._h5['forces']

    @forces.setter
    def forces(self, forces):
        self._h5.create_dataset('forces', data=forces)
        self._forces = True

    @property
    def parameters(self):
        return self._h5['parameters']

    @parameters.setter
    def parameters(self, parameters):
        self._h5.create_dataset('parameters', data=parameters)
        self._parameters = True

    @property
    def observables(self):
        return self._h5['observables']

    @observables.setter
    def observables(self, observables):
        self._h5.create_dataset('observables', data=observables)
        self._observables = True



class WepyHDF5(object):

    def __init__(self, filename, mode='x', topology=None, overwrite=True):
        """Initialize a new Wepy HDF5 file. This is a file that organizes
        wepy.TrajHDF5 dataset subsets by simulations by runs and
        includes resampling records for recovering walker histories.

        mode:
        r        Readonly, file must exist
        w        Create file, truncate if exists
        x        Create file, fail if exists
        a        Append mode, file must exist

        If `overwrite` is True then the previous data will be
        re-initialized upon this constructor being called.

        """
        assert mode in ['r', 'w', 'x', 'a'], "mode must be either r, w, x or a"

        self._filename = filename

        # open the file
        h5 = h5py.File(filename, mode)
        self._h5 = h5
        self.closed = False

        if mode in ['w', 'x'] and overwrite:
            self._runs = self._h5.create_group('runs')
            # this keeps track of the number of runs. The current
            # value will be the name of the next run that is added,
            # and this should be incremented when that happens
            self._run_idx_counter = 0
            if topology:
                self.topology = topology


    @property
    def filename(self):
        return self._filename

    def close(self):
        if not self.closed:
            self._h5.close()
            self.closed = True

    def __del__(self):
        self.close()

    @property
    def h5(self):
        return self._h5

    @property
    def runs(self):
        return self._h5['runs']

    @property
    def topology(self):
        return self._h5['topology']

    @topology.setter
    def topology(self, topology):
        self._h5.create_dataset('topology', data=topology)

    def new_run(self, **kwargs):
        # create a new group named the next integer in the counter
        run_grp = self._h5.create_group('runs/{}'.format(str(self._run_idx_counter)))
        # increment the counter
        self._run_idx_counter += 1

        # add metadata if given
        for key, val in kwargs.items():
            run_grp.attrs[key] = val

        return run_grp
